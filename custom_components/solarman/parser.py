import struct

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
        elif rule == 7:
            self.try_parse_version(rawData,definition, start, length)
        elif rule == 8:
            self.try_parse_datetime(rawData,definition, start, length)
        elif rule == 9:
            self.try_parse_time(rawData,definition, start, length)
        return
    
    def do_validate(self, title, value, rule):
        if 'min' in rule:           
            if rule['min'] > value:
                if 'invalidate_all' in rule:
                    raise ValueError(f'Invalidate complete dataset ({title} ~ {value})')
                return False

        if 'max' in rule:                       
            if rule['max'] < value:
                if 'invalidate_all' in rule:
                    raise ValueError(f'Invalidate complete dataset ({title} ~ {value})')
                return False
        
        return True

    def try_parse_signed (self, rawData, definition, start, length):
        title = definition['name']
        scale = definition['scale'] if 'scale' in definition else 1
        value = 0
        found = True
        shift = 0
        maxint = 0
        for r in definition['registers']:
            index = r - start   # get the decimal value of the register'
            if (index >= 0) and (index < length):
                maxint <<= 16
                maxint |= 0xFFFF
                temp = rawData[index]
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
                
            if 'validation' in definition:
                if not self.do_validate(title, value, definition['validation']):
                    return
                
            if self.is_integer_num (value):
                self.result[title] = int(value)  
            else:   
                self.result[title] = value

        return
    
    def try_parse_unsigned (self, rawData, definition, start, length):
        title = definition['name']
        scale = definition['scale'] if 'scale' in definition else 1
        value = 0
        found = True
        shift = 0
        for r in definition['registers']:
            index = r - start   # get the decimal value of the register'
            if (index >= 0) and (index < length):
                temp = rawData[index]
                value += (temp & 0xFFFF) << shift
                shift += 16
            else:
                found = False
        if found:
            if 'mask' in definition:
                mask = definition['mask']
                value &= mask

            if 'lookup' in definition:
                self.result[title] = self.lookup_value (value, definition['lookup'])
            else:
                if 'offset' in definition:
                    value = value - definition['offset']  
                                   
                value = value * scale
                
                if 'validation' in definition:
                    if not self.do_validate(title, value, definition['validation']):
                        return

                if self.is_integer_num (value):
                    self.result[title] = int(value)  
                else:   
                    self.result[title] = value   
        return


    def lookup_value (self, value, options):
        for o in options:
            if (o['key'] == value):
                return o['value']
        return value


    def try_parse_ascii (self, rawData, definition, start, length):
        title = definition['name']         
        found = True
        value = ''
        for r in definition['registers']:
            index = r - start   # get the decimal value of the register'
            if (index >= 0) and (index < length):
                temp = rawData[index]
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
                temp = rawData[index]
                value.append(hex(temp))
            else:
                found = False

        if found:
            self.result[title] = value
        return 
    
    def try_parse_version (self, rawData, definition, start, length):
        title = definition['name']         
        found = True
        value = ''
        for r in definition['registers']:
            index = r - start   # get the decimal value of the register'
            if (index >= 0) and (index < length):
                temp = rawData[index]
                value = value + str(temp >> 12) + "." +  str(temp >> 8 & 0x0F) + "." + str(temp >> 4 & 0x0F) + "." + str(temp & 0x0F)
            else:
                found = False
 
        if found:
            self.result[title] = value
        return

    def try_parse_datetime (self, rawData, definition, start, length):
        title = definition['name']         
        found = True
        value = ''
        print("start: ", start)
        for i,r in enumerate(definition['registers']):
            index = r - start   # get the decimal value of the register'
            print ("index: ",index)
            if (index >= 0) and (index < length):
                temp = rawData[index]
                if(i==0):
                    value = value + str(temp >> 8)  + "/" + str(temp & 0xFF) + "/"
                elif (i==1):
                    value = value + str(temp >> 8)  + " " + str(temp & 0xFF) + ":"
                elif(i==2):
                    value = value + str(temp >> 8)  + ":" + str(temp & 0xFF)
                else:
                    value = value + str(temp >> 8)  + str(temp & 0xFF)
            else:
                found = False
 
        if found:
            self.result[title] = value
        return

    def try_parse_time (self, rawData, definition, start, length):
        title = definition['name']         
        found = True
        value = ''
        for r in definition['registers']:
            index = r - start   # get the decimal value of the register'
            if (index >= 0) and (index < length):
                temp = rawData[index]
                value = str("{:02d}".format(int(temp / 100))) + ":" + str("{:02d}".format(int(temp % 100)))
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
