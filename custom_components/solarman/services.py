from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.helpers import config_validation as cv, entity_registry, entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.exceptions import ServiceValidationError
import voluptuous as vol
from .const import *
from .solarman import Inverter
import logging

log = logging.getLogger(__name__)

SERVICE_READ_HOLDING_REGISTER            = 'read_holding_register'
SERVICE_READ_MULTIPLE_HOLDING_REGISTERS  = 'read_multiple_holding_registers'
SERVICE_WRITE_HOLDING_REGISTER           = 'write_holding_register'
SERVICE_WRITE_MULTIPLE_HOLDING_REGISTERS = 'write_multiple_holding_registers'
PARAM_DEVICE   = 'device'
PARAM_REGISTER = 'register'
PARAM_COUNT    = 'count'
PARAM_VALUE    = 'value'
PARAM_VALUES   = 'values'


# Register the services one can invoke on the inverter.
# Apart from this, it also need to be defined in the file 
# services.yaml for the Home Assistant UI in "Developer Tools"

SERVICE_READ_REGISTER_SCHEMA = vol.Schema(
    {
        vol.Required(PARAM_DEVICE): vol.All(vol.Coerce(str)),
        vol.Required(PARAM_REGISTER): vol.All(vol.Coerce(int), vol.Range(min=0, max=65535))
    }
)

SERVICE_READ_MULTIPLE_REGISTERS_SCHEMA = vol.Schema(
    {
        vol.Required(PARAM_DEVICE): vol.All(vol.Coerce(str)),
        vol.Required(PARAM_REGISTER): vol.All(vol.Coerce(int), vol.Range(min=0, max=65535)),
        vol.Required(PARAM_COUNT): vol.All(vol.Coerce(int), vol.Range(min=0, max=65535))
    }
)

SERVICE_WRITE_REGISTER_SCHEMA = vol.Schema(
    {
        vol.Required(PARAM_DEVICE): vol.All(vol.Coerce(str)),
        vol.Required(PARAM_REGISTER): vol.All(vol.Coerce(int), vol.Range(min=0, max=65535)),
        vol.Required(PARAM_VALUE): vol.All(vol.Coerce(int), vol.Range(min=0, max=65535)),
    }
)

SERVICE_WRITE_MULTIPLE_REGISTERS_SCHEMA = vol.Schema(
    {
        vol.Required(PARAM_DEVICE): vol.All(vol.Coerce(str)),
        vol.Required(PARAM_REGISTER): vol.All(vol.Coerce(int), vol.Range(min=0, max=65535)),
        vol.Required(PARAM_VALUES): vol.All(cv.ensure_list, [vol.All(vol.Coerce(int), vol.Range(min=0, max=65535))]),
    }
)

def register_services (hass: HomeAssistant ):

    def getInverter(device_id):
        inverter: Inverter | None
        entity_comp: EntityComponent[entity.Entity] | None       
        registry = entity_registry.async_get(hass)
        entries = entity_registry.async_entries_for_device(registry, device_id)
        for entity_reg in entries:
            entity_id = entity_reg.entity_id
            domain = entity_id.partition(".")[0]
            entity_comp = hass.data.get("entity_components", {}).get(domain)
            if entity_comp is None:
                log.info(f'read_holding_register: Component for {entity_id} not loaded')
                continue

            if (entity_obj := entity_comp.get_entity(entity_id)) is None:
                log.info(f'read_holding_register: Entity {entity_id} not found')
                continue

            if (inverter := entity_obj.inverter) is None:
                log.info(f'read_holding_register: Entity {entity_id} has no inverter')
                continue

            break

        return inverter


    async def read_holding_register(call) -> int:
        if (inverter := getInverter(call.data.get(PARAM_DEVICE))) is None:
            raise ServiceValidationError(
                "No communication interface for device found",
                translation_domain=DOMAIN,
                translation_key="no_interface_found"
            )
        
        try:
            response = inverter.service_read_holding_register( register=call.data.get(PARAM_REGISTER) )
        except Exception as e:
            raise ServiceValidationError(
                e,
                translation_domain=DOMAIN,
                translation_key="call_failed"
            )
        
        result = {call.data.get(PARAM_REGISTER): response[0]}
        return result
    
    async def read_multiple_holding_registers(call) -> int:
        if (inverter := getInverter(call.data.get(PARAM_DEVICE))) is None:
            raise ServiceValidationError(
                "No communication interface for device found",
                translation_domain=DOMAIN,
                translation_key="no_interface_found"
            )
        
        try:
            response = inverter.service_read_multiple_holding_registers( 
                register=call.data.get(PARAM_REGISTER),
                 count=call.data.get(PARAM_COUNT) )
        except Exception as e:
            raise ServiceValidationError(
                e,
                translation_domain=DOMAIN,
                translation_key="call_failed"
            )
        
        result = {}
        register=call.data.get(PARAM_REGISTER)
        for i in range(0,call.data.get(PARAM_COUNT)):
            result[register+i] = response[i]
        return result

    async def write_holding_register(call) -> None:
        log.debug(f'write_holding_register: call={call}')
        if (inverter := getInverter(call.data.get(PARAM_DEVICE))) is None:
            raise ServiceValidationError(
                "No communication interface for device found",
                translation_domain=DOMAIN,
                translation_key="no_interface_found",
            )

        try:
            inverter.service_write_holding_register(
                register=call.data.get(PARAM_REGISTER), 
                value=call.data.get(PARAM_VALUE))
        except Exception as e:
            raise ServiceValidationError(
                e,
                translation_domain=DOMAIN,
                translation_key="call_failed"
            )

        return

    async def write_multiple_holding_registers(call) -> None:
        log.debug(f'write_holding_register: call={call}')
        if (inverter := getInverter(call.data.get(PARAM_DEVICE))) is None:
            raise ServiceValidationError(
                "No communication interface for device found",
                translation_domain=DOMAIN,
                translation_key="no_interface_found",
            )

        try:
            inverter.service_write_multiple_holding_registers(
                register=call.data.get(PARAM_REGISTER),
                values=call.data.get(PARAM_VALUES))
        except Exception as e:
            raise ServiceValidationError(
                e,
                translation_domain=DOMAIN,
                translation_key="call_failed"
            )
        
        return

    hass.services.async_register(
        DOMAIN, SERVICE_READ_HOLDING_REGISTER, read_holding_register, schema=SERVICE_READ_REGISTER_SCHEMA, supports_response=SupportsResponse.OPTIONAL
    )

    hass.services.async_register(
        DOMAIN, SERVICE_READ_MULTIPLE_HOLDING_REGISTERS, read_multiple_holding_registers, schema=SERVICE_READ_MULTIPLE_REGISTERS_SCHEMA, supports_response=SupportsResponse.OPTIONAL
    )

    hass.services.async_register(
        DOMAIN, SERVICE_WRITE_HOLDING_REGISTER, write_holding_register, schema=SERVICE_WRITE_REGISTER_SCHEMA
    )

    hass.services.async_register(
        DOMAIN, SERVICE_WRITE_MULTIPLE_HOLDING_REGISTERS, write_multiple_holding_registers, schema=SERVICE_WRITE_MULTIPLE_REGISTERS_SCHEMA
    )
    return
