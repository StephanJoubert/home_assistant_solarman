import socket
import threading
import yaml
import logging
import struct
from homeassistant.util import Throttle
from datetime import datetime
from .parser import ParameterParser
from .const import *
from pysolarmanv5 import PySolarmanV5

# Initialisiere das Logging
log = logging.getLogger(__name__)

# Konstante für die Anzahl der Wiederholungsversuche bei Abfragefehlern
QUERY_RETRY_ATTEMPTS = 2

# Konstanten für Verbindungsstatus
STATUS_CONNECTED = 1
STATUS_DISCONNECTED = 0

class Inverter:
    def __init__(self, path, serial, host, port, mb_slaveid, lookup_file):
        """
        Initialisiert das Inverter-Objekt.
        
        :param path: Pfad zur Konfigurationsdatei
        :param serial: Seriennummer des Inverters
        :param host: Hostname oder IP-Adresse des Datenloggers
        :param port: Portnummer des Datenloggers
        :param mb_slaveid: Modbus-Slave-ID
        :param lookup_file: Name der Lookup-Datei für Parameterdefinitionen
        """
        self._modbus = None
        self._serial = serial
        self.path = path
        self._host = host
        self._port = port
        self._mb_slaveid = mb_slaveid
        self._current_val = None
        self._status_connection = STATUS_DISCONNECTED
        self.status_lastUpdate = "N/A"
        self.lookup_file = lookup_file
        self.lock = threading.Lock()
        
        if not self.lookup_file or self.lookup_file == 'parameters.yaml':
            self.lookup_file = 'deye_hybrid.yaml'

        # Lade die Parameterdefinitionen aus der Lookup-Datei
        try:
            with open(self.path + self.lookup_file) as f:
                self.parameter_definition = yaml.full_load(f)
        except FileNotFoundError:
            log.error(f"Lookup file {self.lookup_file} not found at path {self.path}")
            raise
        except yaml.YAMLError as e:
            log.error(f"Error parsing the lookup file {self.lookup_file}: {e}")
            raise

    @property
    def status_connection(self):
        return 'Connected' if self._status_connection == STATUS_CONNECTED else 'Disconnected'

    def is_connected_to_server(self):
        return self._modbus is not None

    def connect_to_server(self):
        """
        Stellt eine Verbindung zum Solarman-Datenlogger her.
        """
        if self._modbus:
            return self._modbus
        log.info(f"Connecting to solarman data logger {self._host}:{self._port}")
        try:
            self._modbus = PySolarmanV5(
                self._host, self._serial, port=self._port,
                mb_slave_id=self._mb_slaveid, logger=None,
                auto_reconnect=True, socket_timeout=15
            )
            self._status_connection = STATUS_CONNECTED
            log.info("Connection to solarman data logger established successfully.")
        except Exception as e:
            log.error(f"Failed to connect to solarman data logger: {e}")
            self._modbus = None
            self._status_connection = STATUS_DISCONNECTED
        return self._modbus

    def disconnect_from_server(self):
        """
        Trennt die Verbindung zum Solarman-Datenlogger.
        """
        if self._modbus:
            try:
                log.info(f"Disconnecting from solarman data logger {self._host}:{self._port}")
                self._modbus.disconnect()
            except Exception as e:
                log.error(f"Failed to disconnect from solarman data logger: {e}")
            finally:
                self._modbus = None
                self._status_connection = STATUS_DISCONNECTED
                log.info("Successfully disconnected from solarman data logger.")

    def send_request(self, params, start, end, mb_fc) -> None:
        """
        Sendet eine Anfrage an den Datenlogger und parst die Antwort.

        :param params: ParameterParser-Objekt zum Parsen der Antwort
        :param start: Startadresse des Registers
        :param end: Endadresse des Registers
        :param mb_fc: Modbus-Funktionscode (3 oder 4)
        """
        length = end - start + 1
        range_string = f"{start}-{end} (0x{start:04X}-0x{end:04X})"
        try:
            log.debug(f"Sending request to read registers [{range_string}] with function code {mb_fc}")
            match mb_fc:
                case 3:
                    response = self._modbus.read_holding_registers(register_addr=start, quantity=length)
                case 4:
                    response = self._modbus.read_input_registers(register_addr=start, quantity=length)
            params.parse(response, start, length)
            log.debug(f"Successfully sent request and parsed response for registers [{range_string}]")
        except Exception as e:
            log.error(f"Failed to send request for registers [{range_string}] with function code {mb_fc}: {e}")
            raise

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """
        Aktualisiert die Statistiken des Inverters.
        Diese Methode ist gedrosselt, um nicht zu häufig aufgerufen zu werden.
        """
        self.get_statistics()
        return

    def get_statistics(self) -> None:
        """
        Holt die aktuellen Statistiken vom Inverter.
        """
        result = STATUS_CONNECTED
        params = ParameterParser(self.parameter_definition)
        requests = self.parameter_definition['requests']
        log.debug(f"Starting to query for [{len(requests)}] ranges...")

        with self.lock:
            try:
                isConnected = self._status_connection == STATUS_CONNECTED
                for request in requests:
                    start = request['start']
                    end = request['end']
                    mb_fc = request['mb_functioncode']
                    range_string = f"{start}-{end} (0x{start:04X}-0x{end:04X})"
                    log.debug(f"Querying [{range_string}]...")

                    attempts_left = QUERY_RETRY_ATTEMPTS
                    while attempts_left > 0:
                        attempts_left -= 1
                        try:
                            self.connect_to_server()
                            self.send_request(params, start, end, mb_fc)
                            result = STATUS_CONNECTED
                        except Exception as e:
                            result = STATUS_DISCONNECTED
                            log.log((logging.WARNING if isConnected else logging.DEBUG), f"Querying [{start} - {end}] failed with exception [{type(e).__name__}: {e}]")
                            self.disconnect_from_server()
                        if result == STATUS_DISCONNECTED:
                            log.log((logging.WARNING if isConnected else logging.DEBUG), f"Querying [{start} - {end}] failed, [{attempts_left}] retry attempts left")
                        else:
                            log.debug(f"Querying [{range_string}] succeeded")
                            break
                    if result == STATUS_DISCONNECTED:
                        log.log((logging.WARNING if isConnected else logging.DEBUG), f"Querying registers [{start} - {end}] failed, aborting.")
                        break

                if result == STATUS_CONNECTED:
                    log.debug(f"All queries succeeded, exposing updated values.")
                    self.status_lastUpdate = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
                    self._status_connection = STATUS_CONNECTED
                    self._current_val = params.get_result()
                else:
                    self._status_connection = STATUS_DISCONNECTED
                    # Clear cached previous results to not report stale and incorrect data
                    self._current_val = {}
                    self.disconnect_from_server()
            except Exception as e:
                log.warning(f"Querying inverter {self._serial} at {self._host}:{self._port} failed on connection start with exception [{type(e).__name__}: {e}]")
                self._status_connection = STATUS_DISCONNECTED
                # Lösche zwischengespeicherte vorherige Ergebnisse, um keine veralteten Daten zu melden
                self._current_val = {}
                self.disconnect_from_server()

    def get_current_val(self):
        """
        Gibt die aktuellen Werte des Inverters zurück.

        :return: Dictionary mit aktuellen Werten
        """
        return self._current_val

    def get_sensors(self):
        """
        Gibt die Sensoren des Inverters zurück.

        :return: Liste der Sensoren
        """
        params = ParameterParser(self.parameter_definition)
        return params.get_sensors()

    # Service calls
    def service_read_holding_register(self, register):
        log.debug(f'Service Call: read_holding_register : [{register}]')

        with self.lock:
            try:
                wasConnected = self.is_connected_to_server()
                self.connect_to_server()
                response = self._modbus.read_holding_registers(register, 1)
                log.info(f'Service Call: read_holding_registers : [{register}] value [{response}]')
                if not wasConnected:
                    self.disconnect_from_server()
            except Exception as e:
                log.warning(f"Service Call: read_holding_registers : [{register}] failed with exception [{type(e).__name__}: {e}]")
                self.disconnect_from_server()
                raise e

        return response

    def service_read_multiple_holding_registers(self, register, count):
        log.debug(f'Service Call: read_holding_register : [{register}], count : {count}')

        with self.lock:
            try:
                wasConnected = self.is_connected_to_server()
                self.connect_to_server()
                response = self._modbus.read_holding_registers(register, count)
                log.info(f'Service Call: read_holding_registers : [{register}] value [{response}]')
                if not wasConnected:
                    self.disconnect_from_server()
            except Exception as e:
                log.warning(f"Service Call: read_holding_registers : [{register}] failed with exception [{type(e).__name__}: {e}]")
                self.disconnect_from_server()
                raise e

        return response

    def service_write_holding_register(self, register, value):
        log.debug(f'Service Call: write_holding_register : [{register}], value : [{value}]')
        with self.lock:
            try:
                wasConnected = self.is_connected_to_server()
                self.connect_to_server()
                self._modbus.write_holding_register(register, value)
                if not wasConnected:
                    self.disconnect_from_server()
            except Exception as e:
                log.warning(f"Service Call: write_holding_register : [{register}], value : [{value}] failed with exception [{type(e).__name__}: {e}]")
                self.disconnect_from_server()
                raise e
        return

    def service_write_multiple_holding_registers(self, register, values):
        log.debug(f'Service Call: write_multiple_holding_registers: [{register}], values : [{values}]')
        with self.lock:
            try:
                wasConnected = self.is_connected_to_server()
                self.connect_to_server()
                self._modbus.write_multiple_holding_registers(register, values)
                if not wasConnected:
                    self.disconnect_from_server()
            except Exception as e:
                log.warning(f"Service Call: write_multiple_holding_registers: [{register}], values : [{values}] failed with exception [{type(e).__name__}: {e}]")
                self.disconnect_from_server()
                raise e
        return
