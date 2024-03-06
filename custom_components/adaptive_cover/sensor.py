"""Sensor platform for Adaptive Cover integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_SENSOR_TYPE,
    DOMAIN,
)
from .coordinator import AdaptiveDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize Adaptive Cover config entry."""

    name = config_entry.data["name"]
    coordinator: AdaptiveDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    sensor = AdaptiveCoverSensorEntity(
        config_entry.entry_id, hass, config_entry, name, coordinator
    )

    async_add_entities([sensor])


class AdaptiveCoverSensorEntity(
    CoordinatorEntity[AdaptiveDataUpdateCoordinator], SensorEntity
):
    """Adaptive Cover Sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:sun-compass"
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        unique_id: str,
        hass,
        config_entry,
        name: str,
        coordinator: AdaptiveDataUpdateCoordinator,
    ) -> None:
        """Initialize adaptive_cover Sensor."""
        super().__init__(coordinator=coordinator)
        self.type = {
            "cover_blind": "Vertical",
            "cover_awning": "Horizontal",
            "cover_tilt": "Tilt",
        }
        self.data = self.coordinator.data
        self._attr_unique_id = unique_id
        self.hass = hass
        self.config_entry = config_entry
        self._name = name
        self._cover_type = self.config_entry.data["sensor_type"]
        self._sensor_name = "Cover Position"
        self._device_name = self.type[config_entry.data[CONF_SENSOR_TYPE]]

    @property
    def name(self):
        """Name of the entity."""
        return f"{self._sensor_name} {self._name}"

    @property
    def native_value(self) -> str | None:
        """Handle when entity is added."""
        if self.data.climate_mode_toggle:
            return self.data.states["climate"]
        return self.data.states["normal"]

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self._device_name,
        )

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:  # noqa: D102
        return self.data.attributes
