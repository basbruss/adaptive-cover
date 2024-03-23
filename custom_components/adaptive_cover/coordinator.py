"""The Coordinator for Adaptive Cover."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_SET_COVER_POSITION,
    SERVICE_SET_COVER_TILT_POSITION,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.template import state_attr
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
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CONF_AWNING_ANGLE,
    CONF_AZIMUTH,
    CONF_CLIMATE_MODE,
    CONF_DEFAULT_HEIGHT,
    CONF_DELTA_POSITION,
    CONF_DELTA_TIME,
    CONF_DISTANCE,
    CONF_ENTITIES,
    CONF_FOV_LEFT,
    CONF_FOV_RIGHT,
    CONF_HEIGHT_WIN,
    CONF_INVERSE_STATE,
    CONF_LENGTH_AWNING,
    CONF_MAX_POSITION,
    CONF_OUTSIDETEMP_ENTITY,
    CONF_PRESENCE_ENTITY,
    CONF_START_ENTITY,
    CONF_START_TIME,
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
from .helpers import get_last_updated, get_timedelta_str


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

    def __init__(self, hass: HomeAssistant) -> None:  # noqa: D107
        super().__init__(hass, LOGGER, name=DOMAIN)

        self._cover_type = self.config_entry.data.get("sensor_type")
        self._climate_mode = self.config_entry.options.get(CONF_CLIMATE_MODE, False)
        self._switch_mode = True if self._climate_mode else False
        self._inverse_state = self.config_entry.options.get(CONF_INVERSE_STATE, False)
        self._temp_toggle = False

    async def async_check_entity_state_change(
        self, entity: str, old_state: State | None, new_state: State | None
    ) -> None:
        """Fetch and process state change event."""
        self.state_change_data = StateChangedData(entity, old_state, new_state)
        await self.async_refresh()

    async def _async_update_data(self) -> AdaptiveCoverData:
        self.entities = self.config_entry.options.get(CONF_ENTITIES, [])
        self.min_change = self.config_entry.options.get(CONF_DELTA_POSITION, 1)
        self.time_threshold = self.config_entry.options.get(CONF_DELTA_TIME)

        cover_data = self.get_blind_data()

        control_method = "intermediate"
        self.climate_state = None

        if self._climate_mode:
            climate_data_var = [
                self.hass,
                self.config_entry.options.get(CONF_TEMP_ENTITY),
                self.config_entry.options.get(CONF_TEMP_LOW),
                self.config_entry.options.get(CONF_TEMP_HIGH),
                self.config_entry.options.get(CONF_PRESENCE_ENTITY),
                self.config_entry.options.get(CONF_WEATHER_ENTITY),
                self.config_entry.options.get(CONF_WEATHER_STATE),
                self.config_entry.options.get(CONF_OUTSIDETEMP_ENTITY),
                self._temp_toggle,
                self._cover_type,
            ]
            climate = ClimateCoverData(*climate_data_var)
            self.climate_state = round(
                ClimateCoverState(cover_data, climate).get_state()
            )
            climate_data = ClimateCoverState(cover_data, climate).climate_data
            if climate_data.is_summer and self.switch_mode:
                control_method = "summer"
            if climate_data.is_winter and self.switch_mode:
                control_method = "winter"

        self.default_state = round(NormalCoverState(cover_data).get_state())

        self.state

        now = dt.datetime.now(dt.UTC)

        for entity in self.entities:
            last_updated = get_last_updated(entity, self.hass)
            delta_time = now - last_updated >= get_timedelta_str(self.time_threshold)
            if self.check_position(entity) and delta_time or not cover_data.valid:
                await self.async_set_position(entity)

        return AdaptiveCoverData(
            climate_mode_toggle=self.switch_mode,
            states={
                "state": self.state,
                "start": NormalCoverState(cover_data).cover.solar_times()[0],
                "end": NormalCoverState(cover_data).cover.solar_times()[1],
                "control": control_method,
                "binary": NormalCoverState(cover_data).cover.valid,
            },
            attributes={
                "default": self.config_entry.options.get(CONF_DEFAULT_HEIGHT),
                "sunset_default": self.config_entry.options.get(CONF_SUNSET_POS),
                "sunset_offset": self.config_entry.options.get(CONF_SUNSET_OFFSET),
                "azimuth_window": self.config_entry.options.get(CONF_AZIMUTH),
                "field_of_view": [
                    self.config_entry.options.get(CONF_FOV_LEFT),
                    self.config_entry.options.get(CONF_FOV_RIGHT),
                ],
                "entity_id": self.config_entry.options.get(CONF_ENTITIES),
                "cover_type": self._cover_type,
                "delta_position": self.config_entry.options.get(CONF_DELTA_POSITION),
                "delta_time": self.config_entry.options.get(CONF_DELTA_TIME),
                "start_time": self.config_entry.options.get(CONF_START_TIME),
                "start_entity": self.config_entry.options.get(CONF_START_ENTITY),
            },
        )

    async def async_set_position(self, entity):
        """Call service to set cover position."""
        service = SERVICE_SET_COVER_POSITION
        service_data = {}
        service_data[ATTR_ENTITY_ID] = entity

        if self._cover_type == "cover_tilt":
            service = SERVICE_SET_COVER_TILT_POSITION
            service_data[ATTR_TILT_POSITION] = self.state
        else:
            service_data[ATTR_POSITION] = self.state

        await self.hass.services.async_call(COVER_DOMAIN, service, service_data)

    def check_position(self, entity):
        """Check cover positions to reduce calls."""
        position = state_attr(self.hass, entity, "current_position")
        if position is not None:
            return abs(position - self.state) >= self.min_change
        return True

    @property
    def pos_sun(self):
        """Fetch information for sun position."""
        return [
            state_attr(self.hass, "sun.sun", "azimuth"),
            state_attr(self.hass, "sun.sun", "elevation"),
        ]

    @property
    def common_data(self):
        """Update shared parameters."""
        return [
            self.config_entry.options.get(CONF_SUNSET_POS),
            self.config_entry.options.get(CONF_SUNSET_OFFSET),
            self.hass.config.time_zone,
            self.config_entry.options.get(CONF_FOV_LEFT),
            self.config_entry.options.get(CONF_FOV_RIGHT),
            self.config_entry.options.get(CONF_AZIMUTH),
            self.config_entry.options.get(CONF_DEFAULT_HEIGHT),
            self.config_entry.options.get(CONF_MAX_POSITION, 100),
        ]

    @property
    def vertical_data(self):
        """Update data for vertical blinds."""
        return [
            self.config_entry.options.get(CONF_DISTANCE),
            self.config_entry.options.get(CONF_HEIGHT_WIN),
        ]

    @property
    def horizontal_data(self):
        """Update data for horizontal blinds."""
        return [
            self.config_entry.options.get(CONF_LENGTH_AWNING),
            self.config_entry.options.get(CONF_AWNING_ANGLE),
        ]

    @property
    def tilt_data(self):
        """Update data for tilted blinds."""
        return [
            self.config_entry.options.get(CONF_TILT_DISTANCE),
            self.config_entry.options.get(CONF_TILT_DEPTH),
            self.config_entry.options.get(CONF_TILT_MODE),
        ]

    def get_blind_data(self):
        """Assign correct class for type of blind."""
        if self._cover_type == "cover_blind":
            cover_data = AdaptiveVerticalCover(
                self.hass, *self.pos_sun, *self.common_data, *self.vertical_data
            )
        if self._cover_type == "cover_awning":
            cover_data = AdaptiveHorizontalCover(
                self.hass,
                *self.pos_sun,
                *self.common_data,
                *self.vertical_data,
                *self.horizontal_data,
            )
        if self._cover_type == "cover_tilt":
            cover_data = AdaptiveTiltCover(
                self.hass, *self.pos_sun, *self.common_data, *self.tilt_data
            )
        return cover_data

    @property
    def state(self):
        """Handle the output of the state based on mode."""
        state = self.default_state
        if self._switch_mode:
            state = self.climate_state
        if self._inverse_state:
            state = 100 - state
        return state

    async def async_handle_call_service(self):
        """Handle call service."""

    @property
    def switch_mode(self):
        """Let switch toggle climate mode."""
        return self._switch_mode

    @switch_mode.setter
    def switch_mode(self, value):
        self._switch_mode = value

    @property
    def temp_toggle(self):
        """Let switch toggle climate mode."""
        return self._temp_toggle

    @temp_toggle.setter
    def temp_toggle(self, value):
        self._temp_toggle = value
