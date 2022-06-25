
"""Interface with Solarman sensors."""

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Setup from the config entry."""
    inverter = hass.data[DOMAIN][entry.entry_id].inverter

    hass_sensors = []
    for sensor in inverter.get_sensors():
        if "isstr" in sensor:
            hass_sensors.append(SolarmanSensorText(inverter, sensor))
        else:
            hass_sensors.append(SolarmanSensor(inverter, sensor))

    hass_sensors.append(SolarmanStatus(inverter, "status_lastUpdate"))
    hass_sensors.append(SolarmanStatus(inverter, "status_connection"))

    async_add_entities(hass_sensors)
    

class SolarmanStatus(Entity):
    def __init__(self, inverter, field_name):
        self._inverter_name = inverter.name
        self.inverter = inverter
        self._field_name = field_name
        self.p_state = None
        self.p_icon = 'mdi:magnify'
        self._serial_number = inverter.serial_number
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
        return "{}_{}_{}".format(self._inverter_name, self._serial_number, self._field_name)

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

class SolarmanSensorText(SolarmanStatus):
    def __init__(self, inverter, sensor):
        SolarmanStatus.__init__(self, inverter, sensor['name'])
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


class SolarmanSensor(SolarmanSensorText):
    def __init__(self, inverter_name, inverter, sensor):
        SolarmanSensorText.__init__(self, inverter_name, inverter, sensor)
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

