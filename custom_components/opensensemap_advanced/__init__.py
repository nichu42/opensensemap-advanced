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

"""The openSenseMap Advanced integration."""

from dataclasses import dataclass
from typing import Any

from opensensemap_api import OpenSenseMap

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
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
    pull_enabled = entry.options.get("pull_enabled", entry.data.get("pull_enabled", True))
    push_enabled = entry.options.get("push_enabled", entry.data.get("push_enabled", False))

    coordinator = None
    if pull_enabled:
        session = async_get_clientsession(hass)
        api = OpenSenseMap(entry.data[CONF_STATION_ID], session)
        coordinator = OpenSenseMapCoordinator(hass, entry, api)
        await coordinator.async_config_entry_first_refresh()

    push_manager = None
    if push_enabled:
        station_id = entry.data[CONF_STATION_ID]
        api_key = entry.options.get("api_key", entry.data.get("api_key"))
        mappings = entry.options.get("push_mappings", entry.data.get("push_mappings", []))
        if mappings:
            push_manager = OpenSenseMapPushManager(hass, station_id, api_key, mappings)
            push_manager.start()

    entry.runtime_data = OpenSenseMapRuntimeData(
        coordinator=coordinator, push_manager=push_manager
    )

    if pull_enabled:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listen for options changes to update configuration dynamically
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry[OpenSenseMapRuntimeData]) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigEntry[OpenSenseMapRuntimeData]
) -> bool:
    """Unload an openSenseMap Advanced config entry."""
    pull_enabled = entry.options.get("pull_enabled", entry.data.get("pull_enabled", True))

    unload_ok = True
    if pull_enabled:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if entry.runtime_data.push_manager:
        entry.runtime_data.push_manager.stop()

    return unload_ok


async def async_upload_data(
    hass: HomeAssistant,
    station_id: str,
    api_key: str | None,
    data: dict[str, str],
) -> None:
    """Upload measurements to openSenseMap."""
    session = async_get_clientsession(hass)
    url = f"https://api.opensensemap.org/boxes/{station_id}/data"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = api_key

    try:
        async with session.post(url, json=data, headers=headers, timeout=10) as response:
            if response.status not in (200, 201):
                text = await response.text()
                LOGGER.error(
                    "Error uploading data to openSenseMap for box %s: %s (Status: %s)",
                    station_id,
                    text,
                    response.status,
                )
            else:
                LOGGER.debug("Successfully uploaded data to openSenseMap for box %s: %s", station_id, data)
    except Exception as err:
        LOGGER.error("Failed to upload data to openSenseMap for box %s: %s", station_id, err)


class OpenSenseMapPushManager:
    """Manages uploading local sensor data to openSenseMap with debouncing."""

    def __init__(
        self,
        hass: HomeAssistant,
        station_id: str,
        api_key: str | None,
        mappings: list[dict[str, str]],
    ) -> None:
        """Initialize the push manager."""
        self.hass = hass
        self.station_id = station_id
        self.api_key = api_key
        self.mappings = mappings
        self.pending_data: dict[str, str] = {}
        self.unsub_timer: Any = None
        self.unsub_listeners: list[Any] = []

    def start(self) -> None:
        """Start tracking state changes."""
        entity_to_sensor = {m["entity_id"]: m["sensor_id"] for m in self.mappings}

        async def handle_state_change(event: Any) -> None:
            entity_id = event.data["entity_id"]
            new_state = event.data.get("new_state")
            if new_state is None or new_state.state in ("unknown", "unavailable", "none", ""):
                return

            sensor_id = entity_to_sensor.get(entity_id)
            if not sensor_id:
                return

            # Store value
            self.pending_data[sensor_id] = new_state.state

            # Schedule upload if not already scheduled
            if self.unsub_timer is None:
                self.unsub_timer = async_call_later(
                    self.hass, 5, self._async_send_pending
                )

        # Register listeners
        for entity_id in entity_to_sensor:
            unsub = async_track_state_change_event(
                self.hass, entity_id, handle_state_change
            )
            self.unsub_listeners.append(unsub)

    async def _async_send_pending(self, _now: Any) -> None:
        """Send pending data to openSenseMap."""
        self.unsub_timer = None
        if not self.pending_data:
            return

        data_to_send = self.pending_data.copy()
        self.pending_data.clear()

        await async_upload_data(
            self.hass, self.station_id, self.api_key, data_to_send
        )

    def stop(self) -> None:
        """Stop tracking and cancel any pending timers."""
        for unsub in self.unsub_listeners:
            unsub()
        self.unsub_listeners.clear()
        if self.unsub_timer:
            self.unsub_timer()
            self.unsub_timer = None
