
################################################################################
#   Solarman local interface.
#
#   This component can retrieve data solarman using version 5 of the protocol.
#
###############################################################################

from datetime import datetime

import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import ( EVENT_HOMEASSISTANT_STOP, CONF_NAME, CONF_SCAN_INTERVAL )
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle
from homeassistant.helpers.entity import Entity, generate_entity_id


from .const import *
from .solarman import Inverter


def _check_config_schema(conf):
    return conf

PLATFORM_SCHEMA = vol.All(PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME, default=SENSOR_PREFIX): cv.string,
    vol.Required(CONF_INVERTER_HOST, default=None): cv.string,
    vol.Required(CONF_INVERTER_PORT, default=DEFAULT_PORT_INVERTER): cv.positive_int,
    vol.Required(CONF_INVERTER_SERIAL, default=None): cv.positive_int,
}, extra=vol.PREVENT_EXTRA), _check_config_schema)        

def setup_platform(hass, config, add_devices, discovery_info=None):
  inverter_name = config.get(CONF_NAME)
  inverter_host = config.get(CONF_INVERTER_HOST)
  inverter_port = config.get(CONF_INVERTER_PORT)
  inverter_sn = config.get(CONF_INVERTER_SERIAL)
  path=hass.config.path('custom_components/solarman/')
  # Check input configuration. 
  if(inverter_host == None):
    raise vol.Invalid('configuration parameter [inverter_host] does not have a value')
  if(inverter_sn == None):
    raise vol.Invalid('configuration parameter [inverter_serial] does not have a value')
     
  inverter = Inverter(path, inverter_sn, inverter_host, inverter_port)
  #  Prepare the sensor entities.
  hass_sensors = []
  for sensor in inverter.get_sensors():
      hass_sensors.append(SunsynkSensor(inverter_name, inverter, sensor))
  add_devices(hass_sensors)

#############################################################################################################
# This is the sensor entity seen by Home Assistant.
#  It derives from the Entity class in HA
#############################################################################################################

class SunsynkSensor(Entity):
    def __init__(self, inverter_name, inverter, sensor):
        self._inverter_name = inverter_name
        self.inverter = inverter
        self._field_name = sensor['name']
        if 'icon' in sensor:
            self.p_icon = sensor['icon']
        else:
            self.p_icon = ''
        self._device_class = sensor['class']
        self.p_name = self._inverter_name
        self.uom = sensor['uom']
        self.p_state = None
        return

 
    @property
    def icon(self):
        #  Return the icon of the sensor. """
        return self.p_icon
    
    @property
    def name(self):
        #  Return the name of the sensor. 
        return "{} {}".format(self.p_name, self._field_name)
   
    @property
    def state(self):
        #  Return the state of the sensor. 
        return self.p_state


    @property
    def device_class(self):
        return self._device_class


    @property
    def extra_state_attributes(self):
        attrs = {   
            'last_reset' : datetime(1970,1,1,0,0,0,0),
            "state_class": "measurement"
        }
        return attrs

    @property
    def unit_of_measurement(self):
        return self.uom


    def update(self):
    #  Update this sensor using the data. 
    #  Get the latest data and use it to update our sensor state. 
    #  Retrieve the sensor data from actual interface
        self.inverter.update()

        val = self.inverter.get_current_val()
        if val is not None:
            if self._field_name in val:           
                self.p_state = val[self._field_name]

        


