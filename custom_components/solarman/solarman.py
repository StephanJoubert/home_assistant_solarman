import socket
import yaml
import logging
import struct
from homeassistant.util import Throttle
from datetime import datetime
from .parser import ParameterParser
from .const import *
from pysolarmanv5 import PySolarmanV5


log = logging.getLogger(__name__)

START_OF_MESSAGE = 0xA5
END_OF_MESSAGE = 0x15
CONTROL_CODE = [0x10, 0x45]
SERIAL_NO = [0x00, 0x00]
SEND_DATA_FIELD = [0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
QUERY_RETRY_ATTEMPTS = 6

class Inverter:
    def __init__(self, path, serial, host, port, mb_slaveid, lookup_file):
        self._modbus = None
        self._serial = serial
        self.path = path
        self._host = host
        self._port = port
        self._mb_slaveid = mb_slaveid
        self._current_val = None
        self.status_connection = "Disconnected"
        self.status_lastUpdate = "N/A"
        self.lookup_file = lookup_file
        if not self.lookup_file or lookup_file == 'parameters.yaml':
            self.lookup_file = 'deye_hybrid.yaml'

        with open(self.path + self.lookup_file) as f:
            self.parameter_definition = yaml.full_load(f)


    def connect_to_server(self):
        if self._modbus:
            return self._modbus
        
        self._modbus = PySolarmanV5(self._host, self._serial, port=self._port, mb_slave_id=1, verbose=True, auto_reconnect=True)
        return self._modbus

    def disconnect_from_server(self):
        if self._modbus:
            try:
                self._modbus.disconnect()
            finally:
                self._modbus = None
    
    def send_request(self, params, start, end, mb_fc, sock):
        length = end - start + 1
        match mb_fc:
            case 3:
                response  = sock.read_holding_registers(register_addr=start, quantity=length)
            case 4:
                response  = sock.read_input_registers(register_addr=start, quantity=length)
        params.parse(response, start, length)        


    @Throttle (MIN_TIME_BETWEEN_UPDATES)
    def update (self):
        self.get_statistics()
        return


    def get_statistics(self):
        result = 1
        params = ParameterParser(self.parameter_definition)
        requests = self.parameter_definition['requests']
        log.debug(f"Starting to query for [{len(requests)}] ranges...")



        modbus = None
        try:
            modbus = self.connect_to_server()

            for request in requests:
                start = request['start']
                end = request['end']
                mb_fc = request['mb_functioncode']
                log.debug(f"Querying [{start} - {end}]...")

                attempts_left = QUERY_RETRY_ATTEMPTS
                while attempts_left > 0:
                    attempts_left -= 1
                    try:
                        self.send_request(params, start, end, mb_fc, modbus)
                        result = 1
                    except Exception as e:
                        result = 0
                        log.warning(f"Querying [{start} - {end}] failed with exception [{type(e).__name__}]")
                    if result == 0:
                        log.warning(f"Querying [{start} - {end}] failed, [{attempts_left}] retry attempts left")
                    else:
                        log.debug(f"Querying [{start} - {end}] succeeded")
                        break
                if result == 0:
                    log.warning(f"Querying registers [{start} - {end}] failed, aborting.")
                    break

            if result == 1:
                log.debug(f"All queries succeeded, exposing updated values.")
                self.status_lastUpdate = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                self.status_connection = "Connected"
                self._current_val = params.get_result()
            else:
                self.status_connection = "Disconnected"
                # Clear cached previous results to not report stale and incorrect data
                self._current_val = {}
                self.disconnect_from_server(self)
        except Exception as e:
            log.warning(f"Querying inverter {self._serial} at {self._host}:{self._port} failed on connection start with exception [{type(e).__name__}]")
            self.status_connection = "Disconnected"
            # Clear cached previous results to not report stale and incorrect data
            self._current_val = {}
            self.disconnect_from_server(self)
#        finally:
#            if modbus:
#                modbus.disconnect()

    def get_current_val(self):
        return self._current_val

    def get_sensors(self):
        params = ParameterParser(self.parameter_definition)
        return params.get_sensors ()

# Service calls
    def service_write_holding_register(self, register, value):
        log.debug(f'Service Call: write_holding_register : [{register}], value : [{value}]')
        modbus=self.connect_to_server()
        try:
            modbus.write_holding_register(register, value)
#        modbus.disconnect()
        except Exception as e:
            log.warning(f"Service Call: write_holding_register : [{register}], value : [{value}] failed with exception [{type(e).__name__}]")
            self.disconnect_from_server(self)        
        return
        