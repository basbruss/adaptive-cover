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

from .calculation import (
    AdaptiveHorizontalCover,
    AdaptiveTiltCover,
    AdaptiveVerticalCover,
    ClimateCoverData,
    ClimateCoverState,
    NormalCoverState,
)
from .const import (
    CONF_AWNING_ANGLE,
    CONF_AZIMUTH,
    CONF_CLIMATE_MODE,
    CONF_DEFAULT_HEIGHT,
    CONF_DISTANCE,
    CONF_ENTITIES,
    CONF_FOV_LEFT,
    CONF_FOV_RIGHT,
    CONF_HEIGHT_WIN,
    CONF_INVERSE_STATE,
    CONF_LENGTH_AWNING,
    CONF_MODE,
    CONF_PRESENCE_ENTITY,
    CONF_SENSOR_TYPE,
    CONF_SUNSET_OFFSET,
    CONF_SUNSET_POS,
    CONF_TEMP_ENTITY,
    CONF_TEMP_HIGH,
    CONF_TEMP_LOW,
    CONF_TILT_DEPTH,
    CONF_TILT_DISTANCE,
    CONF_TILT_MODE,
    CONF_WEATHER_ENTITY,
    CONF_WEATHER_STATE,
    DOMAIN,
    LOGGER,
)
from .helpers import get_domain, get_safe_state


@dataclass
class StateChangedData:
    """StateChangedData class."""

    entity_id: str
    old_state: State | None
    new_state: State | None


@dataclass
class AdaptiveCoverData:
    """AdaptiveCoverData class."""

    climate_mode_toggle: bool
    states: dict
    attributes: dict


class AdaptiveDataUpdateCoordinator(DataUpdateCoordinator[AdaptiveCoverData]):
    """Adaptive cover data update coordinator."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass, LOGGER, name=DOMAIN)
        self._switch_mode = True
        self._cover_type = self.config_entry.data["sensor_type"]
        self._climate_mode = self.config_entry.options[CONF_CLIMATE_MODE]
        self._inverse_state = self.config_entry.options[CONF_INVERSE_STATE]

    async def async_check_entity_state_change(
        self, entity: str, old_state: State | None, new_state: State | None
    ) -> None:
        """Fetch and process state change event."""
        self.state_change_data = StateChangedData(entity, old_state, new_state)
        await self.async_refresh()

    async def _async_update_data(self) -> AdaptiveCoverData:

        pos_sun = [
            self.hass.states.get("sun.sun").attributes["azimuth"],
            self.hass.states.get("sun.sun").attributes["elevation"],
        ]

        common_data = [
            self.config_entry.options.get(CONF_SUNSET_POS),
            self.config_entry.options.get(CONF_SUNSET_OFFSET),
            self.hass.config.time_zone,
            self.config_entry.options.get(CONF_FOV_LEFT),
            self.config_entry.options.get(CONF_FOV_RIGHT),
            self.config_entry.options.get(CONF_AZIMUTH),
            self.config_entry.options.get(CONF_DEFAULT_HEIGHT),
        ]

        vertical_data = [
            self.config_entry.options.get(CONF_DISTANCE),
            self.config_entry.options.get(CONF_HEIGHT_WIN),
        ]

        horizontal_data = [
            self.config_entry.options.get(CONF_LENGTH_AWNING),
            self.config_entry.options.get(CONF_AWNING_ANGLE),
        ]

        tilt_data = [
            self.config_entry.options.get(CONF_TILT_DISTANCE),
            self.config_entry.options.get(CONF_TILT_DEPTH),
            self.config_entry.options.get(CONF_TILT_MODE),
        ]

        climate_data = [
            self.hass,
            self.config_entry.options.get(CONF_TEMP_ENTITY),
            self.config_entry.options.get(CONF_TEMP_LOW),
            self.config_entry.options.get(CONF_TEMP_HIGH),
            self.config_entry.options.get(CONF_PRESENCE_ENTITY),
            self.config_entry.options.get(CONF_WEATHER_ENTITY),
            self.config_entry.options.get(CONF_WEATHER_STATE),
            self._cover_type,
        ]

        if self._cover_type == "cover_blind":
            cover_data = AdaptiveVerticalCover(
                self.hass, *pos_sun, *common_data, *vertical_data
            )
        if self._cover_type == "cover_awning":
            cover_data = AdaptiveHorizontalCover(
                self.hass, *pos_sun, *common_data, *vertical_data, *horizontal_data
            )
        if self._cover_type == "cover_tilt":
            cover_data = AdaptiveTiltCover(
                self.hass, *pos_sun, *common_data, *tilt_data
            )

        climate = ClimateCoverData(*climate_data)

        default_state = round(NormalCoverState(cover_data).get_state())
        climate_state = round(ClimateCoverState(cover_data, climate).get_state())

        if self._inverse_state:
            default_state = 100-default_state
            climate_state = 100-climate_state

        return AdaptiveCoverData(
            climate_mode_toggle=self.switch_mode,
            states={
                "normal": default_state,
                "climate": climate_state,
            },
            attributes={
                "default": self.config_entry.options.get(CONF_DEFAULT_HEIGHT),
                "sunset_default": self.config_entry.options.get(CONF_SUNSET_POS),
                "sunset_offset": self.config_entry.options.get(CONF_SUNSET_OFFSET),
                "azimuth_window": self.config_entry.options.get(CONF_AZIMUTH),
                "field_of_view": [self.config_entry.options.get(CONF_FOV_LEFT),
            self.config_entry.options.get(CONF_FOV_RIGHT)],
                "entity_id": self.config_entry.options.get(CONF_ENTITIES),
                "cover_type": self._cover_type
            }
            # inputs={
            #     "type": self._cover_type,
            #     "common": common_data,
            #     "vertical": vertical_data,
            #     "horizontal": horizontal_data,
            #     "tilt": tilt_data,
            #     "climate": climate_data,
            # },
        )

    # def _parse_parameters(self, azimuth_sun, elevation_sun):
    #     return MockCalc(azimuth_sun=azimuth_sun, elevation_sun=elevation_sun)

    # def _update_parameters(self, mode, *args):
    #     """Update parameters for vertical blinds."""
    #     dict = {"cover_blind": AdaptiveVerticalCover(*args)}
    #     return dict[mode]

    @property
    def switch_mode(self):
        """Let switch toggle climate mode."""
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
