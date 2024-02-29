"""The Coordinator for Adaptive Cover."""
from __future__ import annotations
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass, field
from datetime import timedelta
from logging import Logger
from typing import Any
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

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
    DOMAIN,
    LOGGER,
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
    CONF_WEATHER_STATE,
)

@dataclass
class StateChangedData:
    """StateChangedData class."""

    entity_id: str
    old_state: State | None
    new_state: State | None

@dataclass
class AdaptiveCoverData:
    """AdaptiveCoverData class."""
    mode: bool
    # sol_azi: float


class AdaptiveDataUpdateCoordinator(DataUpdateCoordinator[AdaptiveCoverData]):
    """Adaptive cover data update coordinator"""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass, LOGGER, name=DOMAIN)
        self._switch_mode=True

    async def async_check_entity_state_change(
        self, entity: str, old_state: State | None, new_state: State | None
    ) -> None:
        """Fetch and process state change event."""
        self.state_change_data = StateChangedData(entity, old_state, new_state)
        await self.async_refresh()

    async def _async_update_data(self) -> AdaptiveCoverData:
        return AdaptiveCoverData(
            mode=self.switch_mode,
            # sol_azi=self.hass.states.get("sun.sun").attributes["azimuth"]
        )

    @property
    def switch_mode(self):
        return self._switch_mode

    @switch_mode.setter
    def switch_mode(self, value):
        self._switch_mode = value








# class AdaptiveDataCoordinator:
#     """Data coordinator."""

#     def __init__(  # noqa: D107
#         self,
#         hass: HomeAssistant = HomeAssistant,
#         config_entry: ConfigEntry = ConfigEntry,
#         sensor: Sensor = Sensor
#     ) -> None:
#         self.hass = hass
#         self.config_entry = config_entry
#         self.sensor = sensor
#         self.sensor_type = self.config_entry.data[CONF_SENSOR_TYPE]
#         self._mode = None
#         self.calculated_state = None
#         self.sol_azi = None
#         self.sol_elev = None
#         self.timezone = self.hass.config.time_zone
#         self.distance = 0.5
#         self.h_def = 60
#         self.h_win = 2.1
#         self.awn_length = 2.1
#         self.awn_angle = 0
#         self.start = None
#         self.end = None
#         self.sunset_pos = 0
#         self.sunset_off = 0
#         self.slat_distance = 2
#         self.depth = 3
#         self.tilt_mode = "mode2"
#         self.fov_left = self.config_entry.options[CONF_FOV_LEFT]
#         self.fov_right = self.config_entry.options[CONF_FOV_RIGHT]
#         self.fov = [self.fov_left, self.fov_right]
#         self.win_azi = 180
#         self.inverse_state = False
#         self._state = None
#         self.current_temp = None
#         self.temp_low = None
#         self.temp_high = None
#         self.presence = None
#         self.presence_entity = None
#         self.weather_entity = None
#         self.weather_state = None
#         self.weather_condition = None
#         self.climate_state = None
#         self.climate_data = None
#         self.climate_mode_set = False
#         self._climate_mode = False

#     @property
#     def climate_mode(self):
#         """Set sensor mode."""
#         return self._climate_mode

#     @climate_mode.setter
#     def climate_mode(self, value):
#         self._climate_mode = value
#         self.sensor.async_update_state()

#     def update(self):
#         """Update all common parameters."""
#         self.inverse_state = self.config_entry.options[CONF_INVERSE_STATE]
#         self.sol_azi = self.hass.states.get("sun.sun").attributes["azimuth"]
#         self.sol_elev = self.hass.states.get("sun.sun").attributes["elevation"]
#         self.sunset_pos = self.config_entry.options[CONF_SUNSET_POS]
#         self.sunset_off = self.config_entry.options[CONF_SUNSET_OFFSET]
#         self.timezone = self.hass.config.time_zone
#         self.fov_left = self.config_entry.options[CONF_FOV_LEFT]
#         self.fov_right = self.config_entry.options[CONF_FOV_RIGHT]
#         self.fov = [self.fov_left, self.fov_right]
#         self.win_azi = self.config_entry.options[CONF_AZIMUTH]
#         self.h_def = self.config_entry.options[CONF_DEFAULT_HEIGHT]
#         self._mode = self.config_entry.data.get(CONF_MODE, "basic")

