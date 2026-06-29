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

"""The openSenseMap Advanced integration."""

import asyncio
from dataclasses import dataclass
import json
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later, async_track_state_change_event

from .const import CONF_STATION_ID, DOMAIN, LOGGER
from .coordinator import OpenSenseMapCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


@dataclass
class OpenSenseMapRuntimeData:
    """Runtime data for the openSenseMap Advanced integration."""

    coordinator: OpenSenseMapCoordinator | None = None
    push_manager: "OpenSenseMapPushManager" | None = None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry[OpenSenseMapRuntimeData]
) -> bool:
    """Set up openSenseMap Advanced from a config entry."""
    station_id = entry.data[CONF_STATION_ID]
    options = entry.options

    pull_enabled = options.get("pull_enabled", entry.data.get("pull_enabled", True))
    push_enabled = options.get("push_enabled", entry.data.get("push_enabled", False))

    coordinator = None
    if pull_enabled:
        coordinator = OpenSenseMapCoordinator(hass, entry)
        await coordinator.async_config_entry_first_refresh()

    push_manager = None
    if push_enabled:
        api_key = options.get("api_key", entry.data.get("api_key", ""))
        mappings_str = options.get("push_mappings_json", entry.data.get("push_mappings_json", "{}"))
        try:
            mappings = json.loads(mappings_str)
        except json.JSONDecodeError:
            mappings = {}

        if api_key and mappings:
            push_manager = OpenSenseMapPushManager(hass, station_id, api_key, mappings)
            push_manager.start()

    entry.runtime_data = OpenSenseMapRuntimeData(
        coordinator=coordinator, push_manager=push_manager
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listen to options flow updates
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigEntry[OpenSenseMapRuntimeData]
) -> bool:
    """Unload a config entry."""
    # Stop push manager listeners if active
    if entry.runtime_data.push_manager:
        entry.runtime_data.push_manager.stop()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_update_options(
    hass: HomeAssistant, entry: ConfigEntry[OpenSenseMapRuntimeData]
) -> None:
    """Handle options updates by reloading the integration."""
    LOGGER.info("Options updated, reloading openSenseMap Advanced integration")
    await hass.config_entries.async_reload(entry.entry_id)


class OpenSenseMapPushManager:
    """Manages batching and pushing local Home Assistant sensor states to openSenseMap API."""

    def __init__(
        self,
        hass: HomeAssistant,
        station_id: str,
        api_key: str,
        mappings: dict[str, str],
    ) -> None:
        """Initialize the push manager."""
        self._hass = hass
        self._station_id = station_id
        self._api_key = api_key
        self._mappings = mappings  # dict of ha_entity_id -> opensensemap_sensor_id

        self._buffer: dict[str, float] = {}
        self._unsub_listeners: list[Any] = []
        self._unsub_push: Any = None

    def start(self) -> None:
        """Start listening to state changes on mapped entities."""
        self.stop()
        LOGGER.info(
            "Starting openSenseMap push exporter for station %s with %d entity mappings",
            self._station_id,
            len(self._mappings),
        )

        for entity_id in self._mappings:
            unsub = async_track_state_change_event(
                self._hass, entity_id, self._handle_state_change
            )
            self._unsub_listeners.append(unsub)

    def stop(self) -> None:
        """Stop listening and clear schedules."""
        if self._unsub_push:
            self._unsub_push()
            self._unsub_push = None

        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()
        self._buffer.clear()

    @callback
    def _handle_state_change(self, event: Event) -> None:
        """Process a state change event, buffering the new numeric value."""
        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")

        if not entity_id or not new_state or new_state.state in ("unavailable", "unknown"):
            return

        try:
            value = float(new_state.state)
        except ValueError:
            # Skip if the state is not a parseable number
            return

        sensor_id = self._mappings.get(entity_id)
        if not sensor_id:
            return

        self._buffer[sensor_id] = value

        # Schedule push if not already scheduled
        if not self._unsub_push:
            self._unsub_push = async_call_later(self._hass, 5, self._async_push_data)

    async def _async_push_data(self, *_: Any) -> None:
        """Send all buffered measurements in a single POST request."""
        self._unsub_push = None
        if not self._buffer:
            return

        payload = dict(self._buffer)
        self._buffer.clear()

        url = f"https://api.opensensemap.org/boxes/{self._station_id}/data"
        headers = {
            "Authorization": self._api_key,
            "Content-Type": "application/json",
        }
        session = async_get_clientsession(self._hass)

        LOGGER.debug("Pushing measurements to openSenseMap: %s", payload)

        try:
            async with session.post(
                url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 201 or response.status == 200:
                    LOGGER.info(
                        "Successfully uploaded %d measurements to openSenseMap station %s",
                        len(payload),
                        self._station_id,
                    )
                else:
                    text = await response.text()
                    LOGGER.error(
                        "Error uploading data (HTTP %d): %s",
                        response.status,
                        text,
                    )
        except Exception as err:
            LOGGER.error("Failed to push data to openSenseMap API: %s", err)
