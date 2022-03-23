
################################################################################
#   Solarman local interface.
#
#   This component can retrieve data from the solarman dongle using version 5
#   of the protocol.
#
###############################################################################

from datetime import datetime

import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import *
from .solarman import Inverter

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    _LOGGER.debug(f'sensor.py:async_setup_entry: {entry.options}')

    inverter_name = entry.options.get(CONF_NAME)
    inverter_host = entry.options.get(CONF_INVERTER_HOST)
    inverter_port = entry.options.get(CONF_INVERTER_PORT)
    inverter_sn = entry.options.get(CONF_INVERTER_SERIAL)
    lookup_file = entry.options.get(CONF_LOOKUP_FILE)
    path = hass.config.path('custom_components/solarman/')

    # Check input configuration.
    if inverter_host is None:
        raise vol.Invalid('configuration parameter [inverter_host] does not have a value')
    if inverter_sn is None:
        raise vol.Invalid('configuration parameter [inverter_serial] does not have a value')

    inverter = Inverter(path, inverter_sn, inverter_host, inverter_port, lookup_file)
    #  Prepare the sensor entities.
    hass_sensors = []
    for sensor in inverter.get_sensors():
        if "isstr" in sensor:
            hass_sensors.append(SunsynkSensorText(inverter_name, inverter, sensor, inverter_sn))
        else:
            hass_sensors.append(SunsynkSensor(inverter_name, inverter, sensor, inverter_sn))

    hass_sensors.append(SynsynkStatus(inverter_name, inverter, "status_lastUpdate", inverter_sn))
    hass_sensors.append(SynsynkStatus(inverter_name, inverter, "status_connection", inverter_sn))

    _LOGGER.debug(f'sensor.py:async_setup_entry: async_add_entities')
    _LOGGER.debug(hass_sensors)

    async_add_entities(hass_sensors)

#############################################################################################################
# This is the entity seen by Home Assistant.
#  It derives from the Entity class in HA and is suited for status values.
#############################################################################################################

class SynsynkStatus(Entity):
    def __init__(self, inverter_name, inverter, field_name, sn):
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
        if 'state_class' in sensor:
            self._state_class = sensor['state_class']
        else:
            self._state_class = None
        self.uom = sensor['uom']
        return

    @property
    def device_class(self):
        return self._device_class


    @property
    def extra_state_attributes(self):
        if self._state_class:
            return  {
                'state_class': self._state_class
            }
        else:
            return None

    @property
    def unit_of_measurement(self):
        return self.uom

