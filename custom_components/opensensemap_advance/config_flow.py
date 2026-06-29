# Copyright (c) 2026 nichu42 and contributors <nichu42@42bit.email>
# Originally derived from Home Assistant Core (Copyright (c) The Home Assistant Authors)
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
#
# Original Home Assistant code is licensed under the Apache License 2.0.
# A copy of the Apache License 2.0 can be found in the LICENSE-APACHE file.
# Modifications made by nichu42 and contributors.

"""Config flow for the openSenseMap Advanced integration."""

import json
from typing import Any, override

from opensensemap_api import OpenSenseMap
from opensensemap_api.exceptions import OpenSenseMapError
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_STATION_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ERROR_CANNOT_CONNECT,
    ERROR_INVALID_STATION,
)

DEFAULT_MAPPINGS_JSON = '{\n  "sensor.your_temperature_entity": "OPENSENSEMAP_SENSOR_ID"\n}'


class CannotConnect(HomeAssistantError):
    """Error to indicate the openSenseMap API is unreachable."""


class InvalidStation(HomeAssistantError):
    """Error to indicate the station ID does not exist."""


class OpenSenseMapConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for openSenseMap Advanced."""

    VERSION = 1

    async def _async_get_station_name(self, station_id: str) -> str:
        """Validate the station ID and return its name."""
        session = async_get_clientsession(self.hass)
        api = OpenSenseMap(station_id, session)
        try:
            await api.get_data()
        except OpenSenseMapError as err:
            raise CannotConnect from err
        if not api.data or not api.data.get("name"):
            raise InvalidStation
        return api.data["name"]

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a user-initiated config flow."""
        errors: dict[str, str] = {}
        if user_input is not None:
            station_id = user_input[CONF_STATION_ID]
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
    def async_get_options_flow(
        config_entry: Any,
    ) -> "OpenSenseMapOptionsFlowHandler":
        """Get the options flow for this handler."""
        return OpenSenseMapOptionsFlowHandler(config_entry)


class OpenSenseMapOptionsFlowHandler(OptionsFlow):
    """Handle openSenseMap Advanced options."""

    def __init__(self, config_entry: Any) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

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

            mappings = []
            if push_enabled:
                try:
                    parsed = json.loads(mappings_str)
                    if not isinstance(parsed, dict):
                        raise ValueError
                    for k, v in parsed.items():
                        if not isinstance(k, str) or not isinstance(v, str):
                            raise ValueError
                        mappings.append({"entity_id": k.strip(), "sensor_id": v.strip()})
                except (json.JSONDecodeError, ValueError):
                    errors["base"] = "invalid_mappings_json"

            if not errors:
                return self.async_create_entry(
                    title="",
                    data={
                        "pull_enabled": user_input["pull_enabled"],
                        "scan_interval": user_input["scan_interval"],
                        "retain_state": user_input["retain_state"],
                        "push_enabled": push_enabled,
                        "api_key": api_key,
                        "push_mappings": mappings,
                        "push_mappings_json": mappings_str,
                    },
                )

        # Set default values from current options or configuration
        options = self.config_entry.options
        data = self.config_entry.data

        pull_enabled = options.get("pull_enabled", data.get("pull_enabled", True))
        scan_interval = options.get(
            "scan_interval", data.get("scan_interval", DEFAULT_SCAN_INTERVAL)
        )
        retain_state = options.get("retain_state", data.get("retain_state", False))
        push_enabled = options.get("push_enabled", data.get("push_enabled", False))
        api_key = options.get("api_key", data.get("api_key", ""))
        mappings_json = options.get(
            "push_mappings_json", data.get("push_mappings_json", DEFAULT_MAPPINGS_JSON)
        )

        schema = vol.Schema(
            {
                vol.Required("pull_enabled", default=pull_enabled): bool,
                vol.Required("scan_interval", default=scan_interval): vol.All(
                    vol.Coerce(int), vol.Range(min=5)
                ),
                vol.Required("retain_state", default=retain_state): bool,
                vol.Required("push_enabled", default=push_enabled): bool,
                vol.Optional("api_key", default=api_key): str,
                vol.Optional("push_mappings_json", default=mappings_json): str,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
