"""The Solarman Collector integration."""

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .solarman import Inverter
from .const import *

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor"]
SCAN_INTERVAL = timedelta(seconds=30)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Solarman Collector from a config entry."""
    _LOGGER.debug(f'__init__.py:async_setup_entry({entry.as_dict()})')

    conf = entry.data

    inverter_name = conf[CONF_NAME]
    inverter_host = conf[CONF_INVERTER_HOST]
    inverter_port = conf[CONF_INVERTER_PORT]
    inverter_sn = conf[CONF_INVERTER_SERIAL_NUMBER]
    
    inverter_server_id = conf[CONF_INVERTER_SERVER_ID]
    lookup_file = conf[CONF_LOOKUP_FILE]
    path = hass.config.path('custom_components/solarman/inverter_definitions/')

    inverter = Inverter(path, inverter_sn, inverter_host, inverter_port, inverter_server_id, lookup_file, name=inverter_name)

    coordinator = SolarmanDataUpdateCoordinator(hass, inverter)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug(f'__init__.py:async_unload_entry({entry.as_dict()})')
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

class SolarmanDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to fetch data from Solarman."""

    def __init__(self, hass: HomeAssistant, inverter):
        """Initialize."""
        self.hass = hass
        self.inverter = inverter
        super().__init__(
            hass, logger=_LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL
        )

    async def _async_update_data(self):
        """Update data."""
        await self.hass.async_add_executor_job(self._sync_update_data)

    def _sync_update_data(self):
        """Fetch synchronous data from Solarman."""
        # TODO: error catching
        self.inverter.update()