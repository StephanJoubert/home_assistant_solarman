# Customizing

The heart of this component is the parameter-definition file, such as _deye_hybrid.yaml_. By changing the file, the behaviour is totally changed.

NOTE:
In order to leave your customized file intact during upgrades, copy the most relevant yaml file to a file called `custom_parameters.yaml`, and set the "lookup_file" option in configuration.yaml to point to it (or just select the file in the configuration flow UI).

```YAML
sensor:
  - platform: ...
    name: ...
    inverter_host: ...
    inverter_port: ...
    inverter_serial: ...
    scan_interval: ...
    lookup_file: custom_parameters.yaml
```

It has two sections:

## 1. Requests

This section defines the requests that should be issued to the logger each time the component does a parameter update. The list below was created for a DEYE 5kW inverter, and could be customized for other models that are not 100% compatible with this inverter.

```YAML
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
```

This block specifies that the component should issue three requests to the logger, the first one requesting parameters 0x0003 up to 0x000E, then a second request for parmeters 0x003B up to 0x0070, and the last for parameters 0x000f4 up to 0x00f8. All of the requests will be sent using Modbus Function Code 0x03.

The **maximum number** of registers that can be queried using the protocol **for each request is 125** (see [here](https://github.com/jmccrohan/pysolarmanv5/issues/51#issuecomment-1902238661)), but some loggers may get errors like `CRC validation failed` if the length is too much; in that case, reduce the length (`end-start`) by doing multiple requests.

If you get `V5FrameError: V5 frame contains invalid sequence number` errors in the log, it might be caused by concurrency (i.e. more than one client connected to the same logger stick).

## 2. Parameters

This section defines the individual parameter definitions: each parameter creates one sensor in Home Assistant. For example:

```YAML
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
```

The register must be included in the requests of the previous point, otherwise the sensor will have an `Unknown` value in Home Assistant.

Pay attention to the registers order when more than one are required; it could be descending when 2 registers are joint together or not, depending on the inverter.

### Group

The group just groups parameters that belong together. The induvidual parameter-items has to be placed in a group. The _items_ parameters contains the parameter definitions that belong in the group.

### Parameter-item

| Field          |                                                                                                                                    | Description                                                                                                                                                                                               |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| name           |                                                                                                                                    | The _name_ field of the home-assistant entity #                                                                                                                                                           |
| class          |                                                                                                                                    | The _class_ field of the home-assistant entity #                                                                                                                                                          |
| state_class    |                                                                                                                                    | The _state_class_ field of the home-assistant entity ##                                                                                                                                                   |
| uom            |                                                                                                                                    | The _unit_of_measurement_ field of the home-assistant entity #                                                                                                                                            |
| icon           |                                                                                                                                    | The _icon_ field of the home-assistant entity #                                                                                                                                                           |
|                | **The fields below define how the value from the logger is parsed**                                                                |
| scale          |                                                                                                                                    | Scaling factor for the value read from the logger (default: 1)                                                                                                                                            |
| scale_division |                                                                                                                                    | If specified, divides the result of the scaling by this number (e.g. if the value of the register is in minutes and you want the home-assistant entity in hours, use `scale_division: 60` and `uom: "h"`) |
| rule           |                                                                                                                                    | Method to interpret the data from the logger (see the table below)                                                                                                                                        |
| mask           |                                                                                                                                    | A mask to filter only used bit fields; this is especialy useful for flag fields                                                                                                                           |
| registers      |                                                                                                                                    | Array of register fields that comprises the value; if the value is placed in a number of registers, this array will contain more than one item (note: order is important)                                 |
| lookup         |                                                                                                                                    | Defines a key-value pair for values where an integer maps to a string field                                                                                                                               |
|                | **The following is optional and could be used, if the inverter delivers sometimes non-usable data (e.g. Total Production == 0.0)** |
| validation     |                                                                                                                                    |                                                                                                                                                                                                           |
|                | min                                                                                                                                | Spefifies the minimum value to accept                                                                                                                                                                     |
|                | max                                                                                                                                | Specifies the maximum value to accept                                                                                                                                                                     |
|                | invalidate_all                                                                                                                     | Optional: invalidate the complete dataset if specified; if not specified, it will only invalidate the specific parameter                                                                                  |

Example yaml file for the mentioned above:

```YAML
    - name: "Total Production"
      class: "energy"
      state_class: "total_increasing"
      uom: "kWh"
      scale: 0.1
      rule: 3
      registers: [0x003F,0x0040]
      icon: 'mdi:solar-power'
      validation:
        min: 0.1
        invalidate_all:
```

\# (see) https://developers.home-assistant.io/docs/core/entity/

\## see https://developers.home-assistant.io/docs/core/entity/sensor/#entities-representing-a-total-amount

### Rule

The `rule` field specifies how to interpret the binary data contained in the register(s).

| Rule # | Description           | Example                                                                                                                                   |
| ------ | --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| 1      | Unsigned 16-bit value |                                                                                                                                           |
| 2      | Signed 16 bit value   |                                                                                                                                           |
| 3      | Unsigned 32 bit value |                                                                                                                                           |
| 4      | Signed 32 bit value   |                                                                                                                                           |
| 5      | ASCII value           |                                                                                                                                           |
| 6      | Bit field             |                                                                                                                                           |
| 7      | Version               |                                                                                                                                           |
| 8      | Date Time             |                                                                                                                                           |
| 9      | Time                  | Time value as string<ul><li>Example 1: Register Value 2200 => Time Value: 22:00</li><li>Example 2: Register value: 400 => 04:00</li></ul> |
