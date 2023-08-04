from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
import voluptuous as vol
from .const import *
from .solarman import Inverter


SERVICE_WRITE_REGISTER = 'write_holding_register'
PARAM_REGISTER = 'register'
PARAM_VALUE = 'value'



# Register the services one can invoke on the inverter.
# Apart from this, it also need to be defined in the file 
# services.yaml for the Home Assistant UI in "Developer Tools"

   
SERVICE_WRITE_REGISTER_SCHEMA = vol.Schema(
    {
        vol.Required(PARAM_REGISTER): cv.positive_int,
        vol.Required(PARAM_VALUE): cv.positive_int,
    }
) 

def register_services (hass: HomeAssistant, inverter: Inverter ):

    async def write_holding_register(call) -> None:  
        inverter.service_write_holding_register(
            register=call.data.get(PARAM_REGISTER), 
            value=call.data.get(PARAM_VALUE))  
        return    
    
    hass.services.async_register(
        DOMAIN, SERVICE_WRITE_REGISTER, write_holding_register, schema=SERVICE_WRITE_REGISTER_SCHEMA
    )        
    return