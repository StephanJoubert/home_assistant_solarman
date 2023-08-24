from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
import voluptuous as vol
from .const import *
from .solarman import Inverter


SERVICE_WRITE_REGISTER = 'write_holding_register'
SERVICE_WRITE_MULTIPLE_REGISTERS = 'write_multiple_holding_registers'
PARAM_REGISTER = 'register'
PARAM_VALUE = 'value'
PARAM_VALUES = 'values'



# Register the services one can invoke on the inverter.
# Apart from this, it also need to be defined in the file 
# services.yaml for the Home Assistant UI in "Developer Tools"


SERVICE_WRITE_REGISTER_SCHEMA = vol.Schema(
    {
        vol.Required(PARAM_REGISTER): vol.All(vol.Coerce(int), vol.Range(min=0, max=65535)),
        vol.Required(PARAM_VALUE): vol.All(vol.Coerce(int), vol.Range(min=0, max=65535)),
    }
)

SERVICE_WRITE_MULTIPLE_REGISTERS_SCHEMA = vol.Schema(
    {
        vol.Required(PARAM_REGISTER): vol.All(vol.Coerce(int), vol.Range(min=0, max=65535)),
        vol.Required(PARAM_VALUES): vol.All(cv.ensure_list, [vol.All(vol.Coerce(int), vol.Range(min=0, max=65535))]),
    }
)

def register_services (hass: HomeAssistant, inverter: Inverter ):

    async def write_holding_register(call) -> None:
        inverter.service_write_holding_register(
            register=call.data.get(PARAM_REGISTER), 
            value=call.data.get(PARAM_VALUE))
        return

    async def write_multiple_holding_registers(call) -> None:
        inverter.service_write_multiple_holding_registers(
            register=call.data.get(PARAM_REGISTER),
            values=call.data.get(PARAM_VALUES))
        return

    hass.services.async_register(
        DOMAIN, SERVICE_WRITE_REGISTER, write_holding_register, schema=SERVICE_WRITE_REGISTER_SCHEMA
    )

    hass.services.async_register(
        DOMAIN, SERVICE_WRITE_MULTIPLE_REGISTERS, write_multiple_holding_registers, schema=SERVICE_WRITE_MULTIPLE_REGISTERS_SCHEMA
    )
    return
