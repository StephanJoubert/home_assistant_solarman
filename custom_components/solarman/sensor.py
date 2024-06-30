
################################################################################
#   Solarman local interface.
#
#   This component can retrieve data from the solarman dongle using version 5
#   of the protocol.
#
###############################################################################

import logging
import re
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import SolarmanSensorCoordinator
from .const import *
from .solarman import Inverter
from .scanner import InverterScanner
from .services import *

_LOGGER = logging.getLogger(__name__)
_inverter_scanner = InverterScanner()


def _do_setup_platform(hass: HomeAssistant, config, async_add_entities : AddEntitiesCallback):
    _LOGGER.debug(f'sensor.py:async_setup_platform: {config}') 
    
    inverter_name = config.get(CONF_NAME)
    inverter_host = config.get(CONF_INVERTER_HOST)
    if inverter_host == "0.0.0.0":
        inverter_host = _inverter_scanner.get_ipaddress()
        
   
    inverter_port = config.get(CONF_INVERTER_PORT)
    inverter_sn = config.get(CONF_INVERTER_SERIAL)
    if inverter_sn == 0:
        inverter_sn = _inverter_scanner.get_serialno()
    
    inverter_mb_slaveid = config.get(CONF_INVERTER_MB_SLAVEID)
    if not inverter_mb_slaveid:
        inverter_mb_slaveid = DEFAULT_INVERTER_MB_SLAVEID
    lookup_file = config.get(CONF_LOOKUP_FILE)
    path = hass.config.path('custom_components/solarman/inverter_definitions/')

    rbi = requests_by_interval(inverter)
    coordinators = [SolarmanSensorCoordinator(hass, _LOGGER, inverter_name, k, v, inverter) for k, v in rbi.items()]

    #Min key
    min_coord = rbi[min(rbi.keys())]

    # Check input configuration.
    if inverter_host is None:
        raise vol.Invalid('configuration parameter [inverter_host] does not have a value')
    if inverter_sn is None:
        raise vol.Invalid('configuration parameter [inverter_serial] does not have a value')

    inverter = Inverter(path, inverter_sn, inverter_host, inverter_port, inverter_mb_slaveid, lookup_file)
    #  Prepare the sensor entities.
    hass_sensors = []
    for sensor in inverter.get_sensors():
        try:
            if "isstr" in sensor:
                hass_sensors.append(SolarmanSensorText(find_coordinator(coordinators, sensor["registers"][0]), inverter_name, inverter, sensor, inverter_sn))
            else:
                hass_sensors.append(SolarmanSensor(find_coordinator(coordinators, sensor["registers"][0]), inverter_name, inverter, sensor, inverter_sn))
        except BaseException as ex:
            _LOGGER.error(f'Config error {ex} {sensor}')
            raise
    hass_sensors.append(SolarmanStatusDiag(min_coord, inverter_name, inverter, "status_lastUpdate", inverter_sn))
    hass_sensors.append(SolarmanStatusDiag(min_coord, inverter_name, inverter, "status_connection", inverter_sn))

    _LOGGER.debug(f'sensor.py:_do_setup_platform: async_add_entities')
    _LOGGER.debug(hass_sensors)

    async_add_entities(hass_sensors)
    # Register the services with home assistant.    
    register_services (hass, inverter)
    
def find_coordinator(coordinators, register):
    for c in coordinators:
        for requests in c.requests:
            if requests['start'] <= register and requests['end'] > register:
                return c
    
def requests_by_interval(inverter):
    tmp = {}
    requests = inverter.get_requests()
    for r in requests:
        interval = max(r.get('interval', 0), MIN_TIME_BETWEEN_UPDATES)
        if interval not in tmp:
            tmp[interval] = []
        tmp[interval].append(r)
        
    

# Set-up from configuration.yaml
async def async_setup_platform(hass: HomeAssistant, config, async_add_entities : AddEntitiesCallback, discovery_info=None):
    _LOGGER.debug(f'sensor.py:async_setup_platform: {config}') 
    _do_setup_platform(hass, config, async_add_entities)
       
# Set-up from the entries in config-flow
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    _LOGGER.debug(f'sensor.py:async_setup_entry: {entry.options}') 
    _do_setup_platform(hass, entry.options, async_add_entities)


#############################################################################################################
# This is the Device seen by Home Assistant.
#  It provides device_info to Home Assistant which allows grouping all the Entities under a single Device.
#############################################################################################################

class SolarmanSensor():
    """Solarman Device class."""

    def __init__(self, id: str = None, device_name: str = None, model: str = None, manufacturer: str = None):
        self.id = id
        self.device_name = device_name
        self.model = model
        self.manufacturer = manufacturer

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.id)},
            "name": self.device_name,
            "model": self.model,
            "manufacturer": self.manufacturer,
        }

    @property
    def extra_state_attributes(self):
        """Return the extra state attributes."""
        return {
            "id": self.id,
            "integration": DOMAIN,
        }


#############################################################################################################
# This is the entity seen by Home Assistant.
#  It derives from the Entity class in HA and is suited for status values.
#############################################################################################################

class SolarmanStatus(SolarmanSensor, CoordinatorEntity):
    def __init__(self, coordinator, inverter_name, inverter, field_name, sn):
        super().__init__(sn, inverter_name, inverter.lookup_file)
        super(CoordinatorEntity).__init__(coordinator)
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
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.p_state = getattr(self.inverter, self._field_name, None)
        self.async_write_ha_state()

#############################################################################################################
# This is the the same of SolarmanStatus, but it has EntityCategory setup to Diagnostic.
#############################################################################################################

class SolarmanStatusDiag(SolarmanStatus):
    def __init__(self, coordinator, inverter_name, inverter, field_name, sn):
        super().__init__(coordinator, inverter_name, inverter, field_name, sn)
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

#############################################################################################################
#  Entity displaying a text field read from the inverter
#   Overrides the Status entity, supply the configured icon, and updates the inverter parameters
#############################################################################################################

class SolarmanSensorText(SolarmanStatus):
    def __init__(self, coordinator, inverter_name, inverter, sensor, sn):
        SolarmanStatus.__init__(self, coordinator, inverter_name, inverter, sensor['name'], sn)
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
            else:
                uom = getattr(self, 'uom', None)
                if uom and (re.match("\S+", uom)):
                    self.p_state = None
                _LOGGER.debug(f'No value recorded for {self._field_name}')


#############################################################################################################
#  Entity displaying a numeric field read from the inverter
#   Overrides the Text sensor and supply the device class, last_reset and unit of measurement
#############################################################################################################

class SolarmanSensor(SolarmanSensorText):
    def __init__(self, coordinator, inverter_name, inverter, sensor, sn):
        SolarmanSensorText.__init__(self, coordinator, inverter_name, inverter, sensor, sn)
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

