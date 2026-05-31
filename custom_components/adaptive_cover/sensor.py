"""Sensor platform for Adaptive Cover integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
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
    start = AdaptiveCoverTimeSensorEntity(
        config_entry.entry_id,
        hass,
        config_entry,
        name,
        "Start Sun",
        "start",
        "mdi:sun-clock-outline",
        coordinator,
    )
    end = AdaptiveCoverTimeSensorEntity(
        config_entry.entry_id,
        hass,
        config_entry,
        name,
        "End Sun",
        "end",
        "mdi:sun-clock",
        coordinator,
    )
    control = AdaptiveCoverControlSensorEntity(
        config_entry.entry_id, hass, config_entry, name, coordinator
    )
    climate_diag = AdaptiveCoverClimateDiagSensor(
        config_entry.entry_id, hass, config_entry, name, coordinator
    )
    async_add_entities([sensor, start, end, control, climate_diag])


# ── Base mixin ───────────────────────────────────────────────────────────────

class _AdaptiveCoverBase(CoordinatorEntity[AdaptiveDataUpdateCoordinator], SensorEntity):
    """Shared boilerplate for all Adaptive Cover sensor entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        unique_id: str,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        name: str,
        coordinator: AdaptiveDataUpdateCoordinator,
    ) -> None:
        super().__init__(coordinator=coordinator)
        self._type_label = {
            "cover_blind": "Vertical",
            "cover_awning": "Horizontal",
            "cover_tilt": "Tilt",
        }
        self.coordinator = coordinator
        self.data = coordinator.data
        self.hass = hass
        self.config_entry = config_entry
        self._name = name
        self._device_id = unique_id
        self._device_name = self._type_label[config_entry.data[CONF_SENSOR_TYPE]]

    @callback
    def _handle_coordinator_update(self) -> None:
        self.data = self.coordinator.data
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
        )


# ── Existing entities (unchanged behaviour) ──────────────────────────────────

class AdaptiveCoverSensorEntity(_AdaptiveCoverBase):
    """Adaptive Cover Position Sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:sun-compass"

    def __init__(self, unique_id, hass, config_entry, name, coordinator) -> None:
        super().__init__(unique_id, hass, config_entry, name, coordinator)
        self._sensor_name = "Cover Position"
        self._attr_unique_id = f"{unique_id}_{self._sensor_name}"

    @property
    def name(self):
        return f"{self._sensor_name} {self._name}"

    @property
    def native_value(self) -> str | None:
        return self.data.states["state"]

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:  # noqa: D102
        return self.data.attributes


class AdaptiveCoverTimeSensorEntity(_AdaptiveCoverBase):
    """Adaptive Cover Time Sensor (Start Sun / End Sun)."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        unique_id,
        hass,
        config_entry,
        name,
        sensor_name: str,
        key: str,
        icon: str,
        coordinator,
    ) -> None:
        super().__init__(unique_id, hass, config_entry, name, coordinator)
        self._attr_icon = icon
        self.key = key
        self._sensor_name = sensor_name
        self._attr_unique_id = f"{unique_id}_{sensor_name}"

    @property
    def name(self):
        return f"{self._sensor_name} {self._name}"

    @property
    def native_value(self) -> str | None:
        return self.data.states[self.key]


class AdaptiveCoverControlSensorEntity(_AdaptiveCoverBase):
    """Adaptive Cover Control Method Sensor."""

    _attr_translation_key = "control"

    def __init__(self, unique_id, hass, config_entry, name, coordinator) -> None:
        super().__init__(unique_id, hass, config_entry, name, coordinator)
        self._sensor_name = "Control Method"
        self._attr_unique_id = f"{unique_id}_{self._sensor_name}"

    @property
    def name(self):
        return f"{self._sensor_name} {self._name}"

    @property
    def native_value(self) -> str | None:
        return self.data.states["control"]


# ── NEW: Climate Debug diagnostic sensor ─────────────────────────────────────

class AdaptiveCoverClimateDiagSensor(_AdaptiveCoverBase):
    """Diagnostic sensor exposing every intermediate value of the climate decision tree.

    State = active branch (summer | winter | intermediate | unavailable).
    Attributes = full snapshot of all inputs used in the decision.

    This entity has EntityCategory.DIAGNOSTIC so it appears in the
    "Diagnostic" section of the device page and is hidden from default dashboards.
    It is only created when climate mode is active; if no climate data is
    available the state reports "unavailable".
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:thermometer-lines"

    def __init__(self, unique_id, hass, config_entry, name, coordinator) -> None:
        super().__init__(unique_id, hass, config_entry, name, coordinator)
        self._sensor_name = "Climate Debug"
        self._attr_unique_id = f"{unique_id}_climate_debug"

    @property
    def name(self) -> str:
        return f"{self._sensor_name} {self._name}"

    @property
    def native_value(self) -> str:
        """Return the active branch name, or 'unavailable' when climate mode is off."""
        if self.data.climate_debug is None:
            return "unavailable"
        return self.data.climate_debug.get("active_branch", "unavailable")

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return the full climate decision snapshot.

        Keys exposed:
          is_winter              — bool : room temp < temp_low
          is_summer              — bool : ref temp > temp_high AND outside_high
          is_presence            — bool : presence sensor state
          sun_in_window          — bool : cover.valid (sun in FOV)
          temp_inside            — float|None : raw inside sensor value
          temp_outside           — float|None : raw outside sensor value
          temp_used_winter       — float|None : value actually compared to temp_low
          temp_used_summer       — float|None : value actually compared to temp_high
          temp_low               — float : configured winter threshold
          temp_high              — float : configured summer threshold
          temp_switch            — bool : outside temp used for summer check
          is_sunny               — bool : weather matches sunny conditions
          lux_below_threshold    — bool : lux sensor below threshold
          irradiance_below_threshold — bool : irradiance sensor below threshold
          active_branch          — str  : summer | winter | intermediate
        """
        return self.data.climate_debug
