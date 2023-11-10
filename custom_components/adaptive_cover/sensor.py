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

from .calculation import (
    AdaptiveVerticalCover,
    AdaptiveHorizontalCover,
    AdaptiveTiltCover,
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
        self._attr_unique_id = unique_id
        self.hass = hass
        self.config_entry = config_entry
        self._cover_data = cover_data
        self._attr_name = (
            f"Adaptive Cover {name} {type[self.config_entry.data[CONF_SENSOR_TYPE]]}"
        )
        self._name = f"Adaptive Cover {name}"
        self.cover_type = self.config_entry.data["sensor_type"]

    @callback
    def async_on_state_change(self, event: EventType[EventStateChangedData]) -> None:
        """Update supported features and state when a new state is received."""
        self.async_set_context(event.context)

        self.async_update_state()

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""
        async_track_state_change_event(
            self.hass, ["sun.sun"], self.async_on_state_change
        )
        self.async_update_state()

    @callback
    def async_update_state(self) -> None:
        """Determine state after push."""
        self._cover_data.update()
        if self.cover_type == "cover_blind":
            self._cover_data.update_vertical()
        if self.cover_type == "cover_awning":
            self._cover_data.update_horizontal()
        if self.cover_type == "cover_tilt":
            self._cover_data.update_tilt()

        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        """Handle when entity is added."""
        return self._cover_data.state

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:  # noqa: D102
        dict_attributes = {
            "azimuth_window": self.config_entry.options[CONF_AZIMUTH],
            "default_height": self.config_entry.options[CONF_DEFAULT_HEIGHT],
            # "field_of_view": self._cover_data.fov,
            # 'start_time': self._cover_data.start,
            # 'end_time': self._cover_data.end,
            "entity_id": self.config_entry.options[CONF_ENTITIES],
            # "test": self.config_entry,
        }
        if self.cover_type == "cover_blind":
            dict_attributes["window_height"] = self.config_entry.options[
                CONF_HEIGHT_WIN
            ]
            dict_attributes["distance"] = self.config_entry.options[CONF_DISTANCE]
        if self.cover_type == "cover_awning":
            dict_attributes["awning_lenght"] = self.config_entry.options[
                CONF_LENGTH_AWNING
            ]
            dict_attributes["awning_angle"] = self.config_entry.options[
                CONF_AWNING_ANGLE
            ]
            dict_attributes["distance"] = self.config_entry.options[CONF_DISTANCE]
        return dict_attributes


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
        self.state_perc = None
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
        self.fov = None
        self.sunset_pos = 0
        self.sunset_off = 0
        self.slat_distance = 2
        self.depth = 3
        self.mode = "mode2"
        self.fov_left = self.config_entry.options[CONF_FOV_LEFT]
        self.fov_right = self.config_entry.options[CONF_FOV_RIGHT]
        self.win_azi = 180

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
        self.win_azi = self.config_entry.options[CONF_AZIMUTH]
        self.h_def = self.config_entry.options[CONF_DEFAULT_HEIGHT]

    def update_vertical(self):
        """Update values for vertical blind."""
        self.distance = self.config_entry.options[CONF_DISTANCE]
        self.h_win = self.config_entry.options[CONF_HEIGHT_WIN]
        values = AdaptiveVerticalCover(
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
        self.state_perc = values.blind_state_perc()

    def update_horizontal(self):
        """Update values for horizontal blind."""
        self.awn_length = self.config_entry.options[CONF_LENGTH_AWNING]
        self.awn_angle = self.config_entry.options[CONF_AWNING_ANGLE]
        values = AdaptiveHorizontalCover(
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
        self.state_perc = values.awn_state_perc()

    def update_tilt(self):
        """Update values for tilted blind."""
        self.slat_distance = self.config_entry.options[CONF_TILT_DISTANCE]
        self.depth = self.config_entry.options[CONF_TILT_DEPTH]
        self.mode = self.config_entry.options[CONF_TILT_MODE]
        values = AdaptiveTiltCover(
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
            self.mode,
        )
        self.state_perc = values.tilt_state_perc()

    @property
    def state(self):
        """Get state from cover type class."""
        state = self.state_perc
        if state is not None:
            return round(state)

    @state.setter
    def inverse_state(self, value):
        """Inverse state."""
        if self.inverse_state:
            return 100 - value
        return value
