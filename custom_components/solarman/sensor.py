"""Interface with Solarman sensors."""

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import SensorEntity


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
    

class SolarmanStatus(SensorEntity):
    def __init__(self, inverter, field_name):
        self.inverter = inverter
        self._field_name = field_name
        self._inverter_name = inverter.name
        self._serial_number = inverter.serial_number
        self._attr_icon = 'mdi:magnify'
        self._attr_name = "{} {}".format(self._inverter_name, field_name)
        self._attr_unique_id = "{}_{}_{}".format(self._inverter_name, self._serial_number, field_name)


    def update(self):
        self._attr_state = getattr(self.inverter, self._field_name)

#############################################################################################################
#  Entity displaying a text field read from the inverter
#   Overrides the Status entity, supply the configured icon, and updates the inverter parameters
#############################################################################################################

class SolarmanSensorText(SolarmanStatus):
    def __init__(self, inverter, sensor):
        SolarmanStatus.__init__(self, inverter, sensor['name'])
        if 'icon' in sensor:
            self._attr_icon = sensor['icon']


    def update(self):
    #  Update this sensor using the data.
    #  Get the latest data and use it to update our sensor state.
    #  Retrieve the sensor data from actual interface
        self.inverter.update()

        val = self.inverter.get_current_val()
        if val is not None:
            if self._field_name in val:
                self._attr_state = val[self._field_name]


#############################################################################################################
#  Entity displaying a numeric field read from the inverter
#   Overrides the Text sensor and supply the device class, last_reset and unit of measurement
#############################################################################################################


class SolarmanSensor(SolarmanSensorText):
    def __init__(self, inverter_name, inverter, sensor):
        SolarmanSensorText.__init__(self, inverter_name, inverter, sensor)
        self._attr_device_class = sensor['class']
        if 'state_class' in sensor:
            self._attr_state_class = sensor['state_class']

        self._attr_native_unit_of_measurement = sensor['uom']
        return

