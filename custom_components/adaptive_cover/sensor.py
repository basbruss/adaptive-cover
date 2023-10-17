"""Sensor platform for Adaptive Cover integration."""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, CoreState
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import UndefinedType

from .calculation import AdaptiveCoverCalculator

from .const import (
    DOMAIN,
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
    SensorType,
)

SCAN_INTERVAL = timedelta(seconds=10)


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

    def __init__(
        self,
        unique_id: str,
        hass,
        config_entry,
        name: str,
        cover_data: AdaptiveCoverCalculator,
    ) -> None:
        """Initialize adaptive_cover Sensor."""
        type = {
            'cover_blind': 'Vertical',
            'cover_awning': 'Horizontal',
            'cover_tilt': 'Tilt'
        }
        self._attr_unique_id = unique_id
        self.hass = hass
        self.config_entry = config_entry
        self._cover_data = cover_data
        self._attr_name = f"Adaptive Cover {name} {type[self.config_entry.data[CONF_SENSOR_TYPE]]}"
        self._name = f"Adaptive Cover {name}"

    async def async_added_to_hass(self) -> None:
        """Handle when entity is added."""
        if self.hass.state != CoreState.running:
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self.first_update
            )
        else:
            await self.first_update()

    @property
    def native_value(self) -> int | None:
        """Handle when entity is added"""
        return self._cover_data.state

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        dict_attributes = {
            "azimuth_window": self.config_entry.options[CONF_AZIMUTH],
            "default_height": self.config_entry.options[CONF_DEFAULT_HEIGHT],
            "field_of_view": self._cover_data.fov,
            'start_time': self._cover_data.start,
            'end_time': self._cover_data.end,
            "entity_id": self.config_entry.options[CONF_ENTITIES],
            # "test": self.config_entry,
        }
        if self.config_entry.data["sensor_type"] == "cover_blind":
            dict_attributes["window_height"] = self.config_entry.options[
                CONF_HEIGHT_WIN
            ]
            dict_attributes["distance"] = self.config_entry.options[CONF_DISTANCE]
        if self.config_entry.data["sensor_type"] == "cover_awning":
            dict_attributes["awning_lenght"] = self.config_entry.options[
                CONF_LENGTH_AWNING
            ]
            dict_attributes["awning_angle"] = self.config_entry.options[
                CONF_AWNING_ANGLE
            ]
            dict_attributes["distance"] = self.config_entry.options[CONF_DISTANCE]
        return dict_attributes

    async def first_update(self, _=None) -> None:
        """Run first update and write state."""
        await self.hass.async_add_executor_job(self.update)
        self.async_write_ha_state()

    def update(self) -> None:
        """Fetch new state data for the sensor."""
        self._cover_data.update()


class AdaptiveCoverData:
    """AdaptiveCover data object"""

    def __init__(
        self,
        hass,
        config_entry: ConfigEntry,
    ) -> None:
        self.hass = hass
        self.config_entry = config_entry
        self.state = None
        self.sol_azi = None
        self.elev_sun = None
        self.distance = 0.5
        self.h_win = 2.1
        self.awn_length = 2.1
        self.awn_angle = 0
        self.start = None
        self.end = None
        self.fov = None
        self.test_update = None
        self.def_height = 2.1
        self.sunset_pos = 0
        self.sunset_off = 0
        self.sensor_type = self.config_entry.data[CONF_SENSOR_TYPE]
        self.slat_distance = 2
        self.depth = 3
        self.mode = 'mode2'

    def update(self):
        """Update parameters"""

        azi_set = self.config_entry.options[CONF_AZIMUTH]
        if self.config_entry.options.get(CONF_HEIGHT_WIN) is not None:
            self.h_win = self.config_entry.options[CONF_HEIGHT_WIN]
        if self.config_entry.options.get(CONF_DISTANCE) is not None:
            self.distance = self.config_entry.options[CONF_DISTANCE]
        fov_left = self.config_entry.options[CONF_FOV_LEFT]
        fov_right = self.config_entry.options[CONF_FOV_RIGHT]
        self.sunset_pos = self.config_entry.options[CONF_SUNSET_POS]
        self.sunset_off = self.config_entry.options[CONF_SUNSET_OFFSET]
        self.def_height = self.config_entry.options[CONF_DEFAULT_HEIGHT]
        if self.config_entry.options.get(CONF_TILT_DISTANCE) is not None:
            self.slat_distance = self.config_entry.options[CONF_TILT_DISTANCE]
        if self.config_entry.options.get(CONF_TILT_DEPTH) is not None:
            self.depth = self.config_entry.options[CONF_TILT_DEPTH]
        if self.config_entry.options.get(CONF_LENGTH_AWNING) is not None:
            self.awn_length = self.config_entry.options[CONF_LENGTH_AWNING]
        if self.config_entry.options.get(CONF_AWNING_ANGLE) is not None:
            self.awn_angle = self.config_entry.options[CONF_AWNING_ANGLE]
        if self.config_entry.options.get(CONF_TILT_MODE) is not None:
            self.mode = self.config_entry.options[CONF_TILT_MODE]
        inverse = self.config_entry.options[CONF_INVERSE_STATE]
        timezone = self.hass.config.time_zone
        lat = self.hass.config.latitude
        lon = self.hass.config.longitude
        self.sol_azi = self.hass.states.get("sun.sun").attributes["azimuth"]
        self.elev_sun = self.hass.states.get("sun.sun").attributes["elevation"]
        params = AdaptiveCoverCalculator(
            self.hass,
            timezone,
            lat,
            lon,
            self.sol_azi,
            self.elev_sun,
            azi_set,
            self.h_win,
            self.distance,
            fov_left,
            fov_right,
            self.def_height,
            self.awn_angle,
            self.awn_length,
            self.sunset_pos,
            self.sunset_off,
            self.slat_distance,
            self.depth,
            self.mode
        )
        self.fov = params.fov()
        self.start = params.solar_times()[0]
        self.end = params.solar_times()[1]
        # self.test_update = params.test(lon)

        if self.sensor_type == SensorType.BLIND:
            state = params.blind_state_perc()
        if self.sensor_type == SensorType.AWNING:
            state = params.awn_state_perc()
        if self.sensor_type == SensorType.TILT:
            state = params.tilt_state_perc()
        self.state = round(state)
        if inverse:
            self.state = 100 - state
