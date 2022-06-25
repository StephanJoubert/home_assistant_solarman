from datetime import timedelta

DOMAIN = 'solarman'

DEFAULT_PORT_INVERTER = 8899
DEFAULT_INVERTER_SERVER_ID = 1
DEFAULT_LOOKUP_FILE = 'deye_hybrid.yaml'
LOOKUP_FILES = ['deye_hybrid.yaml', 'deye_string.yaml', 'sofar_lsw3.yaml', 'solis_hybrid.yaml', 'custom_parameters.yaml']

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

CONF_INVERTER_HOST = 'inverter_host'
CONF_INVERTER_PORT = 'inverter_port'
CONF_INVERTER_SERIAL = 'inverter_serial'
#TODO:  find old 'inverter_mb_slaveid' and change to server, or just move to config_flow v2 ?
CONF_INVERTER_SERVER_ID = 'inverter_mb_slaveid'
CONF_LOOKUP_FILE = 'lookup_file'

SENSOR_PREFIX = 'Solarman'
