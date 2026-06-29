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

"""Sensor platform for the openSenseMap Advanced integration."""

from typing import override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OpenSenseMapConfigEntry, OpenSenseMapCoordinator


def _determine_device_class(title: str, unit: str) -> SensorDeviceClass | None:
    """Helper to dynamically map sensor titles/units to Home Assistant device classes."""
    title_lower = title.lower()
    unit_lower = unit.lower().strip()

    # Temperature mapping
    if unit_lower in ("°c", "c", "°f", "f", "k") or "temperatur" in title_lower:
        return SensorDeviceClass.TEMPERATURE

    # Humidity mapping
    if unit_lower == "%" and ("humidity" in title_lower or "feuchte" in title_lower or "feuchtigkeit" in title_lower):
        return SensorDeviceClass.HUMIDITY

    # Atmospheric Pressure mapping
    if unit_lower in ("hpa", "pa", "bar", "mbar", "kpa") or "pressure" in title_lower or "luftdruck" in title_lower:
        return SensorDeviceClass.PRESSURE

    # Illuminance mapping
    if unit_lower in ("lx", "lux") or "illuminance" in title_lower or "helligkeit" in title_lower or "licht" in title_lower:
        return SensorDeviceClass.ILLUMINANCE

    # Particulate Matter mapping
    if "µg/m³" in unit_lower or "ug/m³" in unit_lower or "g/m³" in unit_lower:
        if "pm2.5" in title_lower or "pm25" in title_lower or "pm2_5" in title_lower:
            return SensorDeviceClass.PM25
        if "pm10" in title_lower:
            return SensorDeviceClass.PM10
        if "pm1" in title_lower:
            return SensorDeviceClass.PM1

    # Carbon Dioxide mapping
    if unit_lower == "ppm" and "co2" in title_lower:
        return SensorDeviceClass.CO2

    # Wind Speed mapping
    if unit_lower in ("m/s", "km/h", "mph", "kts") or "windgeschwindigkeit" in title_lower or "wind speed" in title_lower:
        return SensorDeviceClass.WIND_SPEED

    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OpenSenseMapConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up openSenseMap sensors dynamically from a config entry."""
    # Check if pulling is enabled for this entry
    if not entry.options.get("pull_enabled", entry.data.get("pull_enabled", True)):
        return

    coordinator = entry.runtime_data.coordinator
    if not coordinator or not coordinator.data:
        return

    # Add entities for all sensors configured on the station
    entities = [
        OpenSenseMapSensor(coordinator, sensor_id)
        for sensor_id in coordinator.data.sensors
    ]
    async_add_entities(entities)


class OpenSenseMapSensor(CoordinatorEntity[OpenSenseMapCoordinator], SensorEntity):
    """Sensor entity representing a single dynamic measurement from an openSenseMap station."""

    _attr_attribution = "Data provided by openSenseMap"
    _attr_has_entity_name = True

    def __init__(self, coordinator: OpenSenseMapCoordinator, sensor_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.sensor_id = sensor_id

        # Use the station ID and sensor ID to generate a unique ID
        self._attr_unique_id = f"opensensemap_sensor_{sensor_id}"

        # Populate static attributes from the initial fetch configurations
        sensor_config = coordinator.data.sensors[sensor_id]
        self._attr_name = sensor_config.title
        self._attr_native_unit_of_measurement = sensor_config.unit or None
        self._attr_device_class = _determine_device_class(sensor_config.title, sensor_config.unit)
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    @override
    def native_value(self) -> float | None:
        """Return the current sensor value."""
        # Safeguard if sensor list dynamically changes or is empty
        if self.sensor_id not in self.coordinator.data.sensors:
            return None
        return self.coordinator.data.sensors[self.sensor_id].value

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional info about the sensor."""
        if self.sensor_id not in self.coordinator.data.sensors:
            return {}
        sensor_config = self.coordinator.data.sensors[self.sensor_id]
        return {
            "sensor_id": self.sensor_id,
            "sensor_type": sensor_config.sensor_type,
            "last_measurement": sensor_config.created_at,
        }

    @property
    @override
    def device_info(self) -> DeviceInfo:
        """Return device details linking all sensors to a single station device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.station_id)},
            name=self.coordinator.data.name,
            model=self.coordinator.data.model,
            manufacturer="openSenseMap",
            configuration_url=f"https://opensensemap.org/explore/{self.coordinator.station_id}",
        )
