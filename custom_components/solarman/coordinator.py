
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .solarman import Inverter
import async_timeout

class SolarmanSensorCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, logger, name, update_interval, requests, inverter: Inverter):
        super().__init__(hass, logger, name=name, update_interval=update_interval)
        self.inverter = inverter
        self.requests = requests


    async def _async_update_data(self):
        try:
            async with async_timeout.timeout(10):
                self.inverter.get_statistics(self.requests)
                return None
        except Exception as e:
            self.logger.error(f"Error querying inverter: {e}")
            return None
        