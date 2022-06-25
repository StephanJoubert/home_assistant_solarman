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


def step_user_data_schema(data: dict[str, Any] = {CONF_NAME: SENSOR_PREFIX, CONF_INVERTER_PORT: DEFAULT_PORT_INVERTER, CONF_INVERTER_SERVER_ID: DEFAULT_INVERTER_SERVER_ID, CONF_LOOKUP_FILE: DEFAULT_LOOKUP_FILE}) -> Schema:
    _LOGGER.debug(f'config_flow.py:step_user_data_schema: {data}')
    STEP_USER_DATA_SCHEMA = vol.Schema(
        {
            vol.Required(CONF_NAME, default=data.get(CONF_NAME)): str,
            vol.Required(CONF_INVERTER_HOST, default=data.get(CONF_INVERTER_HOST)): str,
            vol.Required(CONF_INVERTER_SERIAL, default=data.get(CONF_INVERTER_SERIAL)): int,
            vol.Optional(CONF_INVERTER_PORT, default=data.get(CONF_INVERTER_PORT)): int,
            vol.Optional(CONF_INVERTER_SERVER_ID, default=data.get(CONF_INVERTER_SERVER_ID)): int,
            vol.Optional(CONF_LOOKUP_FILE, default=data.get(CONF_LOOKUP_FILE)): vol.In(LOOKUP_FILES),
        },
        extra=vol.PREVENT_EXTRA
    )
    _LOGGER.debug(
        f'config_flow.py:step_user_data_schema: STEP_USER_DATA_SCHEMA: {STEP_USER_DATA_SCHEMA}')
    return STEP_USER_DATA_SCHEMA


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    _LOGGER.debug(f'config_flow.py:validate_input: {data}')

    try:
        getaddrinfo(
            data[CONF_INVERTER_HOST], data[CONF_INVERTER_PORT], family=0, type=0, proto=0, flags=0
        )
    except herror:
        raise InvalidHost
    except gaierror:
        raise CannotConnect
    except TimeoutError:
        raise CannotConnect

    return {"title": data[CONF_INVERTER_HOST]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SolarMAN logger."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        _LOGGER.debug(f'config_flow.py:ConfigFlow.async_step_user: {user_input}')
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=step_user_data_schema()
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except InvalidHost:
            errors["base"] = "invalid_host"
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            _LOGGER.debug(f'config_flow.py:ConfigFlow.async_step_user: validation passed: {user_input}')
            # await self.async_set_unique_id(user_input.device_id) # not sure this is permitted as the user can change the device_id
            # self._abort_if_unique_id_configured()
            return self.async_create_entry(title=info["title"], data=user_input)

        _LOGGER.debug(f'config_flow.py:ConfigFlow.async_step_user: validation failed: {user_input}')

        return self.async_show_form(
            step_id="user",
            data_schema=step_user_data_schema(user_input),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidHost(HomeAssistantError):
    """Error to indicate there is invalid hostname or IP address."""
