"""The Coordinator for Adaptive Cover."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
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
    CONF_MAX_POSITION,
    CONF_OUTSIDETEMP_ENTITY,
    CONF_PRESENCE_ENTITY,
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
        pos_sun = [
            state_attr(self.hass, "sun.sun", "azimuth"),
            state_attr(self.hass, "sun.sun", "elevation"),
        ]

        common_data = [
            self.config_entry.options.get(CONF_SUNSET_POS),
            self.config_entry.options.get(CONF_SUNSET_OFFSET),
            self.hass.config.time_zone,
            self.config_entry.options.get(CONF_FOV_LEFT),
            self.config_entry.options.get(CONF_FOV_RIGHT),
            self.config_entry.options.get(CONF_AZIMUTH),
            self.config_entry.options.get(CONF_DEFAULT_HEIGHT),
            self.config_entry.options.get(CONF_MAX_POSITION, 100),
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

        control_method = "intermediate"
        climate_state = None

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
            climate_state = round(ClimateCoverState(cover_data, climate).get_state())
            climate_data = ClimateCoverState(cover_data, climate).climate_data
            if climate_data.is_summer and self.switch_mode:
                control_method = "summer"
            if climate_data.is_winter and self.switch_mode:
                control_method = "winter"

        default_state = round(NormalCoverState(cover_data).get_state())

        state = default_state
        if self._switch_mode:
            state = climate_state

        if self._inverse_state:
            state = 100 - state

        return AdaptiveCoverData(
            climate_mode_toggle=self.switch_mode,
            states={
                "normal": default_state,
                "climate": climate_state,
                "state": state,
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
                "outside": self.config_entry.options.get(CONF_OUTSIDETEMP_ENTITY),
                "outside_temp": climate_data.outside_temperature,
                "current_temp": climate_data.get_current_temperature,
                "toggle": climate_data.temp_switch,
            },
        )

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
