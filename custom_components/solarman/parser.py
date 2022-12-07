import yaml
import struct
import math




# The parameters start in the "business field" 
# just after the first two bytes.
OFFSET_PARAMS = 28


class ParameterParser:
    def __init__(self, lookups):
        self.result = {}
        self._lookups = lookups 
        return

    def parse (self, rawData, start, length):
        for i in self._lookups['parameters']:
            for j in i['items']:
                self.try_parse_field(rawData, j, start, length)        
        return

    def get_result(self):
        return self.result


    def try_parse_field (self, rawData, definition, start, length):
        rule = definition['rule']
        if rule == 1:
            self.try_parse_unsigned(rawData,definition, start, length)
        elif rule == 2:
            self.try_parse_signed(rawData,definition, start, length)
        elif rule == 3:
            self.try_parse_unsigned(rawData,definition, start, length)
        elif rule == 4:
            self.try_parse_signed(rawData,definition, start, length)
        elif rule == 5:
            self.try_parse_ascii(rawData,definition, start, length)
        elif rule == 6:
            self.try_parse_bits(rawData,definition, start, length)
        return

    def try_parse_signed (self, rawData, definition, start, length):
        title = definition['name']
        scale = definition['scale']
        value = 0
        found = True
        shift = 0
        maxint = 0
        for r in definition['registers']:
            index = r - start   # get the decimal value of the register'
            if (index >= 0) and (index < length):
                maxint <<= 16
                maxint |= 0xFFFF
                offset = OFFSET_PARAMS + (index * 2)
                temp = struct.unpack('>H', rawData[offset:offset + 2])[0]
                value += (temp & 0xFFFF) << shift
                shift += 16
            else:
                found = False
        if found:
            if 'offset' in definition:
                value = value - definition['offset']       
                      
            if value > maxint/2:
                value = (value - maxint) * scale
            else:
                value = value * scale
                
            if self.is_integer_num (value):
                self.result[title] = int(value)  
            else:   
                self.result[title] = value

            if 'invalid' in definition:
                if math.fabs(definition['invalid'] - value) < 0.001:
                    raise ValueError(f'Invalidate complete dataset ({title} ~ {value})')
        return
    
    def try_parse_unsigned (self, rawData, definition, start, length):
        title = definition['name']
        scale = definition['scale']
        value = 0
        found = True
        shift = 0
        for r in definition['registers']:
            index = r - start   # get the decimal value of the register'
            if (index >= 0) and (index < length):
                offset = OFFSET_PARAMS + (index * 2)
                temp = struct.unpack('>H', rawData[offset:offset + 2])[0]
                value += (temp & 0xFFFF) << shift
                shift += 16
            else:
                found = False
        if found:
            if 'lookup' in definition:
                self.result[title] = self.lookup_value (value, definition['lookup'])
            else:
                if 'offset' in definition:
                    value = value - definition['offset']  
                                   
                value = value * scale
                if self.is_integer_num (value):
                    self.result[title] = int(value)  
                else:   
                    self.result[title] = value   

                if 'invalid' in definition:
                    if math.fabs(definition['invalid'] - value) < 0.001:
                        raise ValueError(f'Invalidate complete dataset ({title} ~ {value})')
        return


    def lookup_value (self, value, options):
        for o in options:
            if (o['key'] == value):
                return o['value']
        return "LOOKUP"


    def try_parse_ascii (self, rawData, definition, start, length):
        title = definition['name']         
        found = True
        value = ''
        for r in definition['registers']:
            index = r - start   # get the decimal value of the register'
            if (index >= 0) and (index < length):
                offset = OFFSET_PARAMS + (index * 2)
                temp = struct.unpack('>H', rawData[offset:offset + 2])[0]
                value = value + chr(temp >> 8) + chr(temp & 0xFF)
            else:
                found = False

        if found:
            self.result[title] = value
        return  
    
    def try_parse_bits (self, rawData, definition, start, length):
        title = definition['name']         
        found = True
        value = []
        for r in definition['registers']:
            index = r - start   # get the decimal value of the register'
            if (index >= 0) and (index < length):
                offset = OFFSET_PARAMS + (index * 2)
                temp = struct.unpack('>H', rawData[offset:offset + 2])[0]
                value.append(hex(temp))
            else:
                found = False

        if found:
            self.result[title] = value
        return 
    
    def get_sensors (self):
        result = []
        for i in self._lookups['parameters']:
            for j in i['items']:
                result.append(j)
        return result
    
    def is_integer_num(self, n):
        if isinstance(n, int):
            return True
        if isinstance(n, float):
            return n.is_integer()
        return False