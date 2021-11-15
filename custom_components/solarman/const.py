from datetime import timedelta

VERSION = '0.0.1'

DEFAULT_PORT_INVERTER = 8899
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)

CONF_INVERTER_HOST = 'inverter_host'
CONF_INVERTER_PORT = 'inverter_port'
CONF_INVERTER_SERIAL = 'inverter_serial'
CONF_SENSORS = 'sensors'
SENSOR_PREFIX = 'Solarman'
SENSOR_TYPES = {
    'PV1_Power':                ['PV1 Power', 'W', 'mdi:solar-power'],
    'PV2_Power':                ['PV2 Power', 'W', 'mdi:solar-power'],
    'Daily_Load_Consumption':   ['Daily Load Consumption', 'kWH', 'mdi:weather-sunny'],
    'Total_Grid_Production':    ['Total Grid Production', 'kWh', 'mdi:flash-outline'],
    'Total_Energy_Sold':        ['Total Energy Sold', 'kWh', 'mdi:flash-outline'],
    'Daily_Energy_Sold':        ['Daily Energy Sold', 'kWH', 'mdi:timer'],
    'Total_Energy_Bought':      ['Total Energy Bought', "kWH", 'mdi:information-outline'],
    'Daily_Energy_Bought':      ['Daily Energy Bought', 'kWH', 'mdi:thermometer'],
    'Total_Production':         ['Total Production', 'kWH', 'mdi:flash-outline'],
    'Daily_Production':         ['Daily Production', 'kWH', 'mdi:flash-outline'],
    'PV2_Current':              ['PV2 Current', 'A', 'mdi:flash-outline'],
    'PV1_Current':              ['PV1 Current', 'A', 'mdi:flash-outline'],
    'PV2_Voltage':              ['PV2 Voltage', 'V', 'mdi:flash-outline'],
    'PV1_Voltage':              ['PV1 Voltage', 'V', 'mdi:flash-outline'],
  }