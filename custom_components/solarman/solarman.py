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

QUERY_RETRY_ATTEMPTS = 2

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
        self.last_update = {}
        if not self.lookup_file or lookup_file == 'parameters.yaml':
            self.lookup_file = 'deye_hybrid.yaml'

        with open(self.path + self.lookup_file) as f:
            self.parameter_definition = yaml.full_load(f)

        self.params = ParameterParser(self.parameter_definition)

    def should_update_range(self, start, end, interval):
        if (start, end) not in self.last_update:
            return True
        last_update = self.last_update[(start, end)]
        return (datetime.now() - last_update).total_seconds() > interval

    def mark_range_updated(self, start, end):
        self.last_update[(start, end)] = datetime.now()

    def connect_to_server(self):
        if self._modbus:
            return self._modbus
        log.info(f"Connecting to solarman data logger {self._host}:{self._port}")
        self._modbus = PySolarmanV5(self._host, self._serial, port=self._port, mb_slave_id=self._mb_slaveid, logger=log, auto_reconnect=True, socket_timeout=15)

    def disconnect_from_server(self):
        if self._modbus:
            try:
                log.info(f"Disconnecting from solarman data logger {self._host}:{self._port}")
                self._modbus.disconnect()
            finally:
                self._modbus = None

    def send_request(self, start, end, mb_fc):
        length = end - start + 1
        match mb_fc:
            case 3:
                response  = self._modbus.read_holding_registers(register_addr=start, quantity=length)
            case 4:
                response  = self._modbus.read_input_registers(register_addr=start, quantity=length)
        self.params.parse(response, start, length)        

    
    def get_requests(self):
        return self.parameter_definition['requests']

    def get_statistics(self, requests):
        result = 1
        #requests = self.parameter_definition['requests']
        log.debug(f"Starting to query for [{len(requests)}] ranges...")

        try:

            for request in requests:
                start = request['start']
                end = request['end']
                mb_fc = request['mb_functioncode']
                interval = request.get('interval', 0)
                range_string = f"{start}-{end} (0x{start:04X}-0x{end:04X})"

                if not self.should_update_range(start, end, interval):
                    log.debug(f"Skipping [{range_string}]...")
                    continue
                else:
                    self.mark_range_updated(start, end)
                
                log.debug(f"Querying [{range_string}]...")

                attempts_left = QUERY_RETRY_ATTEMPTS
                while attempts_left > 0:
                    attempts_left -= 1
                    try:
                        self.connect_to_server()
                        self.send_request(start, end, mb_fc)
                        result = 1
                    except Exception as e:
                        result = 0
                        log.warning(f"Querying [{range_string}] failed with exception [{type(e).__name__}: {e}]")
                        self.disconnect_from_server()
                    if result == 0:
                        log.warning(f"Querying [{range_string}] failed, [{attempts_left}] retry attempts left")
                    else:
                        log.debug(f"Querying [{range_string}] succeeded")
                        break
                if result == 0:
                    log.warning(f"Querying registers [{range_string}] failed, aborting.")
                    break

            if result == 1:
                log.debug(f"All queries succeeded, exposing updated values.")
                self.status_lastUpdate = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                self.status_connection = "Connected"
                self._current_val = self.params.get_result()
            else:
                self.status_connection = "Disconnected"
                # Clear cached previous results to not report stale and incorrect data
                self._current_val = {}
                self.disconnect_from_server()
        except Exception as e:
            log.warning(f"Querying inverter {self._serial} at {self._host}:{self._port} failed on connection start with exception [{type(e).__name__}: {e}]")
            self.status_connection = "Disconnected"
            # Clear cached previous results to not report stale and incorrect data
            self._current_val = {}
            self.disconnect_from_server()

    def get_current_val(self):
        return self._current_val

    def get_sensors(self):
        return self.params.get_sensors()

# Service calls
    def service_write_holding_register(self, register, value):
        log.debug(f'Service Call: write_holding_register : [{register}], value : [{value}]')
        try:
            self.connect_to_server()
            self._modbus.write_holding_register(register, value)
        except Exception as e:
            log.warning(f"Service Call: write_holding_register : [{register}], value : [{value}] failed with exception [{type(e).__name__}: {e}]")
            self.disconnect_from_server()
        return

    def service_write_multiple_holding_registers(self, register, values):
        log.debug(f'Service Call: write_multiple_holding_registers: [{register}], values : [{values}]')
        try:
            self.connect_to_server()
            self._modbus.write_multiple_holding_registers(register, values)
        except Exception as e:
            log.warning(f"Service Call: write_multiple_holding_registers: [{register}], values : [{values}] failed with exception [{type(e).__name__}: {e}]")
            self.disconnect_from_server()
        return

