import socket
import yaml
import logging
import struct
from homeassistant.util import Throttle
from datetime import datetime
from .parser import ParameterParser
from .const import *
from random import randrange

log = logging.getLogger(__name__)

START_OF_MESSAGE = 0xA5
END_OF_MESSAGE = 0x15
CONTROL_CODE = [0x10, 0x45]
SERIAL_NO = [0x00, 0x00]
SEND_DATA_FIELD = [0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
QUERY_RETRY_ATTEMPTS = 6

class Inverter:
    def __init__(self, path, serial, host, port, mb_slaveid, lookup_file):
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

        # this value is used to validate the request packet number last sent, to actual response packets received
        self.current_sequence_number = None

    def advance_sequence_number(self):
        # generate the initial value randomly and increment from then forward
        if self.current_sequence_number is None:
            self.current_sequence_number = randrange(0x01, 0xFF)
        else:
            self.current_sequence_number = (self.current_sequence_number + 1) & 0xFF # prevent overflow

    def modbus(self, data):
        POLY = 0xA001

        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                crc = ((crc >> 1) ^ POLY
                if (crc & 0x0001)
                else crc >> 1)
        return crc

    def get_serial_hex(self):
        serial_hex = hex(self._serial)[2:]
        serial_bytes = bytearray.fromhex(serial_hex)
        serial_bytes.reverse()
        return serial_bytes

    def get_business_field(self, start, length, mb_fc):
        request_data = bytearray([self._mb_slaveid, mb_fc]) # Function Code
        request_data.extend(start.to_bytes(2, 'big'))
        request_data.extend(length.to_bytes(2, 'big'))
        crc = self.modbus(request_data)
        request_data.extend(crc.to_bytes(2, 'little'))
        return request_data 

    def generate_packet(self, param1, param2, mb_fc):
        # set the next sequence number to use for building the request
        self.advance_sequence_number()
        packet = bytearray([START_OF_MESSAGE])

        packet_data = []
        packet_data.extend (SEND_DATA_FIELD)
        buisiness_field = self.get_business_field(param1, param2, mb_fc)
        packet_data.extend(buisiness_field)
        length = packet_data.__len__()
        packet.extend(length.to_bytes(2, "little"))
        packet.extend(CONTROL_CODE)
        # this next field will be echoed back in the response message
        packet.extend(struct.pack("<H", self.current_sequence_number)) 
        packet.extend(self.get_serial_hex())
        packet.extend(packet_data)
        #Checksum
        checksum = 0
        for i in range(1,len(packet),1):
            checksum += packet[i]
        packet.append(checksum & 0xFF)
        packet.append(END_OF_MESSAGE)

        del packet_data
        del buisiness_field
        return packet

    def validate_packet(self, packet, length):
        # Perform some checks to ensure the received packet is correct
        # Start with the outer V5 logger packet and work inwards towards the embedded modbus frame

        # Does the v5 packet start and end with what we expect?
        if packet[0] != 0xa5 or packet[len(packet) - 1] != 0x15:
            log.warning("unexpected v5 packet start/stop")
            return 0
        # Does the v5 packet have the correct checksum?
        elif self.validate_v5_checksum(packet) == 0:
            log.warning("invalid v5 checksum")
            return 0
        # Is the control code what we expect?  Note: We sometimes see keepalives appear (0x4710)
        elif packet[3:5] != struct.pack("<H", 0x1510):
            log.warning("unexpected v5 control code")
            return 0
        # Is the v5 packet of the expected type?
        elif packet[11] != 0x02:
            log.warning("unexpected v5 frame type")
            return 0

        # Move onto the encapsulated modbus frame
        modbus_frame = packet[25:len(packet) - 2]

        # Is the modbus CRC correct?
        if self.validate_modbus_crc(modbus_frame) == 0:
            log.warning("invalid modbus crc")
            return 0

        # Does the response match the request?
        if packet[5] != self.current_sequence_number:
            log.warning("response frame contains unexpected sequence number")
            return 0

        # Were the expected number of registers returned?
        if self.validate_expected_registers_length(modbus_frame, length) == 0:		
            log.warning("unexpected number of registers found in response")
            return 0

        # Validation compelted successfully
        return 1

    def validate_expected_registers_length(self, modbus_frame_bytes, length):
        # Check that two bytes of data are returned for every register requested
        # If not, then this is likely the wrong response for the request or parsing will be unsafe
        actual_data_len = len(modbus_frame_bytes)-5 # do not count slave id, function code, length or CRC bytes (2)
        if actual_data_len == length*2:
            return 1
        else:
            return 0

    def validate_modbus_crc(self, frame):
        # Calculate crc with all but the last 2 bytes of the frame (they contain the crc)
        calc_crc = 0xFFFF
        for pos in frame[:-2]:
            calc_crc ^= pos
            for i in range(8):
                if (calc_crc & 1) != 0:
                    calc_crc >>= 1
                    calc_crc ^= 0xA001  # bitwise 'or' with modbus magic number (0xa001 == bitwise reverse of 0x8005)
                else:
                    calc_crc >>= 1

        # Compare calculated crc with the one supplied in the frame....
        frame_crc, = struct.unpack('<H', frame[-2:])
        if calc_crc == frame_crc:
            return 1
        else:
            return 0


    def validate_v5_checksum(self, packet):
        checksum = 0
        length = len(packet)
        # Don't include the checksum and END OF MESSAGE (-2)
        for i in range(1, length - 2, 1):
            checksum += packet[i]
        checksum &= 0xFF
        if checksum == packet[length - 2]:
            return 1
        else:
            return 0

    def connect_to_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.settimeout(6)
        server.connect((self._host, self._port))
        return server
        
    def send_request(self, params, start, end, mb_fc, sock):
        result = 0
        length = end - start + 1
        request = self.generate_packet(start, length, mb_fc)
        try:
            log.debug(request.hex())
            sock.sendall(request)
            raw_msg = sock.recv(1024)
            log.debug(raw_msg.hex())
            if self.validate_packet(raw_msg, length) == 1:
                result = 1
                params.parse(raw_msg, start, length)
            else:
                log.warn(f"Querying [{start} - {end}] failed, invalid response packet.")
            del raw_msg
        finally:
            del request
        return result

    def write_register (self, register, value, mb_fc):
        sock = None
        command = None
        try:
            sock = self.connect_to_server()
            if mb_fc:
                command = self.generate_packet(register, value, mb_fc)
            else:
                command = self.generate_packet(register, value, 6)
            log.debug(command.hex())
            sock.sendall(command)
            raw_msg = sock.recv(1024)
            log.debug(raw_msg.hex())
            del raw_msg
        except Exception as e:
            log.warning(f"Writing to inverter failed with exception [{type(e).__name__}]")
        finally:
            if command:
                del command
            if sock:
                del sock

    @Throttle (MIN_TIME_BETWEEN_UPDATES)
    def update (self):
        self.get_statistics()
        return


    def get_statistics(self):
        result = 1
        params = ParameterParser(self.parameter_definition)
        requests = self.parameter_definition['requests']
        log.debug(f"Starting to query for [{len(requests)}] ranges...")



        sock = None
        try:
            sock = self.connect_to_server()

            for request in requests:
                start = request['start']
                end = request['end']
                mb_fc = request['mb_functioncode']
                log.debug(f"Querying [{start} - {end}]...")

                attempts_left = QUERY_RETRY_ATTEMPTS
                while attempts_left > 0:
                    attempts_left -= 1
                    result = 0
                    try:
                        result = self.send_request(params, start, end, mb_fc, sock)
                    except ConnectionResetError:
                        log.warning(f"Querying [{start} - {end}] failed as client closed stream, trying to re-open.")
                        sock.close()
                        sock = self.connect_to_server()
                    except TimeoutError:
                        log.warning(f"Querying [{start} - {end}] failed with timeout")
                    except Exception as e:
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
        except Exception as e:
            log.warning(f"Querying inverter {self._serial} at {self._host}:{self._port} failed on connection start with exception [{type(e).__name__}]")
            self.status_connection = "Disconnected"
        finally:
            if sock:
                sock.close()

    def get_current_val(self):
        return self._current_val

    def get_sensors(self):
        params = ParameterParser(self.parameter_definition)
        return params.get_sensors ()

# Service calls
    def service_write_register(self, register, value, mb_fc):
        log.warning(f'Write Register : [{register}], value : [{value}], modbus_fc: [{mb_fc}]')
        self.write_register(register, value, mb_fc)