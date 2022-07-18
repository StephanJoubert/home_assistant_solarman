"""Interface with Solarman sensors."""

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
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
    """Generic Solarman sensor entity."""

    def __init__(self, inverter, field_name):
        """Initialize."""
        self.inverter = inverter
        self._field_name = field_name
        self._inverter_name = inverter.name
        self._serial_number = inverter.serial_number
        self._attr_icon = "mdi:magnify"
        self._attr_name = "{} {}".format(self._inverter_name, field_name)
        self._attr_unique_id = "{}_{}_{}".format(
            self._inverter_name, self._serial_number, field_name
        )

    def update(self):
        """Update this sensor using the data."""
        self._attr_state = getattr(self.inverter, self._field_name)


class SolarmanSensorText(SolarmanStatus):
    """Entity displaying a text field read from the inverter."""

    def __init__(self, inverter, sensor):
        """Initialize."""
        SolarmanStatus.__init__(self, inverter, sensor["name"])
        if "icon" in sensor:
            self._attr_icon = sensor["icon"]

    def update(self):
        """Update this sensor using the data."""
        self.inverter.update()

        val = self.inverter.get_current_val()
        if val is not None:
            if self._field_name in val:
                self._attr_state = val[self._field_name]


class SolarmanSensor(SolarmanSensorText):
    """Entity displaying a numeric field read from the inverter."""

    def __init__(self, inverter, sensor):
        """Initialize."""
        SolarmanSensorText.__init__(self, inverter, sensor)
        self._attr_device_class = sensor["class"]
        if "state_class" in sensor:
            self._attr_state_class = sensor["state_class"]

        self._attr_native_unit_of_measurement = sensor["uom"]
        return