#     def update_vertical(self):
#         """Update values for vertical blind."""
#         self.distance = self.config_entry.options[CONF_DISTANCE]
#         self.h_win = self.config_entry.options[CONF_HEIGHT_WIN]
#         vertical = AdaptiveVerticalCover(
#             self.hass,
#             self.sol_azi,
#             self.sol_elev,
#             self.sunset_pos,
#             self.sunset_off,
#             self.timezone,
#             self.fov_left,
#             self.fov_right,
#             self.win_azi,
#             self.h_def,
#             self.distance,
#             self.h_win,
#         )

#         state = NormalCoverState(vertical)
#         if self.climate_data is not None:
#             state = ClimateCoverState(vertical, self.climate_data)
#         self.calculated_state = state.get_state()

#         self.start, self.end = vertical.solar_times()

#     def update_horizontal(self):
#         """Update values for horizontal blind."""
#         self.awn_length = self.config_entry.options[CONF_LENGTH_AWNING]
#         self.awn_angle = self.config_entry.options[CONF_AWNING_ANGLE]
#         horizontal = AdaptiveHorizontalCover(
#             self.hass,
#             self.sol_azi,
#             self.sol_elev,
#             self.sunset_pos,
#             self.sunset_off,
#             self.timezone,
#             self.fov_left,
#             self.fov_right,
#             self.win_azi,
#             self.h_def,
#             self.distance,
#             self.h_win,
#             self.awn_length,
#             self.awn_angle,
#         )

#         state = NormalCoverState(horizontal)
#         if self.climate_data is not None:
#             state = ClimateCoverState(horizontal, self.climate_data)
#         self.calculated_state = state.get_state()

#         self.start, self.end = horizontal.solar_times()

#     def update_tilt(self):
#         """Update values for tilted blind."""
#         self.slat_distance = self.config_entry.options[CONF_TILT_DISTANCE]
#         self.depth = self.config_entry.options[CONF_TILT_DEPTH]
#         self.tilt_mode = self.config_entry.options[CONF_TILT_MODE]
#         tilt = AdaptiveTiltCover(
#             self.hass,
#             self.sol_azi,
#             self.sol_elev,
#             self.sunset_pos,
#             self.sunset_off,
#             self.timezone,
#             self.fov_left,
#             self.fov_right,
#             self.win_azi,
#             self.h_def,
#             self.slat_distance,
#             self.depth,
#             self.tilt_mode,
#         )

#         state = NormalCoverState(tilt)
#         if self.climate_data is not None:
#             state = ClimateCoverState(tilt, self.climate_data)
#         self.calculated_state = state.get_state()

#         self.start, self.end = tilt.solar_times()

#     def update_climate(self):
#         """Update climate variables."""
#         self.temp_low = self.config_entry.options.get(CONF_TEMP_LOW)
#         self.temp_high = self.config_entry.options.get(CONF_TEMP_HIGH)
#         self.temp_entity = self.config_entry.options.get("temp_entity")
#         self.presence_entity = self.config_entry.options.get("presence_entity")
#         self.weather_entity = self.config_entry.options.get("weather_entity")
#         self.weather_condition = self.config_entry.get(CONF_WEATHER_STATE)
#         self.presence = None
#         if get_domain(self.temp_entity) == "climate":
#             self.current_temp = self.hass.states.get(self.temp_entity).attributes[
#                 "current_temperature"
#             ]
#         else:
#             self.current_temp = get_safe_state(self.hass, self.temp_entity)

#         if self.presence_entity is not None:
#             self.presence = get_safe_state(self.hass, self.presence_entity)
#         if self.weather_entity is not None:
#             self.weather_state = get_safe_state(self.hass, self.weather_entity)

#         self.climate_data = ClimateCoverData(
#             self.current_temp,
#             self.temp_low,
#             self.temp_high,
#             self.presence,
#             self.presence_entity,
#             self.weather_state,
#             self.weather_condition,
#             self.sensor_type,
#         )

#     @property
#     def state(self):
#         """Get state from cover type class."""
#         state = self.calculated_state
#         if state is not None:
#             self._state = round(state)
#             if self.inverse_state:
#                 return 100 - self._state
#             return self._state
