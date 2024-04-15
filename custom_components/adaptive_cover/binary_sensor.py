"""Binary Sensor platform for the Adaptive Cover integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SENSOR_TYPE, DOMAIN
from .coordinator import AdaptiveDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Adaptive Cover binary sensor platform."""
    coordinator: AdaptiveDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    binary_sensor = AdaptiveCoverBinarySensor(
        config_entry,
        config_entry.entry_id,
        "Sun Infront",
        False,
        "sun_motion",
        BinarySensorDeviceClass.MOTION,
        coordinator,
    )
    manual_override = AdaptiveCoverBinarySensor(
        config_entry,
        config_entry.entry_id,
        "Manual Override",
        False,
        "manual_override",
        BinarySensorDeviceClass.RUNNING,
        coordinator,
    )
    async_add_entities([binary_sensor, manual_override])


class AdaptiveCoverBinarySensor(
    CoordinatorEntity[AdaptiveDataUpdateCoordinator], BinarySensorEntity
):
    """representation of a Adaptive Cover binary sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        config_entry,
        unique_id: str,
        binary_name: str,
        state: bool,
        key: str,
        device_class: BinarySensorDeviceClass,
        coordinator: AdaptiveDataUpdateCoordinator,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator=coordinator)
        self.type = {
            "cover_blind": "Vertical",
            "cover_awning": "Horizontal",
            "cover_tilt": "Tilt",
        }
        self._key = key
        self._attr_translation_key = key
        self._name = config_entry.data["name"]
        self._device_name = self.type[config_entry.data[CONF_SENSOR_TYPE]]
        self._binary_name = binary_name
        self._attr_unique_id = f"{unique_id}_{binary_name}"
        self._device_id = unique_id
        self._state = state
        self._attr_device_class = device_class
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
        )

    @property
    def name(self):
        """Name of the entity."""
        return f"{self._binary_name} {self._name}"

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self.coordinator.data.states[self._key]

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:  # noqa: D102
        if self._key == "manual_override":
            return {"manual_controlled": self.coordinator.data.states["manual_list"]}
