# Solarman integration
Home Assistant component for interacting with Solarman data collectors that works with a variety of inverters and connects in direct mode over the local network and no cables are required. It has been tested with a 5kW DEYE/SUNSYNK inverter.

This component uses the version 5 specification of the communication protocol. If you inverter/collector is older and this comoonent does not work, try the following integration:

https://github.com/heinoldenhuis/home_assistant_omnik_solar


## Configuration

On your DHCP server, allocate a static IP to the WiFi data logger. 

In your configuration.yaml file, add the following values under "sensors"


Example:

~~~text

sensors:
  - platform: solarman
    name: DEYE
    inverter_host: 192.168.0.201
    inverter_port: 8899
    inverter_serial: 1720747149 
    scan_interval: 30
~~~

| Parameter | Description |
| ---- | ---- |
| name | This name will be prefixed to all parameter values|
| inverter_host| The IP address of the data logger |
| inverter_port | Always 8899 |
| inverter_serial| The serial number of the data collector |
| scan_interval | Time in seconds between refresh intervals |




