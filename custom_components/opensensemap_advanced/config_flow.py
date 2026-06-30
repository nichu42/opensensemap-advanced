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
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_PUSH_INTERVAL,
    CONF_RETAIN_STATE,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    DEFAULT_PUSH_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ERROR_CANNOT_CONNECT,
    ERROR_INVALID_STATION,
)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect to the API."""


class InvalidStation(HomeAssistantError):
    """Error to indicate the station ID is invalid."""


def _determine_selector_device_class(title: str, unit: str) -> str | None:
    """Determine the Home Assistant device class for filtering entity selector."""
    title_lower = title.lower()
    unit_lower = unit.lower()

    if "temp" in title_lower or unit_lower in ("°c", "°f", "k"):
        return "temperature"
    if "humid" in title_lower or unit_lower == "%":
        if "batt" in title_lower:
            return "battery"
        return "humidity"
    if "pressure" in title_lower or unit_lower in ("hpa", "pa", "bar"):
        return "pressure"
    if "lux" in unit_lower or "lx" in unit_lower or "light" in title_lower or "illu" in title_lower:
        return "illuminance"
    if "pm2.5" in title_lower or "pm25" in title_lower:
        return "pm25"
    if "pm10" in title_lower:
        return "pm10"
    if "pm1" in title_lower:
        return "pm1"
    if "co2" in title_lower or "carbon dioxide" in title_lower:
        return "carbon_dioxide"
    if "co" in title_lower or "carbon monoxide" in title_lower:
        return "carbon_monoxide"
    if "no2" in title_lower or "nitrogen dioxide" in title_lower:
        return "nitrogen_dioxide"
    if "aqi" in title_lower or "air quality" in title_lower:
        return "aqi"
    if "voltage" in title_lower or unit_lower in ("v", "mv"):
        return "voltage"
    if "batt" in title_lower or "akku" in title_lower:
        return "battery"
    if "wind" in title_lower or unit_lower in ("m/s", "km/h", "mph"):
        return "wind_speed"
    return None


class OpenSenseMapConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for openSenseMap Advanced."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()
        self.station_id: str = ""
        self.station_name: str = ""
        self.pull_enabled: bool = True
        self.push_enabled: bool = False
        self.api_key: str = ""
        self.station_sensors: list[dict[str, Any]] = []

        # Target mappings to build: ha_entity_id -> opensensemap_sensor_id
        self.push_mappings: dict[str, str] = {}
        self.current_sensor_index: int = 0

        self.scan_interval: int = DEFAULT_SCAN_INTERVAL
        self.retain_state: bool = False

    async def _async_get_station_details(self, station_id: str) -> tuple[str, list[dict[str, Any]]]:
        """Query openSenseMap API to verify station and retrieve its details."""
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
        sensors = data.get("sensors", [])
        if not name:
            raise InvalidStation
        return name, sensors

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle welcome and mode selection step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            raw_input = user_input[CONF_STATION_ID].strip()
            # If the user pasted a full URL, extract the last path segment (Station ID)
            # URL format: https://opensensemap.org/explore/62f77dc305b75c001bb659fe
            if "opensensemap.org" in raw_input:
                clean_url = raw_input.rstrip("/")
                self.station_id = clean_url.split("/")[-1].split("?")[0].strip()
            else:
                self.station_id = raw_input

            self.pull_enabled = user_input.get("pull_enabled", True)
            self.push_enabled = user_input.get("push_enabled", False)

            if not self.pull_enabled and not self.push_enabled:
                errors["base"] = "select_at_least_one_mode"

            if not errors:
                try:
                    self.station_name, self.station_sensors = await self._async_get_station_details(
                        self.station_id
                    )
                except CannotConnect:
                    errors["base"] = ERROR_CANNOT_CONNECT
                except InvalidStation:
                    errors["base"] = ERROR_INVALID_STATION
                else:
                    await self.async_set_unique_id(self.station_id)
                    self._abort_if_unique_id_configured()

                    if self.push_enabled:
                        return await self.async_step_push_api_key()
                    if self.pull_enabled:
                        return await self.async_step_pull_config()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATION_ID, default=self.station_id): str,
                    vol.Required("pull_enabled", default=self.pull_enabled): bool,
                    vol.Required("push_enabled", default=self.push_enabled): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_push_api_key(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle entering push API Key."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.api_key = user_input.get("api_key", "").strip()
            if not self.api_key:
                errors["api_key"] = "api_key_required"

            if not errors:
                self.current_sensor_index = 0
                self.push_mappings = {}
                return await self.async_step_push_config()

        return self.async_show_form(
            step_id="push_api_key",
            data_schema=vol.Schema(
                {
                    vol.Required("api_key", default=self.api_key): str,
                }
            ),
            errors=errors,
        )

    async def async_step_push_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle step-by-step mapping of senseBox sensors to HA entities."""
        if user_input is not None:
            entity_id = user_input.get("entity_id")
            sensor = self.station_sensors[self.current_sensor_index]

            # Save the mapping if an entity was selected
            if entity_id:
                self.push_mappings[entity_id] = sensor["_id"]

            self.current_sensor_index += 1

        # Check if we have more sensors to map
        if self.current_sensor_index < len(self.station_sensors):
            sensor = self.station_sensors[self.current_sensor_index]
            sensor_name = sensor.get("title", "Sensor")
            sensor_type = sensor.get("sensorType", "")
            sensor_unit = sensor.get("unit", "")

            # Restrict dropdown list to matching device class if detected
            device_class = _determine_selector_device_class(sensor_name, sensor_unit)
            selector_config: dict[str, Any] = {"domain": "sensor"}
            if device_class:
                selector_config["device_class"] = device_class

            # Show form for the current sensor
            return self.async_show_form(
                step_id="push_config",
                data_schema=vol.Schema(
                    {
                        vol.Optional("entity_id"): selector.EntitySelector(
                            selector.EntitySelectorConfig(**selector_config)
                        ),
                    }
                ),
                description_placeholders={
                    "sensor_name": sensor_name,
                    "sensor_type": sensor_type or "Unknown type",
                    "sensor_unit": sensor_unit or "No Unit",
                },
            )

        # All sensors mapped, proceed to pull config or finish
        if self.pull_enabled:
            return await self.async_step_pull_config()
        return self._async_create_entry()

    async def async_step_pull_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle pull configuration step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.scan_interval = user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL)
            self.retain_state = user_input.get("retain_state", False)
            return self._async_create_entry()

        return self.async_show_form(
            step_id="pull_config",
            data_schema=vol.Schema(
                {
                    vol.Required("scan_interval", default=self.scan_interval): vol.All(
                        vol.Coerce(int), vol.Range(min=5)
                    ),
                    vol.Required("retain_state", default=self.retain_state): bool,
                }
            ),
            errors=errors,
        )

    def _async_create_entry(self) -> ConfigFlowResult:
        """Helper to create the config entry."""
        return self.async_create_entry(
            title=self.station_name,
            data={
                CONF_STATION_ID: self.station_id,
            },
            options={
                "pull_enabled": self.pull_enabled,
                "scan_interval": self.scan_interval,
                "retain_state": self.retain_state,
                "push_enabled": self.push_enabled,
                "api_key": self.api_key,
                "push_mappings_json": json.dumps(self.push_mappings),
                CONF_PUSH_INTERVAL: DEFAULT_PUSH_INTERVAL,
            },
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

    def __init__(self) -> None:
        """Initialize the options flow."""
        super().__init__()
        self.new_options: dict[str, Any] = {}
        self.station_sensors: list[dict[str, Any]] = []
        self.push_mappings: dict[str, str] = {}
        self.current_sensor_index: int = 0

    async def _async_get_station_sensors(self, station_id: str) -> list[dict[str, Any]]:
        """Query openSenseMap API to retrieve sensors list."""
        url = f"https://api.opensensemap.org/boxes/{station_id}"
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("sensors", [])
        except Exception:
            pass
        return []

    @override
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the initial options screen."""
        errors: dict[str, str] = {}

        if user_input is not None:
            push_enabled = user_input.get("push_enabled", False)
            api_key = user_input.get("api_key", "").strip()

            if push_enabled and not api_key:
                errors["api_key"] = "api_key_required"

            if not errors:
                self.new_options = dict(user_input)
                if push_enabled:
                    # Fetch sensors to set up mapping
                    self.station_sensors = await self._async_get_station_sensors(
                        self.config_entry.data[CONF_STATION_ID]
                    )
                    self.current_sensor_index = 0
                    self.push_mappings = {}
                    return await self.async_step_push_config()
                else:
                    self.new_options["push_mappings_json"] = "{}"
                    return self.async_create_entry(title="", data=self.new_options)

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
        push_interval = options.get(
            CONF_PUSH_INTERVAL, data.get(CONF_PUSH_INTERVAL, DEFAULT_PUSH_INTERVAL)
        )

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
                    vol.Required(CONF_PUSH_INTERVAL, default=push_interval): vol.All(
                        vol.Coerce(int), vol.Range(min=5)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_push_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle step-by-step mapping in options flow."""
        if user_input is not None:
            entity_id = user_input.get("entity_id")
            sensor = self.station_sensors[self.current_sensor_index]

            if entity_id:
                self.push_mappings[entity_id] = sensor["_id"]

            self.current_sensor_index += 1

        # Check if we have more sensors to map
        if self.current_sensor_index < len(self.station_sensors):
            sensor = self.station_sensors[self.current_sensor_index]
            sensor_id = sensor["_id"]
            sensor_name = sensor.get("title", "Sensor")
            sensor_type = sensor.get("sensorType", "")
            sensor_unit = sensor.get("unit", "")

            # Look up current mapped entity for default value in selector
            # The current mappings dict in options is ha_entity_id -> opensensemap_sensor_id
            try:
                current_mappings = json.loads(
                    self.config_entry.options.get("push_mappings_json", "{}")
                )
            except json.JSONDecodeError:
                current_mappings = {}

            # Invert mappings dict to find: opensensemap_sensor_id -> ha_entity_id
            current_mappings_inverted = {v: k for k, v in current_mappings.items()}
            default_entity = current_mappings_inverted.get(sensor_id, vol.UNDEFINED)

            # Restrict dropdown list to matching device class if detected
            device_class = _determine_selector_device_class(sensor_name, sensor_unit)
            selector_config: dict[str, Any] = {"domain": "sensor"}
            if device_class:
                selector_config["device_class"] = device_class

            return self.async_show_form(
                step_id="push_config",
                data_schema=vol.Schema(
                    {
                        vol.Optional("entity_id", default=default_entity): selector.EntitySelector(
                            selector.EntitySelectorConfig(**selector_config)
                        ),
                    }
                ),
                description_placeholders={
                    "sensor_name": sensor_name,
                    "sensor_type": sensor_type or "Unknown type",
                    "sensor_unit": sensor_unit or "No Unit",
                },
            )

        # Save all options on completion
        self.new_options["push_mappings_json"] = json.dumps(self.push_mappings)
        return self.async_create_entry(title="", data=self.new_options)
