# Copyright (c) 2026 nichu42 <nichu42@42bit.email> and contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Config flow and Options flow for openSenseMap Advanced integration."""

from __future__ import annotations

import asyncio
import json
import socket
from typing import Any, override

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_RETAIN_STATE,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ERROR_CANNOT_CONNECT,
    ERROR_INVALID_MAPPINGS,
    ERROR_INVALID_STATION,
)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect to the API."""


class InvalidStation(HomeAssistantError):
    """Error to indicate the station ID is invalid."""


class OpenSenseMapConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for openSenseMap Advanced."""

    VERSION = 1

    async def _async_get_station_name(self, station_id: str) -> str:
        """Query openSenseMap API to verify station exists and retrieve its name."""
        url = f"https://api.opensensemap.org/boxes/{station_id}"
        session = async_get_clientsession(self.hass)

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 404:
                    raise InvalidStation
                if response.status != 200:
                    raise CannotConnect
                data = await response.json()
        except (asyncio.TimeoutError, aiohttp.ClientError, socket.gaierror) as err:
            raise CannotConnect from err

        name = data.get("name")
        if not name:
            raise InvalidStation
        return name

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a user-initiated config flow."""
        errors: dict[str, str] = {}
        if user_input is not None:
            station_id = user_input[CONF_STATION_ID].strip()
            try:
                name = await self._async_get_station_name(station_id)
            except CannotConnect:
                errors["base"] = ERROR_CANNOT_CONNECT
            except InvalidStation:
                errors["base"] = ERROR_INVALID_STATION
            else:
                await self.async_set_unique_id(station_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_STATION_ID: station_id,
                        "pull_enabled": True,
                        "push_enabled": False,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_STATION_ID): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    @override
    def async_get_options_flow(
        config_entry: Any,
    ) -> OpenSenseMapOptionsFlowHandler:
        """Get the options flow for this handler."""
        return OpenSenseMapOptionsFlowHandler()


class OpenSenseMapOptionsFlowHandler(OptionsFlow):
    """Handle openSenseMap Advanced options."""

    @override
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            push_enabled = user_input.get("push_enabled", False)
            api_key = user_input.get("api_key")
            mappings_str = user_input.get("push_mappings_json", "{}").strip()

            # Validation: API key is required if push is enabled
            if push_enabled and not api_key:
                errors["api_key"] = "api_key_required"

            # Validation: Parse and validate JSON string mapping
            if push_enabled or mappings_str != "{}":
                try:
                    mappings = json.loads(mappings_str)
                    if not isinstance(mappings, dict):
                        raise ValueError
                    for k, v in mappings.items():
                        if not isinstance(k, str) or not isinstance(v, str):
                            raise ValueError
                except (json.JSONDecodeError, ValueError):
                    errors["push_mappings_json"] = ERROR_INVALID_MAPPINGS

            if not errors:
                return self.async_create_entry(title="", data=user_input)

        # Retrieve current configuration values
        data = self.config_entry.data
        options = self.config_entry.options

        pull_enabled = options.get("pull_enabled", data.get("pull_enabled", True))
        scan_interval = options.get(
            CONF_SCAN_INTERVAL, data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        retain_state = options.get(CONF_RETAIN_STATE, data.get(CONF_RETAIN_STATE, False))
        push_enabled = options.get("push_enabled", data.get("push_enabled", False))
        api_key = options.get("api_key", data.get("api_key", ""))
        push_mappings_json = options.get("push_mappings_json", data.get("push_mappings_json", "{}"))

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("pull_enabled", default=pull_enabled): bool,
                    vol.Required("scan_interval", default=scan_interval): vol.All(
                        vol.Coerce(int), vol.Range(min=5)
                    ),
                    vol.Required(CONF_RETAIN_STATE, default=retain_state): bool,
                    vol.Required("push_enabled", default=push_enabled): bool,
                    vol.Optional("api_key", default=api_key): str,
                    vol.Optional("push_mappings_json", default=push_mappings_json): str,
                }
            ),
            errors=errors,
        )
