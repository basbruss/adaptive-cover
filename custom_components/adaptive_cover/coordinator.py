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
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State
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
    _LOGGER,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CONF_AWNING_ANGLE,
    CONF_AZIMUTH,
    CONF_BLIND_SPOT_ELEVATION,
    CONF_BLIND_SPOT_LEFT,
    CONF_BLIND_SPOT_RIGHT,
    CONF_CLIMATE_MODE,
    CONF_DEFAULT_HEIGHT,
    CONF_DELTA_POSITION,
    CONF_DELTA_TIME,
    CONF_DISTANCE,
    CONF_ENABLE_BLIND_SPOT,
    CONF_END_ENTITY,
    CONF_END_TIME,
    CONF_ENTITIES,
    CONF_FOV_LEFT,
    CONF_FOV_RIGHT,
    CONF_HEIGHT_WIN,
    CONF_INVERSE_STATE,
    CONF_LENGTH_AWNING,
    CONF_MANUAL_IGNORE_INTERMEDIATE,
    CONF_MANUAL_OVERRIDE_DURATION,
    CONF_MANUAL_OVERRIDE_RESET,
    CONF_MANUAL_THRESHOLD,
    CONF_MAX_ELEVATION,
    CONF_MAX_POSITION,
    CONF_MIN_ELEVATION,
    CONF_OUTSIDETEMP_ENTITY,
    CONF_PRESENCE_ENTITY,
    CONF_START_ENTITY,
    CONF_START_TIME,
    CONF_SUNRISE_OFFSET,
    CONF_SUNSET_OFFSET,
    CONF_SUNSET_POS,
    CONF_TEMP_ENTITY,
    CONF_TEMP_HIGH,
    CONF_TEMP_LOW,
    CONF_TILT_DEPTH,
    CONF_TILT_DISTANCE,
    CONF_TILT_MODE,
    CONF_TRANSPARENT_BLIND,
    CONF_WEATHER_ENTITY,
    CONF_WEATHER_STATE,
    DOMAIN,
    LOGGER,
)
from .helpers import get_datetime_from_str, get_last_updated, get_safe_state


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
        self._temp_toggle = None
        self._control_toggle = None
        self._manual_toggle = None
        self.manual_reset = self.config_entry.options.get(
            CONF_MANUAL_OVERRIDE_RESET, False
        )
        self.manual_duration = self.config_entry.options.get(
            CONF_MANUAL_OVERRIDE_DURATION, {"minutes": 15}
        )
        self.state_change = False
        self.cover_state_change = False
        self.first_refresh = False
        self.timed_refresh = False
        self.state_change_data: StateChangedData | None = None
        self.manager = AdaptiveCoverManager(self.manual_duration)
        self.wait_for_target = {}
        self.target_call = {}
        self.ignore_intermediate_states = self.config_entry.options.get(
            CONF_MANUAL_IGNORE_INTERMEDIATE, False
        )

    async def async_config_entry_first_refresh(self) -> None:
        """Config entry first refresh."""
        self.first_refresh = True
        await super().async_config_entry_first_refresh()
        _LOGGER.debug("Config entry first refresh")

    async def async_timed_refresh(self, event) -> None:
        """Control state at end time."""

        if self.end_time is not None:
            time = self.end_time
        if self.end_time_entity is not None:
            time = get_safe_state(self.hass, self.end_time_entity)
        time_check = dt.datetime.now() - get_datetime_from_str(time)
        if time is not None and (time_check <= dt.timedelta(seconds=1)):
            self.timed_refresh = True
            _LOGGER.debug("Timed refresh triggered")
            await self.async_refresh()
        else:
            _LOGGER.debug("Time not equal to end time")

    async def async_check_entity_state_change(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Fetch and process state change event."""
        _LOGGER.debug("Entity state change")
        self.state_change = True
        await self.async_refresh()

    async def async_check_cover_state_change(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Fetch and process state change event."""
        _LOGGER.debug("Cover state change")
        data = event.data
        if data["old_state"] is None:
            _LOGGER.debug("Old state is None")
            return
        self.state_change_data = StateChangedData(
            data["entity_id"], data["old_state"], data["new_state"]
        )
        self.cover_state_change = True
        self.process_entity_state_change()
        await self.async_refresh()

    def process_entity_state_change(self):
        """Process state change event."""
        event = self.state_change_data
        _LOGGER.debug("Processing state change event: %s", event)
        entity_id = event.entity_id
        if self.ignore_intermediate_states and event.new_state.state in [
            "opening",
            "closing",
        ]:
            _LOGGER.debug("Ignoring intermediate state change for %s", entity_id)
            return
        if self.wait_for_target.get(entity_id):
            position = event.new_state.attributes.get(
                "current_position"
                if self._cover_type != "cover_tilt"
                else "current_tilt_position"
            )
            if position == self.target_call.get(entity_id):
                self.wait_for_target[entity_id] = False
                _LOGGER.debug("Position %s reached for %s", position, entity_id)
        _LOGGER.debug("Wait for target: %s", self.wait_for_target)

    async def _async_update_data(self) -> AdaptiveCoverData:
        self.entities = self.config_entry.options.get(CONF_ENTITIES, [])
        self.min_change = self.config_entry.options.get(CONF_DELTA_POSITION, 1)
        self.time_threshold = self.config_entry.options.get(CONF_DELTA_TIME, 2)
        self.start_time = self.config_entry.options.get(CONF_START_TIME)
        self.start_time_entity = self.config_entry.options.get(CONF_START_ENTITY)
        self.end_time = self.config_entry.options.get(CONF_END_TIME)
        self.end_time_entity = self.config_entry.options.get(CONF_END_ENTITY)
        self.manual_reset = self.config_entry.options.get(
            CONF_MANUAL_OVERRIDE_RESET, False
        )
        self.manual_duration = self.config_entry.options.get(
            CONF_MANUAL_OVERRIDE_DURATION, {"minutes": 15}
        )
        self.manual_threshold = self.config_entry.options.get(CONF_MANUAL_THRESHOLD)

        cover_data = self.get_blind_data()

        self.manager.add_covers(self.entities)

        control_method = "intermediate"
        self.climate_state = None

        if not self._manual_toggle:
            for entity in self.manager.manual_controlled:
                self.manager.reset(entity)

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
                self.config_entry.options.get(CONF_TRANSPARENT_BLIND),
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

        if self.cover_state_change and self.manual_toggle and self.control_toggle:
            self.manager.handle_state_change(
                self.state_change_data,
                self.state,
                self._cover_type,
                self.manual_reset,
                self.wait_for_target,
                self.manual_threshold,
            )
            self.cover_state_change = False  # reset state change

        await self.manager.reset_if_needed()

        if self.state_change and self.control_toggle:
            self.state_change = False
            for cover in self.entities:
                await self.async_handle_call_service(cover)
        elif self.state_change:
            _LOGGER.debug("State change but control toggle is off")

        if self.first_refresh and self.control_toggle:
            for cover in self.entities:
                if (
                    self.check_adaptive_time
                    and not self.manager.is_cover_manual(cover)
                    and self.check_position(cover)
                ):
                    await self.async_set_position(cover)
            self.first_refresh = False
        elif self.first_refresh:
            _LOGGER.debug("First refresh but control toggle is off")

        if self.timed_refresh and self.control_toggle:
            for cover in self.entities:
                await self.async_set_manual_position(
                    cover, self.config_entry.options.get(CONF_SUNSET_POS)
                )
            self.timed_refresh = False
        elif self.timed_refresh:
            _LOGGER.debug("Timed refresh but control toggle is off")

        return AdaptiveCoverData(
            climate_mode_toggle=self.switch_mode,
            states={
                "state": self.state,
                "start": NormalCoverState(cover_data).cover.solar_times()[0],
                "end": NormalCoverState(cover_data).cover.solar_times()[1],
                "control": control_method,
                "sun_motion": NormalCoverState(cover_data).cover.valid,
                "manual_override": self.manager.binary_cover_manual,
                "manual_list": self.manager.manual_controlled,
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
                "blind_spot": self.config_entry.options.get(CONF_BLIND_SPOT_ELEVATION),
            },
        )

    async def async_handle_call_service(self, entity):
        """Handle call service."""
        if (
            self.check_position(entity)
            and self.check_time_delta(entity)
            and self.check_adaptive_time
            and not self.manager.is_cover_manual(entity)
        ):
            await self.async_set_position(entity)

    async def async_set_position(self, entity):
        """Call service to set cover position."""
        await self.async_set_manual_position(entity, self.state)

    async def async_set_manual_position(self, entity, position):
        """Call service to set cover position."""
        service = SERVICE_SET_COVER_POSITION
        service_data = {}
        service_data[ATTR_ENTITY_ID] = entity

        if self._cover_type == "cover_tilt":
            service = SERVICE_SET_COVER_TILT_POSITION
            service_data[ATTR_TILT_POSITION] = position
        else:
            service_data[ATTR_POSITION] = position

        self.wait_for_target[entity] = True
        self.target_call[entity] = position
        _LOGGER.debug(
            "Set wait for target %s and target call %s",
            self.wait_for_target,
            self.target_call,
        )
        _LOGGER.debug("Run %s with data %s", service, service_data)
        await self.hass.services.async_call(COVER_DOMAIN, service, service_data)

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
    def check_adaptive_time(self):
        """Check if time is within start and end times."""
        return self.before_end_time and self.after_start_time

    @property
    def after_start_time(self):
        """Check if time is after start time."""
        if self.start_time_entity is not None:
            time = get_datetime_from_str(
                get_safe_state(self.hass, self.start_time_entity)
            )
            now = dt.datetime.now()
            _LOGGER.debug(
                "Start time: %s, now: %s, now >= time: %s ", time, now, now >= time
            )
            return now >= time
        if self.start_time is not None:
            time = get_datetime_from_str(self.start_time).time()
            now = dt.datetime.now().time()
            _LOGGER.debug(
                "Start time: %s, now: %s, now >= time: %s", time, now, now >= time
            )
            return now >= time
        return True

    @property
    def before_end_time(self):
        """Check if time is before end time."""
        if self.end_time_entity is not None:
            time = get_datetime_from_str(
                get_safe_state(self.hass, self.end_time_entity)
            )
            now = dt.datetime.now()
            _LOGGER.debug(
                "End time: %s, now: %s, now < time: %s", time, now, now < time
            )
            return now < time
        if self.end_time is not None:
            time = get_datetime_from_str(self.end_time).time()
            now = dt.datetime.now().time()
            _LOGGER.debug(
                "End time: %s, now: %s, now < time: %s", time, now, now < time
            )
            return now < time
        return True

    def check_position(self, entity):
        """Check cover positions to reduce calls."""
        if self._cover_type == "cover_tilt":
            position = state_attr(self.hass, entity, "current_tilt_position")
        else:
            position = state_attr(self.hass, entity, "current_position")
        if position is not None:
            condition = abs(position - self.state) >= self.min_change
            _LOGGER.debug(
                "Entity: %s,  position: %s, state: %s, delta position: %s, min_change: %s, condition: %s",
                entity,
                position,
                self.state,
                abs(position - self.state),
                self.min_change,
                condition,
            )
            return condition
        return True

    def check_time_delta(self, entity):
        """Check if time delta is passed."""
        now = dt.datetime.now(dt.UTC)
        last_updated = get_last_updated(entity, self.hass)
        if last_updated is not None:
            condition = now - last_updated >= dt.timedelta(minutes=self.time_threshold)
            _LOGGER.debug(
                "Entity: %s, time delta: %s, threshold: %s, condition: %s",
                entity,
                now - last_updated,
                self.time_threshold,
                condition,
            )
            return condition
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
            self.config_entry.options.get(
                CONF_SUNRISE_OFFSET, self.config_entry.options.get(CONF_SUNSET_OFFSET)
            ),
            self.hass.config.time_zone,
            self.config_entry.options.get(CONF_FOV_LEFT),
            self.config_entry.options.get(CONF_FOV_RIGHT),
            self.config_entry.options.get(CONF_AZIMUTH),
            self.config_entry.options.get(CONF_DEFAULT_HEIGHT),
            self.config_entry.options.get(CONF_MAX_POSITION, 100),
            self.config_entry.options.get(CONF_BLIND_SPOT_LEFT),
            self.config_entry.options.get(CONF_BLIND_SPOT_RIGHT),
            self.config_entry.options.get(CONF_BLIND_SPOT_ELEVATION),
            self.config_entry.options.get(CONF_ENABLE_BLIND_SPOT, False),
            self.config_entry.options.get(CONF_MIN_ELEVATION, None),
            self.config_entry.options.get(CONF_MAX_ELEVATION, None),
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

    @property
    def state(self):
        """Handle the output of the state based on mode."""
        state = self.default_state
        if self._switch_mode:
            state = self.climate_state
        if self._inverse_state:
            state = 100 - state
        _LOGGER.debug("Calculated position: %s", state)
        return state

    @property
    def switch_mode(self):
        """Let switch toggle climate mode."""
        return self._switch_mode

    @switch_mode.setter
    def switch_mode(self, value):
        self._switch_mode = value

    @property
    def temp_toggle(self):
        """Let switch toggle between inside or outside temperature."""
        return self._temp_toggle

    @temp_toggle.setter
    def temp_toggle(self, value):
        self._temp_toggle = value

    @property
    def control_toggle(self):
        """Toggle automation."""
        return self._control_toggle

    @control_toggle.setter
    def control_toggle(self, value):
        self._control_toggle = value

    @property
    def manual_toggle(self):
        """Toggle automation."""
        return self._manual_toggle

    @manual_toggle.setter
    def manual_toggle(self, value):
        self._manual_toggle = value


class AdaptiveCoverManager:
    """Track position changes."""

    def __init__(self, reset_duration: dict[str:int]) -> None:
        """Initialize the AdaptiveCoverManager."""
        self.covers: set[str] = set()

        self.manual_control: dict[str, bool] = {}
        self.manual_control_time: dict[str, dt.datetime] = {}
        self.reset_duration = dt.timedelta(**reset_duration)

    def add_covers(self, entity):
        """Update set with entities."""
        self.covers.update(entity)

    def handle_state_change(
        self,
        states_data,
        our_state,
        blind_type,
        allow_reset,
        wait_target_call,
        manual_threshold,
    ):
        """Process state change event."""
        event = states_data
        if event is None:
            return
        entity_id = event.entity_id
        if entity_id not in self.covers:
            return
        if wait_target_call.get(entity_id):
            return

        new_state = event.new_state

        if blind_type == "cover_tilt":
            new_position = new_state.attributes.get("current_tilt_position")
        else:
            new_position = new_state.attributes.get("current_position")

        if new_position != our_state:
            if (
                manual_threshold is not None
                and abs(our_state - new_position) < manual_threshold
            ):
                _LOGGER.debug(
                    "Position change is less than threshold %s for %s",
                    manual_threshold,
                    entity_id,
                )
                return
            _LOGGER.debug(
                "Set manual control for %s, for at least %s seconds, reset_allowed: %s",
                entity_id,
                self.reset_duration.total_seconds(),
                allow_reset,
            )
            self.mark_manual_control(entity_id)
            self.set_last_updated(entity_id, new_state, allow_reset)

    def set_last_updated(self, entity_id, new_state, allow_reset):
        """Set last updated time for manual control."""
        if entity_id not in self.manual_control_time or allow_reset:
            last_updated = new_state.last_updated
            self.manual_control_time[entity_id] = last_updated
            _LOGGER.debug(
                "Updating last updated to %s for %s. Allow reset:%s",
                last_updated,
                entity_id,
                allow_reset,
            )
        elif not allow_reset:
            _LOGGER.debug(
                "Already time specified for %s, reset is not allowed by user setting:%s",
                entity_id,
                allow_reset,
            )

    def mark_manual_control(self, cover: str) -> None:
        """Mark cover as under manual control."""
        self.manual_control[cover] = True

    async def reset_if_needed(self):
        """Reset manual control state of the covers."""
        current_time = dt.datetime.now(dt.UTC)
        manual_control_time_copy = dict(self.manual_control_time)
        for entity_id, last_updated in manual_control_time_copy.items():
            if current_time - last_updated > self.reset_duration:
                _LOGGER.debug(
                    "Resetting manual override for %s, because duration has elapsed",
                    entity_id,
                )
                self.reset(entity_id)

    def reset(self, entity_id):
        """Reset manual control for a cover."""
        self.manual_control[entity_id] = False
        self.manual_control_time.pop(entity_id, None)
        _LOGGER.debug("Reset manual override for %s", entity_id)

    def is_cover_manual(self, entity_id):
        """Check if a cover is under manual control."""
        return self.manual_control.get(entity_id, False)

    @property
    def binary_cover_manual(self):
        """Check if any cover is under manual control."""
        return any(value for value in self.manual_control.values())

    @property
    def manual_controlled(self):
        """Get the list of covers under manual control."""
        return [k for k, v in self.manual_control.items() if v]
