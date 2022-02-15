from datetime import timedelta


DEFAULT_PORT_INVERTER = 8899
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

CONF_INVERTER_HOST = 'inverter_host'
CONF_INVERTER_PORT = 'inverter_port'
CONF_INVERTER_SERIAL = 'inverter_serial'
CONF_LOOKUP_FILE = 'lookup_file'

SENSOR_PREFIX = 'Solarman'
