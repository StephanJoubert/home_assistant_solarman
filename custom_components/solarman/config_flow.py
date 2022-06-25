"""Config flow for SolarMAN logger integration."""
from __future__ import annotations

import logging
from typing import Any
from socket import getaddrinfo, herror, gaierror

import voluptuous as vol
from voluptuous.schema_builder import Schema

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from homeassistant.const import CONF_NAME
import homeassistant.helpers.config_validation as cv
from .const import *

_LOGGER = logging.getLogger(__name__)


def get_data_schema(data: dict[str, Any] = None) -> Schema:
    """Generate a data schema."""
    if data is None:
        data = {}

    data_schema = vol.Schema(
        {
            vol.Required(CONF_NAME, default=data.get(CONF_NAME, SENSOR_PREFIX)): str,
            vol.Required(CONF_INVERTER_HOST, default=data.get(CONF_INVERTER_HOST, DEFAULT_PORT_INVERTER)): str,
            vol.Required(CONF_INVERTER_SERIAL, default=data.get(CONF_INVERTER_SERIAL)): int,
            vol.Optional(CONF_INVERTER_PORT, default=data.get(CONF_INVERTER_PORT)): int,
            vol.Optional(CONF_INVERTER_SERVER_ID, default=data.get(CONF_INVERTER_SERVER_ID, DEFAULT_INVERTER_SERVER_ID)): int,
            vol.Optional(CONF_LOOKUP_FILE, default=data.get(CONF_LOOKUP_FILE, DEFAULT_LOOKUP_FILE)): vol.In(LOOKUP_FILES),
        },
        extra=vol.PREVENT_EXTRA
    )
    return data_schema


async def validate_input(host, port):
    """Validate the host and port allows us to connect."""
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

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=get_data_schema()
            )

        errors = {}

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
