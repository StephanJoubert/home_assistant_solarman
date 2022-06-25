"""Config flow for SolarMAN logger integration."""
from __future__ import annotations

import logging
from typing import Any
from socket import getaddrinfo, herror, gaierror

import voluptuous as vol
from voluptuous.schema_builder import Schema

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from homeassistant.const import CONF_NAME
from .const import *
from .scanner import InverterScanner

_LOGGER = logging.getLogger(__name__)


def get_data_schema(data: dict[str, Any] = None) -> Schema:
    """Generate a data schema."""
    if data is None:
        data = {}

    data_schema = vol.Schema(
        {
            vol.Required(CONF_NAME, default=data.get(CONF_NAME, SENSOR_PREFIX)): str,
            vol.Required(CONF_INVERTER_HOST, default=data.get(CONF_INVERTER_HOST, DEFAULT_INVERTER_HOST)): str,
            vol.Required(CONF_INVERTER_SERIAL_NUMBER, default=data.get(CONF_INVERTER_SERIAL_NUMBER, DEFAULT_INVERTER_SERIAL_NUMBER)): int,
            vol.Optional(CONF_INVERTER_PORT, default=data.get(CONF_INVERTER_PORT, DEFAULT_INVERTER_PORT)): int,
            vol.Optional(CONF_INVERTER_SERVER_ID, default=data.get(CONF_INVERTER_SERVER_ID, DEFAULT_INVERTER_SERVER_ID)): int,
            vol.Optional(CONF_LOOKUP_FILE, default=data.get(CONF_LOOKUP_FILE, DEFAULT_LOOKUP_FILE)): vol.In(LOOKUP_FILES),
        },
        extra=vol.PREVENT_EXTRA
    )
    return data_schema


async def validate_input(host, port):
    """Validate the host and port allows us to connect."""
    # TODO: is this actually async ?
    try:
        getaddrinfo(
            host, port, family=0, type=0, proto=0, flags=0
        )
    except herror:
        raise InvalidHost
    except gaierror or TimeoutError:
        raise CannotConnect


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for SolarMAN logger."""

    VERSION = 1

    async def __init__(self):
        """Initialize the config flow."""
        self._scanner = InverterScanner()    

    def _sync_get_ip_address(self):
        """Get the IP address."""
        return self._scanner.get_ipaddress()

    def _sync_get_serial_number(self):
        """Get the serial number."""
        return self._scanner.get_serialno()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=get_data_schema()
            )

        errors = {}

        if user_input[CONF_INVERTER_HOST] == DEFAULT_INVERTER_HOST:
            user_input[CONF_INVERTER_HOST] = await self.hass.async_add_executor_job(self._sync_get_ip_address)

        if user_input[CONF_INVERTER_SERIAL_NUMBER] == DEFAULT_INVERTER_SERIAL_NUMBER:
            user_input[CONF_INVERTER_SERIAL_NUMBER] = await self.hass.async_add_executor_job(self._sync_get_serial_number)
        # TODO:  think about validation a bit more....should serial # go after validate_input?


        try:
            await validate_input(user_input[CONF_INVERTER_HOST], user_input[CONF_INVERTER_PORT])
        except InvalidHost:
            errors["base"] = "invalid_host"
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            # await self.async_set_unique_id(user_input.device_id) # not sure this is permitted as the user can change the device_id
            # self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_INVERTER_HOST], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=get_data_schema(user_input),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidHost(HomeAssistantError):
    """Error to indicate there is invalid hostname or IP address."""
