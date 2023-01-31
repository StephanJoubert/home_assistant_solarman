import socket
import yaml
import logging
import struct
from homeassistant.util import Throttle
from datetime import datetime
from .parser import ParameterParser
from .const import *

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
        if not lookup_file:
            lookup_file = 'deye_hybrid.yaml'
        elif lookup_file == 'parameters.yaml':
            lookup_file = 'deye_hybrid.yaml'

            
        with open(self.path + lookup_file) as f:
            self.parameter_definition = yaml.full_load(f) 

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
    
    def get_read_business_field(self, start, length, mb_fc):
        request_data = bytearray([self._mb_slaveid, mb_fc]) # Function Code
        request_data.extend(start.to_bytes(2, 'big'))
        request_data.extend(length.to_bytes(2, 'big'))
        crc = self.modbus(request_data)
        request_data.extend(crc.to_bytes(2, 'little'))  
        return request_data
        
    def generate_request(self, start, length, mb_fc):
        packet = bytearray([START_OF_MESSAGE])

        packet_data = []
        packet_data.extend (SEND_DATA_FIELD)
        buisiness_field = self.get_read_business_field(start, length, mb_fc)
        packet_data.extend(buisiness_field)
        length = packet_data.__len__()
        packet.extend(length.to_bytes(2, "little")) 
        packet.extend(CONTROL_CODE)
        packet.extend(SERIAL_NO)
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

    def validate_packet(self, packet):
        # Perform some checks to ensure the received packet is correct
        # Start with the outer V5 logger packet and work inwards towards the embedded modbus frame

        # Does the v5 packet start and end with what we expect?
        if packet[0] != 0xa5 or packet[len(packet) - 1] != 0x15:
            log.debug("unexpected v5 packet start/stop")
            return 0
        # Does the v5 packet have the correct checksum?
        elif self.validate_v5_checksum(packet) == 0:
            log.debug("invalid v5 checksum")
            return 0
        # Is the control code what we expect?  Note: We sometimes see keepalives appear (0x4710)
        elif packet[3:5] != struct.pack("<H", 0x1510):
            log.debug("unexpected v5 control code")
            return 0
        # Is the v5 packet of the expected type?
        elif packet[11] != 0x02:
            log.debug("unexpected v5 frame type")
            return 0

        # Move onto the encapsulated modbus frame
        modbus_frame = packet[25:len(packet) - 2]

        # Is the modbus CRC correct?
        if self.validate_modbus_crc(modbus_frame) == 0:
            log.debug("invalid modbus crc")
            return 0

        # Validation compelted successfully
        return 1


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


    def send_request(self, params, start, end, mb_fc, sock):
        result = 0
        length = end - start + 1
        request = self.generate_request(start, length, mb_fc)
        try:
            log.debug(request.hex())
            sock.sendall(request)
            raw_msg = sock.recv(1024)
            log.debug(raw_msg.hex())
            if self.validate_packet(raw_msg) == 1:
                result = 1
                params.parse(raw_msg, start, length)
            else:
                log.debug(f"Querying [{start} - {end}] failed, invalid response packet.")
            del raw_msg
        finally:
            del request
        return result

    @Throttle (MIN_TIME_BETWEEN_UPDATES)
    def update (self):
        self.get_statistics()
        return


    def get_statistics(self):
        result = 1
        params = ParameterParser(self.parameter_definition)
        requests = self.parameter_definition['requests']
        log.debug(f"Starting to query for [{len(requests)}] ranges...")

        def connect_to_server():
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.settimeout(10)
            server.connect((self._host, self._port))
            return server

        for request in requests:
            sock = None
            try:
                sock = connect_to_server()
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
                        log.debug(f"Querying [{start} - {end}] failed as client closed stream, trying to re-open.")
                        sock.close()
                        sock = connect_to_server()
                    except TimeoutError:
                        log.debug(f"Querying [{start} - {end}] failed with timeout")
                    except Exception as e:
                        log.debug(f"Querying [{start} - {end}] failed with exception [{type(e).__name__}]")
                    if result == 0:
                        log.debug(f"Querying [{start} - {end}] failed, [{attempts_left}] retry attempts left")
                    else:
                        log.debug(f"Querying [{start} - {end}] succeeded")
                        break
                if result == 0:
                    log.warning(f"Querying registers [{start} - {end}] failed, aborting.")
                    break
            except Exception as e:
                log.warning(f"Querying failed on connection start with exception [{type(e).__name__}]")
            finally:
                if sock:
                    sock.close()

        if result == 1:
            log.debug(f"All queries succeeded, exposing updated values.")
            self.status_lastUpdate = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
            self.status_connection = "Connected"
            self._current_val = params.get_result()
        else:
            self.status_connection = "Disconnected"

    def get_current_val(self):
        return self._current_val

    def get_sensors(self):
        params = ParameterParser(self.parameter_definition)
        return params.get_sensors ()
