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

"""Data update coordinator for the openSenseMap Advanced integration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
import socket
from typing import TYPE_CHECKING, Any, override

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_RETAIN_STATE,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
)

if TYPE_CHECKING:
    from . import OpenSenseMapRuntimeData

OpenSenseMapConfigEntry = ConfigEntry["OpenSenseMapRuntimeData"]


@dataclass
class OpenSenseMapSensorData:
    """Data for a single sensor of an openSenseMap station."""

    id: str
    title: str
    unit: str
    sensor_type: str
    value: float | None
    created_at: str | None


@dataclass
class OpenSenseMapStationData:
    """Structure representing a complete openSenseMap station state."""

    name: str
    station_id: str
    exposure: str | None
    model: str | None
    coordinates: list[float] | None
    sensors: dict[str, OpenSenseMapSensorData]  # Map of sensor_id -> OpenSenseMapSensorData


class OpenSenseMapCoordinator(DataUpdateCoordinator[OpenSenseMapStationData]):
    """Coordinator to manage data updates for an openSenseMap station."""

    config_entry: OpenSenseMapConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: OpenSenseMapConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.station_id = config_entry.data[CONF_STATION_ID]
        self.last_known_data: OpenSenseMapStationData | None = None

        scan_interval = config_entry.options.get(
            CONF_SCAN_INTERVAL,
            config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    @override
    async def _async_update_data(self) -> OpenSenseMapStationData:
        """Fetch the latest station measurements from openSenseMap API."""
        url = f"https://api.opensensemap.org/boxes/{self.station_id}"
        session = async_get_clientsession(self.hass)

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 404:
                    raise UpdateFailed(f"openSenseMap station {self.station_id} not found")
                if response.status != 200:
                    raise UpdateFailed(f"HTTP error {response.status} fetching station data")
                data = await response.json()

        except (asyncio.TimeoutError, aiohttp.ClientError, socket.gaierror) as err:
            # Fallback to last known states if retain_state option is enabled
            retain_state = self.config_entry.options.get(CONF_RETAIN_STATE, False)
            if retain_state and self.last_known_data is not None:
                LOGGER.warning(
                    "Error connecting to openSenseMap API: %s. Retaining last known sensor states.",
                    err,
                )
                return self.last_known_data
            raise UpdateFailed(f"Error communicating with openSenseMap API: {err}") from err

        # Parse station level info
        name = data.get("name", "openSenseMap Station")
        exposure = data.get("exposure")
        model = data.get("model")
        coordinates = data.get("currentLocation", {}).get("coordinates")

        # Parse sensors list
        sensors_dict: dict[str, OpenSenseMapSensorData] = {}
        for sensor in data.get("sensors", []):
            sensor_id = sensor.get("_id")
            if not sensor_id:
                continue

            title = sensor.get("title", "Unknown")
            unit = sensor.get("unit", "")
            sensor_type = sensor.get("sensorType", "")

            # Get last measurement
            last_measurement = sensor.get("lastMeasurement") or {}
            raw_value = last_measurement.get("value")
            created_at = last_measurement.get("createdAt")

            # Try parsing value to float
            value: float | None = None
            if raw_value is not None:
                try:
                    value = float(raw_value)
                except ValueError:
                    LOGGER.warning("Could not convert sensor value '%s' to float", raw_value)

            sensors_dict[sensor_id] = OpenSenseMapSensorData(
                id=sensor_id,
                title=title,
                unit=unit,
                sensor_type=sensor_type,
                value=value,
                created_at=created_at,
            )

        station_data = OpenSenseMapStationData(
            name=name,
            station_id=self.station_id,
            exposure=exposure,
            model=model,
            coordinates=coordinates,
            sensors=sensors_dict,
        )

        self.last_known_data = station_data
        return station_data
