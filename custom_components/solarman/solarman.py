import socket
import yaml
import logging
from datetime import datetime
from .parser import ParameterParser
from .const import *

_LOGGER = logging.getLogger(__name__)

START_OF_MESSAGE = 0xA5
END_OF_MESSAGE = 0x15
CONTROL_CODE = [0x10, 0x45]
SERIAL_NO = [0x00, 0x00]
SEND_DATA_FIELD = [0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

class Inverter:
    def __init__(self, path, serial_number, host, port, server_id, lookup_file, name):
        self._serial_number = serial_number
        self._serial_hex = self._get_serial_hex()
        self.path = path
        self._host = host
        self._port = port
        self._server_id = server_id
        self._current_val = None
        self._name = name
        self.status_connection = "Disconnected"
        self.status_lastUpdate = "N/A"
        if not lookup_file:
            lookup_file = 'deye_hybrid.yaml'
        elif lookup_file == 'parameters.yaml':
            lookup_file = 'deye_hybrid.yaml'

            
        with open(self.path + lookup_file) as f:
            self.parameter_definition = yaml.full_load(f) 

    @property
    def name(self):
        """Return name."""
        return self._name

    @property
    def serial_number(self):
        """Return serial number."""
        return self._serial_number

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

    def _get_serial_hex(self):
        serial_hex = hex(self._serial_number)[2:]
        serial_bytes = bytearray.fromhex(serial_hex)
        serial_bytes.reverse()
        return serial_bytes
    
    def get_read_business_field(self, start, length, mb_fc):
        request_data = bytearray([self._server_id, mb_fc]) # Function Code
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
        packet.extend(self._serial_hex)    
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
    
    def validate_checksum(self, packet):
        checksum = 0
        length = len(packet)
        # Don't include the checksum and END OF MESSAGE (-2)
        for i in range(1,length-2,1):
            checksum += packet[i]
        checksum &= 0xFF
        if checksum == packet[length-2]:
            return 1
        else:
            return 0
        
    
 
    def send_request (self, params, start, end, mb_fc):
        result = 0
        length = end - start + 1
        request = self.generate_request(start, length, mb_fc)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        try:
            sock.connect((self._host, self._port))
            _LOGGER.debug(request.hex())
            sock.sendall(request) # Request param 0x3B up to 0x71
            raw_msg = sock.recv(1024)
            _LOGGER.debug(raw_msg.hex())
            if self.validate_checksum(raw_msg) == 1:
                result = 1
                params.parse(raw_msg, start, length) 
            del raw_msg
        except:
            result = 0
        finally:
            sock.close()   
            del request
        return result

    
    def update (self):
        self.get_statistics()
        return


    def get_statistics(self):
        result = 1
        params = ParameterParser(self.parameter_definition)
        for request in self.parameter_definition['requests']:
            start = request['start']
            end= request['end']
            mb_fc = request['mb_functioncode']
            if 0 == self.send_request(params, start, end, mb_fc):
                # retry once
                if 0 == self.send_request(params, start, end, mb_fc):
                    result = 0
                    
        if result == 1: 
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
