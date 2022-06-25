from datetime import timedelta

DOMAIN = 'solarman'

DEFAULT_INVERTER_PORT = 8899
DEFAULT_INVERTER_HOST = "0.0.0.0"
DEFAULT_INVERTER_SERVER_ID = 1
DEFAULT_INVERTER_SERIAL_NUMBER = 0
DEFAULT_LOOKUP_FILE = 'deye_hybrid.yaml'
LOOKUP_FILES = ['deye_hybrid.yaml', 'deye_string.yaml', 'sofar_lsw3.yaml', 'solis_hybrid.yaml', 'custom_parameters.yaml']

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

CONF_INVERTER_HOST = 'inverter_host'
CONF_INVERTER_PORT = 'inverter_port'
CONF_INVERTER_SERIAL_NUMBER = 'inverter_serial_number'
CONF_INVERTER_SERVER_ID = 'inverter_mb_server_id'
CONF_LOOKUP_FILE = 'lookup_file'

SENSOR_PREFIX = 'Solarman'
