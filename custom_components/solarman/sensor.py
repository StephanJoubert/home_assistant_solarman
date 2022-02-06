
################################################################################
#   Solarman local interface.
#
#   This component can retrieve data from the solarman dongle using version 5 
#   of the protocol.
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
      if "isstr" in sensor:
        hass_sensors.append(SunsynkSensorText(inverter_name, inverter, sensor, inverter_sn))
      else:
        hass_sensors.append(SunsynkSensor(inverter_name, inverter, sensor, inverter_sn))

  hass_sensors.append(SynsynkStatus(inverter_name, inverter, "status_lastUpdate", inverter_sn))
  hass_sensors.append(SynsynkStatus(inverter_name, inverter, "status_connection", inverter_sn))  
  add_devices(hass_sensors)

#############################################################################################################
# This is the entity seen by Home Assistant.
#  It derives from the Entity class in HA and is suited for status values.
#############################################################################################################

class SynsynkStatus(Entity):
    def __init__(self,inverter_name, inverter, field_name, sn):
        self._inverter_name = inverter_name
        self.inverter = inverter
        self._field_name = field_name
        self.p_state = None
        self.p_icon = 'mdi:magnify'
        self._sn = sn        
        return        
    
    @property
    def icon(self):
        #  Return the icon of the sensor. """
        return self.p_icon    
   
    @property
    def name(self):
        #  Return the name of the sensor. 
        return "{} {}".format(self._inverter_name, self._field_name)
    
    @property
    def unique_id(self):
        # Return a unique_id based on the serial number
        return "{}_{}_{}".format(self._inverter_name, self._sn, self._field_name)   

    @property
    def state(self):
        #  Return the state of the sensor. 
        return self.p_state     
    
    def update(self):
        self.p_state = getattr(self.inverter, self._field_name)

#############################################################################################################
#  Entity displaying a text field read from the inverter
#   Overrides the Status entity, supply the configured icon, and updates the inverter parameters
#############################################################################################################

class SunsynkSensorText(SynsynkStatus):
    def __init__(self, inverter_name, inverter, sensor, sn):
        SynsynkStatus.__init__(self,inverter_name, inverter, sensor['name'], sn)
        if 'icon' in sensor:
            self.p_icon = sensor['icon']
        else:
            self.p_icon = ''
        return

 
    def update(self):
    #  Update this sensor using the data. 
    #  Get the latest data and use it to update our sensor state. 
    #  Retrieve the sensor data from actual interface
        self.inverter.update()

        val = self.inverter.get_current_val()
        if val is not None:
            if self._field_name in val:           
                self.p_state = val[self._field_name]
                
                
#############################################################################################################
#  Entity displaying a numeric field read from the inverter
#   Overrides the Text sensor and supply the device class, last_reset and unit of measurement 
#############################################################################################################


class SunsynkSensor(SunsynkSensorText):
    def __init__(self, inverter_name, inverter, sensor, sn):
        SunsynkSensorText.__init__(self, inverter_name, inverter, sensor, sn)
        self._device_class = sensor['class']
        self.uom = sensor['uom']
        return
        
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

