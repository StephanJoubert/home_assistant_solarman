# Customizing 

The hart of this component is the parameter-definition file ex *deye_hybrid.yaml*. By changing the file, the behaviour is totally changed.

NOTE:
In order to leave your customized file intact during upgrades, copy the most relevant yaml file to a file called "custom_parameters.yaml, and set the "lookup_file" option in configuration.yaml to point to it.

~~~ YAML
sensor:
  - platform: ...
    name: ...
    inverter_host: ...
    inverter_port: ...
    inverter_serial: ... 
    scan_interval: ...
    lookup_file: custom_parameters.yaml
~~~

It has two sections:

## 1. Requests
This section defines the requests that should be issued to the logger each time the component does a parameter update. The list below was created for a DEYE 5kW inverter, and could be customized for other models that are not 100% compatible with this inverter.

~~~ YAML
requests:
  - start: 0x0003
    end:  0x000E
    mb_functioncode: 0x03
  - start: 0x003B
    end: 0x0070
    mb_functioncode: 0x03
  - start: 0x0096
    end: 0x00C3
    mb_functioncode: 0x03
  - start: 0x00f4
    end: 0x00f8
    mb_functioncode: 0x03

~~~

This block specifies that the component should issue three requests to the logger, the first one requesting parameters 0x0003 up to 0x000E, then a second request for parmeters 0x003B up to 0x0070, and the last for parameters 0x000f4 up to 0x00f8. All of the requests will be sent using Modbus Function Code 0x03.

## 2. Parameters
This section defines the induvidual parameter definitions. For example:

~~~ YAML
parameters:
 - group: solar
   items: 
    - name: "PV1 Power"
      class: "power"
      state_class: "measurement"
      uom: "W"
      scale: 1
      rule: 1
      registers: [0x00BA]
      icon: 'mdi:solar-power'
~~~

### group
The group just groups parameters that belong together. The induvidual parameter-items has to be placed in a group. The *items* parameters contains the parameter definitions that belong in the group.

### Parameter-item


|field|description|
|:----------:|----------|
|name|The *name* field of the home-assistant entity #|
|class|The *class* field of the home-assistant entity #|
|state_class|The *state_class* field of the home assistant entity ##|
|uom|The *unit_of_measurement* field of the home-assistant entity #|
|icon|The *icon* field of the home-assistant entity #|
|| **The fields below define how the value from the logger is parsed** |
|scale|Scaling factor for the value read from the logger|
|rule|Method to interpret the data from the logger ###|
|registers|Array of register fields that comprises the value. If the value is placed in a number of registers, this  array will contain more than one item.|
|lookup|Defines a key-value pair for values where an integer maps to a string field|
|invalid|Optional validation against a reference value, which invalidate complete dataset. Could be used, if the inverter delivers sometimes non usable data (e.g. Total Production == 0.0)|


\# (see) https://developers.home-assistant.io/docs/core/entity/

\## see https://developers.home-assistant.io/docs/core/entity/sensor/#entities-representing-a-total-amount

\### The rule field specifies how to interpret the binary data. 

1. unsigned 16-bit value
2. signed 16 bit value
3. unsigned 32 bit value
4. signed 32 bit value
5. ascii value
6. bit field



