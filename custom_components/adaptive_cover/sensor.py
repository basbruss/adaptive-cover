"""Sensor platform for Adaptive Cover integration."""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import EventType
from homeassistant.helpers.event import (
    EventStateChangedData,
    async_track_state_change_event,
)
from .helpers import get_safe_state, get_domain
from .calculation import (
    AdaptiveVerticalCover,
    AdaptiveHorizontalCover,
    AdaptiveTiltCover,
    NormalCoverState,
    ClimateCoverState,
    ClimateCoverData,
)

from .const import (
    CONF_AZIMUTH,
    CONF_HEIGHT_WIN,
    CONF_DISTANCE,
    CONF_DEFAULT_HEIGHT,
    CONF_FOV_LEFT,
    CONF_FOV_RIGHT,
    CONF_ENTITIES,
    CONF_LENGTH_AWNING,
    CONF_AWNING_ANGLE,
    CONF_INVERSE_STATE,
    CONF_SENSOR_TYPE,
    CONF_SUNSET_POS,
    CONF_SUNSET_OFFSET,
    CONF_TILT_DEPTH,
    CONF_TILT_DISTANCE,
    CONF_TILT_MODE,
    CONF_TEMP_LOW,
    CONF_TEMP_HIGH,
    CONF_MODE,
    CONF_WEATHER_STATE
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize Adaptive Cover config entry."""

    name = config_entry.data["name"]
    data = AdaptiveCoverData(
        hass,
        config_entry,
    )

    sensor = AdaptiveCoverSensorEntity(
        config_entry.entry_id, hass, config_entry, name, data
    )

    async_add_entities([sensor], False)


class AdaptiveCoverSensorEntity(SensorEntity):
    """adaptive_cover Sensor."""

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
        cover_data: AdaptiveCoverData,
    ) -> None:
        """Initialize adaptive_cover Sensor."""
        type = {
            "cover_blind": "Vertical",
            "cover_awning": "Horizontal",
            "cover_tilt": "Tilt",
        }

        self.data = self.coordinator.data
        self._attr_unique_id = unique_id
        self.hass = hass
        self.config_entry = config_entry
        self._cover_data = cover_data
        self._cover_type = self.config_entry.data["sensor_type"]
        self._attr_name = f"Adaptive Cover {name if name != 'Adaptive Cover' else ''} {type[self._cover_type]}"
        self._name = self._attr_name
        self._mode = self.config_entry.data.get(CONF_MODE, "basic")
        self._temp_entity = self.config_entry.options.get("temp_entity", None)
        self._presence_entity = self.config_entry.options.get("presence_entity", None)
        self._weather_entity = self.config_entry.options.get("weather_entity", None)
        self._entities = ["sun.sun"]
        for entity in [self._temp_entity, self._presence_entity, self._weather_entity]:
            if entity is not None:
                self._entities.append(entity)

    @callback
    def async_on_state_change(self, event: EventType[EventStateChangedData]) -> None:
        """Update supported features and state when a new state is received."""
        self.async_set_context(event.context)

        self.async_update_state()

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""
        async_track_state_change_event(
            self.hass, self._entities, self.async_on_state_change
        )
        self.async_update_state()

    @callback
    def async_update_state(self) -> None:
        """Determine state after push."""
        self._cover_data.update()
        if self._mode == "climate":
            self._cover_data.update_climate()
        if self._cover_type == "cover_blind":
            self._cover_data.update_vertical()
        if self._cover_type == "cover_awning":
            self._cover_data.update_horizontal()
        if self._cover_type == "cover_tilt":
            self._cover_data.update_tilt()

        self.async_write_ha_state()

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


class AdaptiveCoverData:
    """Adaptive Cover data Collector."""

    def __init__(  # noqa: D107
        self,
        hass,
        config_entry: ConfigEntry,
    ) -> None:
        self.hass = hass
        self.config_entry = config_entry
        self.sensor_type = self.config_entry.data[CONF_SENSOR_TYPE]
        self._mode = None
        self.calculated_state = None
        self.sol_azi = None
        self.sol_elev = None
        self.timezone = self.hass.config.time_zone
        self.distance = 0.5
        self.h_def = 60
        self.h_win = 2.1
        self.awn_length = 2.1
        self.awn_angle = 0
        self.start = None
        self.end = None
        self.sunset_pos = 0
        self.sunset_off = 0
        self.slat_distance = 2
        self.depth = 3
        self.tilt_mode = "mode2"
        self.fov_left = self.config_entry.options[CONF_FOV_LEFT]
        self.fov_right = self.config_entry.options[CONF_FOV_RIGHT]
        self.fov = [self.fov_left, self.fov_right]
        self.win_azi = 180
        self.inverse_state = False
        self._state = None
        self.current_temp = None
        self.temp_low = None
        self.temp_high = None
        self.presence = None
        self.presence_entity = None
        self.weather_entity = None
        self.weather_state = None
        self.weather_condition = None
        self.climate_state = None
        self.climate_data = None

    def update(self):
        """Update all common parameters."""
        self.inverse_state = self.config_entry.options[CONF_INVERSE_STATE]
        self.sol_azi = self.hass.states.get("sun.sun").attributes["azimuth"]
        self.sol_elev = self.hass.states.get("sun.sun").attributes["elevation"]
        self.sunset_pos = self.config_entry.options[CONF_SUNSET_POS]
        self.sunset_off = self.config_entry.options[CONF_SUNSET_OFFSET]
        self.timezone = self.hass.config.time_zone
        self.fov_left = self.config_entry.options[CONF_FOV_LEFT]
        self.fov_right = self.config_entry.options[CONF_FOV_RIGHT]
        self.fov = [self.fov_left, self.fov_right]
        self.win_azi = self.config_entry.options[CONF_AZIMUTH]
        self.h_def = self.config_entry.options[CONF_DEFAULT_HEIGHT]
        self._mode = self.config_entry.data.get(CONF_MODE, "basic")

    def update_vertical(self):
        """Update values for vertical blind."""
        self.distance = self.config_entry.options[CONF_DISTANCE]
        self.h_win = self.config_entry.options[CONF_HEIGHT_WIN]
        vertical = AdaptiveVerticalCover(
            self.hass,
            self.sol_azi,
            self.sol_elev,
            self.sunset_pos,
            self.sunset_off,
            self.timezone,
            self.fov_left,
            self.fov_right,
            self.win_azi,
            self.h_def,
            self.distance,
            self.h_win,
        )

        state = NormalCoverState(vertical)
        if self.climate_data is not None:
            state = ClimateCoverState(vertical, self.climate_data)
        self.calculated_state = state.get_state()

        self.start, self.end = vertical.solar_times()

    def update_horizontal(self):
        """Update values for horizontal blind."""
        self.awn_length = self.config_entry.options[CONF_LENGTH_AWNING]
        self.awn_angle = self.config_entry.options[CONF_AWNING_ANGLE]
        horizontal = AdaptiveHorizontalCover(
            self.hass,
            self.sol_azi,
            self.sol_elev,
            self.sunset_pos,
            self.sunset_off,
            self.timezone,
            self.fov_left,
            self.fov_right,
            self.win_azi,
            self.h_def,
            self.distance,
            self.h_win,
            self.awn_length,
            self.awn_angle,
        )

        state = NormalCoverState(horizontal)
        if self.climate_data is not None:
            state = ClimateCoverState(horizontal, self.climate_data)
        self.calculated_state = state.get_state()

        self.start, self.end = horizontal.solar_times()

    def update_tilt(self):
        """Update values for tilted blind."""
        self.slat_distance = self.config_entry.options[CONF_TILT_DISTANCE]
        self.depth = self.config_entry.options[CONF_TILT_DEPTH]
        self.tilt_mode = self.config_entry.options[CONF_TILT_MODE]
        tilt = AdaptiveTiltCover(
            self.hass,
            self.sol_azi,
            self.sol_elev,
            self.sunset_pos,
            self.sunset_off,
            self.timezone,
            self.fov_left,
            self.fov_right,
            self.win_azi,
            self.h_def,
            self.slat_distance,
            self.depth,
            self.tilt_mode,
        )

        state = NormalCoverState(tilt)
        if self.climate_data is not None:
            state = ClimateCoverState(tilt, self.climate_data)
        self.calculated_state = state.get_state()

        self.start, self.end = tilt.solar_times()

    def update_climate(self):
        """Update climate variables."""
        self.temp_low = self.config_entry.options[CONF_TEMP_LOW]
        self.temp_high = self.config_entry.options[CONF_TEMP_HIGH]
        self.temp_entity = self.config_entry.options["temp_entity"]
        self.presence_entity = self.config_entry.options["presence_entity"]
        self.weather_entity = self.config_entry.options["weather_entity"]
        self.weather_condition = self.config_entry.get(CONF_WEATHER_STATE)
        self.presence = None
        if get_domain(self.temp_entity) == "climate":
            self.current_temp = self.hass.states.get(self.temp_entity).attributes[
                "current_temperature"
            ]
        else:
            self.current_temp = get_safe_state(self.hass, self.temp_entity)

        if self.presence_entity is not None:
            self.presence = get_safe_state(self.hass, self.presence_entity)
        if self.weather_entity is not None:
            self.weather_state = get_safe_state(self.hass, self.weather_entity)

        self.climate_data = ClimateCoverData(
            self.current_temp,
            self.temp_low,
            self.temp_high,
            self.presence,
            self.presence_entity,
            self.weather_state,
            self.weather_condition,
            self.sensor_type,
        )

    @property
    def state(self):
        """Get state from cover type class."""
        state = self.calculated_state
        if state is not None:
            self._state = round(state)
            if self.inverse_state:
                return 100 - self._state
            return self._state
