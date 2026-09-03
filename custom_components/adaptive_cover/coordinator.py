"""The Coordinator for Adaptive Cover."""

from __future__ import annotations

import asyncio
import datetime as dt
from dataclasses import dataclass

import numpy as np
import pytz
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_SET_COVER_POSITION,
    SERVICE_SET_COVER_TILT_POSITION,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.event import async_call_later, async_track_point_in_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .config_context_adapter import ConfigContextAdapter

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
    CONF_ENABLE_MAX_POSITION,
    CONF_ENABLE_MIN_POSITION,
    CONF_END_ENTITY,
    CONF_END_TIME,
    CONF_ENTITIES,
    CONF_FOV_LEFT,
    CONF_FOV_RIGHT,
    CONF_HEIGHT_WIN,
    CONF_INTERP,
    CONF_INTERP_END,
    CONF_INTERP_LIST,
    CONF_INTERP_LIST_NEW,
    CONF_INTERP_START,
    CONF_INVERSE_STATE,
    CONF_IRRADIANCE_ENTITY,
    CONF_IRRADIANCE_THRESHOLD,
    CONF_LENGTH_AWNING,
    CONF_LUX_ENTITY,
    CONF_LUX_THRESHOLD,
    CONF_MANUAL_IGNORE_INTERMEDIATE,
    CONF_MANUAL_OVERRIDE_DURATION,
    CONF_MANUAL_OVERRIDE_RESET,
    CONF_MANUAL_THRESHOLD,
    CONF_MAX_ELEVATION,
    CONF_MAX_POSITION,
    CONF_MIN_ELEVATION,
    CONF_MIN_POSITION,
    CONF_NOTIFY_DELAY,
    CONF_NOTIFY_THRESHOLD,
    CONF_OUTSIDE_THRESHOLD,
    CONF_OUTSIDETEMP_ENTITY,
    CONF_PRESENCE_ENTITY,
    CONF_RETURN_SUNSET,
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
    EVENT_WILL_CLOSE,
    LOGGER,
)
from .helpers import get_datetime_from_str, get_last_updated, get_safe_state, is_presence_detected


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
    climate_debug: dict | None = None


class AdaptiveDataUpdateCoordinator(DataUpdateCoordinator[AdaptiveCoverData]):
    """Adaptive cover data update coordinator."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant) -> None:  # noqa: D107
        super().__init__(hass, LOGGER, name=DOMAIN)

        self.logger = ConfigContextAdapter(_LOGGER)
        self.logger.set_config_name(self.config_entry.data.get("name"))
        self._cover_type = self.config_entry.data.get("sensor_type")
        self._climate_mode = self.config_entry.options.get(CONF_CLIMATE_MODE, False)
        self._switch_mode = True if self._climate_mode else False
        self._inverse_state = self.config_entry.options.get(CONF_INVERSE_STATE, False)
        self._use_interpolation = self.config_entry.options.get(CONF_INTERP, False)
        self._track_end_time = self.config_entry.options.get(CONF_RETURN_SUNSET)
        self._temp_toggle = None
        self._control_toggle = None
        self._manual_toggle = None
        self._security_toggle = False  # OFF by default; restored by switch.py

        self._lux_toggle = (
            True if self.config_entry.options.get(CONF_LUX_ENTITY) else None
        )
        self._irradiance_toggle = (
            True if self.config_entry.options.get(CONF_IRRADIANCE_ENTITY) else None
        )

        self._start_time = None
        self._sun_end_time = None
        self._sun_start_time = None
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
        self.climate_state = None
        self.control_method = "intermediate"
        self.state_change_data: StateChangedData | None = None
        self.manager = AdaptiveCoverManager(self.manual_duration, self.logger)
        self.wait_for_target = {}
        self.target_call = {}
        self._climate_debug: dict | None = None
        self.ignore_intermediate_states = self.config_entry.options.get(
            CONF_MANUAL_IGNORE_INTERMEDIATE, False
        )
        self._update_listener = None
        self._scheduled_time = dt.datetime.now()

        self._cached_options = None

        # Pre-close notification (see EVENT_WILL_CLOSE): a target position at
        # or below the threshold is delayed by this many seconds, firing an
        # event first, so users can hook a warning before the cover actually
        # moves. 0 disables the feature entirely. Cancelled entries in
        # self._pending_close are covers currently waiting out that delay.
        # NumberSelector round-trips as a float (e.g. 60.0); cast once here
        # so every consumer (the event payload, async_call_later) gets a
        # plain int rather than a "close in 60.0s" event.
        self._notify_delay = int(
            self.config_entry.options.get(CONF_NOTIFY_DELAY, 0)
        )
        self._notify_threshold = int(
            self.config_entry.options.get(CONF_NOTIFY_THRESHOLD, 20)
        )
        self._pending_close: dict[str, CALLBACK_TYPE] = {}
        self.config_entry.async_on_unload(self._async_cancel_pending_close_notices)

    async def async_config_entry_first_refresh(self) -> None:
        """Config entry first refresh."""
        self.first_refresh = True
        await super().async_config_entry_first_refresh()
        self.logger.debug("Config entry first refresh")

    async def async_timed_refresh(self, event) -> None:
        """Control state at end time."""
        now = dt.datetime.now()
        time = self.end_time
        if self.end_time_entity is not None:
            time = get_safe_state(self.hass, self.end_time_entity)

        self.logger.debug("Checking timed refresh. End time: %s, now: %s", time, now)

        time_check = now - get_datetime_from_str(time)
        if time is not None and (time_check <= dt.timedelta(seconds=1)):
            self.timed_refresh = True
            self.logger.debug("Timed refresh triggered")
            await self.async_refresh()
        else:
            self.logger.debug("Timed refresh, but: not equal to end time")

    async def async_check_entity_state_change(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Fetch and process state change event."""
        self.logger.debug("Entity state change")
        self.state_change = True
        await self.async_refresh()

    async def async_check_cover_state_change(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Fetch and process state change event."""
        self.logger.debug("Cover state change")
        data = event.data
        if data["old_state"] is None:
            self.logger.debug("Old state is None")
            return
        self.state_change_data = StateChangedData(
            data["entity_id"], data["old_state"], data["new_state"]
        )
        if self.state_change_data.old_state.state != "unknown":
            self.cover_state_change = True
            self.process_entity_state_change()
            await self.async_refresh()
        else:
            self.logger.debug("Old state is unknown, not processing")

    def process_entity_state_change(self):
        """Process state change event."""
        event = self.state_change_data
        self.logger.debug("Processing state change event: %s", event)
        entity_id = event.entity_id
        if self.ignore_intermediate_states and event.new_state.state in [
            "opening",
            "closing",
        ]:
            self.logger.debug("Ignoring intermediate state change for %s", entity_id)
            return
        if self.wait_for_target.get(entity_id):
            position = event.new_state.attributes.get(
                "current_position"
                if self._cover_type != "cover_tilt"
                else "current_tilt_position"
            )
            if position == self.target_call.get(entity_id):
                self.wait_for_target[entity_id] = False
                self.logger.debug("Position %s reached for %s", position, entity_id)
            self.logger.debug("Wait for target: %s", self.wait_for_target)
        else:
            self.logger.debug("No wait for target call for %s", entity_id)

    @callback
    def _async_cancel_update_listener(self) -> None:
        """Cancel the scheduled update."""
        if self._update_listener:
            self._update_listener()
            self._update_listener = None

    async def async_timed_end_time(self) -> None:
        """Control state at end time."""
        self.logger.debug("Scheduling end time update at %s", self._end_time)
        self._async_cancel_update_listener()
        self.logger.debug(
            "End time: %s, Track end time: %s, Scheduled time: %s, Condition: %s",
            self._end_time,
            self._track_end_time,
            self._scheduled_time,
            self._end_time > self._scheduled_time,
        )
        self._update_listener = async_track_point_in_time(
            self.hass, self.async_timed_refresh, self._end_time
        )
        self._scheduled_time = self._end_time

    async def _async_update_data(self) -> AdaptiveCoverData:
        self.logger.debug("Updating data")
        if self.first_refresh:
            self._cached_options = self.config_entry.options

        options = self.config_entry.options
        self._update_options(options)

        cover_data = self.get_blind_data(options=options)

        self._update_manager_and_covers()

        if self._climate_mode:
            self.climate_mode_data(options, cover_data)
        else:
            self.logger.debug("Control method is %s", self.control_method)

        self.normal_cover_state = NormalCoverState(cover_data)
        self.logger.debug(
            "Determined normal cover state to be %s", self.normal_cover_state
        )

        self.default_state = round(self.normal_cover_state.get_state())
        self.logger.debug("Determined default state to be %s", self.default_state)
        state = self.state

        await self.manager.reset_if_needed()

        if (
            self._end_time
            and self._track_end_time
            and self._end_time > self._scheduled_time
        ):
            await self.async_timed_end_time()

        if self.state_change:
            await self.async_handle_state_change(state, options)
        if self.cover_state_change:
            await self.async_handle_cover_state_change(state)
        if self.first_refresh:
            await self.async_handle_first_refresh(state, options)
        if self.timed_refresh:
            await self.async_handle_timed_refresh(options)

        normal_cover = self.normal_cover_state.cover
        if (
            self.first_refresh
            or self._sun_start_time is None
            or dt.datetime.now(pytz.UTC).date() != self._sun_start_time.date()
        ):
            self.logger.debug("Calculating solar times")
            loop = asyncio.get_event_loop()
            start, end = await loop.run_in_executor(None, normal_cover.solar_times)
            self._sun_start_time = start
            self._sun_end_time = end
            self.logger.debug("Sun start time: %s, Sun end time: %s", start, end)
        else:
            start, end = self._sun_start_time, self._sun_end_time
        return AdaptiveCoverData(
            climate_mode_toggle=self.switch_mode,
            states={
                "state": state,
                "start": start,
                "end": end,
                "control": self.control_method,
                "sun_motion": normal_cover.valid,
                "manual_override": self.manager.binary_cover_manual,
                "manual_list": self.manager.manual_controlled,
            },
            attributes={
                "default": options.get(CONF_DEFAULT_HEIGHT),
                "sunset_default": options.get(CONF_SUNSET_POS),
                "sunset_offset": options.get(CONF_SUNSET_OFFSET),
                "azimuth_window": options.get(CONF_AZIMUTH),
                "field_of_view": [
                    options.get(CONF_FOV_LEFT),
                    options.get(CONF_FOV_RIGHT),
                ],
                "blind_spot": options.get(CONF_BLIND_SPOT_ELEVATION),
            },
            climate_debug=self._climate_debug,
        )

    async def async_handle_state_change(self, state: int, options):
        """Handle state change from tracked entities.

        Security mode takes priority over adaptive positioning:
        when active, every cover (except those in manual override) is moved
        to the security position instead of the calculated adaptive position.
        """
        if self.control_toggle:
            for cover in self.entities:
                if self.security_active:
                    await self._apply_security_position(cover, options)
                else:
                    await self.async_handle_call_service(cover, state, options)
        else:
            self.logger.debug("State change but control toggle is off")
        self.state_change = False
        self.logger.debug("State change handled")

    async def async_handle_cover_state_change(self, state: int):
        """Handle state change from assigned covers."""
        if self.manual_toggle and self.control_toggle:
            self.manager.handle_state_change(
                self.state_change_data,
                state,
                self._cover_type,
                self.manual_reset,
                self.wait_for_target,
                self.manual_threshold,
            )
        self.cover_state_change = False
        self.logger.debug("Cover state change handled")

    async def async_handle_first_refresh(self, state: int, options):
        """Handle first refresh.

        Security mode is applied immediately on startup when active.
        """
        if self.control_toggle:
            for cover in self.entities:
                if self.security_active:
                    await self._apply_security_position(cover, options)
                elif (
                    self.check_adaptive_time
                    and not self.manager.is_cover_manual(cover)
                    and self.check_position_delta(cover, state, options)
                ):
                    await self.async_set_position(cover, state)
        else:
            self.logger.debug("First refresh but control toggle is off")
        self.first_refresh = False
        self.logger.debug("First refresh handled")

    async def async_handle_timed_refresh(self, options):
        """Handle timed refresh (sunset position).

        Security mode overrides the sunset position when active.
        """
        self.logger.debug(
            "This is a timed refresh, using sunset position: %s",
            options.get(CONF_SUNSET_POS),
        )
        if self.control_toggle:
            for cover in self.entities:
                if self.security_active:
                    await self._apply_security_position(cover, options)
                else:
                    sunset_position = (
                        inverse_state(options.get(CONF_SUNSET_POS))
                        if self._inverse_state
                        else options.get(CONF_SUNSET_POS)
                    )
                    # Routed through async_set_position (not called directly)
                    # so the sunset close is subject to the same pre-close
                    # notification as any other close — this is, in fact,
                    # the scenario CONF_NOTIFY_DELAY exists for.
                    await self.async_set_position(cover, sunset_position)
        else:
            self.logger.debug("Timed refresh but control toggle is off")
        self.timed_refresh = False
        self.logger.debug("Timed refresh handled")

    async def async_handle_call_service(self, entity, state: int, options):
        """Handle call service."""
        if (
            self.check_adaptive_time
            and self.check_position_delta(entity, state, options)
            and self.check_time_delta(entity)
            and not self.manager.is_cover_manual(entity)
        ):
            await self.async_set_position(entity, state)

    async def async_set_position(self, entity, state: int):
        """Call service to set cover position.

        If pre-close notification is configured (CONF_NOTIFY_DELAY > 0) and
        this move crosses into "closing" territory, the move is delayed and
        EVENT_WILL_CLOSE is fired first — see _schedule_close_notice.

        Three cases, handled in this order:

        1. Target is above the notify threshold ("opening" or "not closing"
           enough to matter): any pending close for this entity is a stale
           decision that's just been superseded — cancel it, then apply the
           new, safer position right away. This is deliberately unconditional
           (not gated behind a threshold check first) so a legitimate "open
           back up" decision is never swallowed by an in-flight close timer.
        2. Target is at/below the threshold and a close is already counting
           down for this entity: do nothing. Letting the existing timer run
           to completion is the whole point — without this, the very next
           refresh cycle that reaches the same "close" conclusion would
           short-circuit the delay by falling through to case 3 below.
        3. Target is at/below the threshold and nothing is pending: schedule
           a new notice (or apply immediately if notifications are off).

        Two known, deliberately-accepted limitations, rather than silently
        left unhandled:

        - If the cover's current position can't be read (case 3, ``current
          is None``), a notice is fired on the safe assumption that it's
          worth a heads-up. ``async_set_manual_position`` may then no-op at
          apply time (it also can't confirm the position differs), so the
          event can rarely announce a move that doesn't actually happen. The
          alternative — staying silent whenever the position is unknown — was
          judged worse: it would mean never warning at all for a cover whose
          state is flaky, which is exactly when a warning matters most.
        - A very long delay (up to 600s) applies the position computed
          *when the notice was scheduled*; case 2 doesn't refresh it if the
          decision's magnitude changes while still below the threshold (a
          higher, still-closing value doesn't retrigger case 1). The error
          this can introduce is bounded to the [0, notify_threshold] range,
          and is expected to matter only at delays well past what anyone
          would realistically configure for a "you're about to be shut out"
          warning.
        """
        if state > self._notify_threshold:
            self._cancel_pending_close(entity)
            await self.async_set_manual_position(entity, state)
            return
        if entity in self._pending_close:
            return
        if self._notify_delay > 0:
            current = self._get_current_position(entity)
            if current is None or current > self._notify_threshold:
                self._schedule_close_notice(entity, state)
                return
        await self.async_set_manual_position(entity, state)

    def _cancel_pending_close(self, entity: str) -> None:
        """Cancel and drop a pending close notice for entity, if any."""
        cancel = self._pending_close.pop(entity, None)
        if cancel is not None:
            cancel()
            self.logger.debug(
                "Cancelled pending close notice for %s: superseded by a "
                "newer, non-closing decision",
                entity,
            )

    def _schedule_close_notice(self, entity: str, state: int) -> None:
        """Fire EVENT_WILL_CLOSE, then apply the position after the delay."""
        self.hass.bus.async_fire(
            EVENT_WILL_CLOSE,
            {
                "entity_id": entity,
                "target_position": state,
                "reason": self.control_method,
                "delay_seconds": self._notify_delay,
            },
        )
        self.logger.debug(
            "Delaying close of %s to %s%% by %ss (reason=%s)",
            entity,
            state,
            self._notify_delay,
            self.control_method,
        )

        async def _apply_after_delay(_now) -> None:
            self._pending_close.pop(entity, None)
            if not self.control_toggle:
                # The whole point of the notice is to give someone a window
                # to react — turning adaptive control off during that window
                # is exactly the reaction it's meant to allow for.
                self.logger.debug(
                    "Skipping delayed close of %s: control toggle turned "
                    "off during the notice delay",
                    entity,
                )
                return
            if self.manager.is_cover_manual(entity):
                self.logger.debug(
                    "Skipping delayed close of %s: manual override started "
                    "during the notice delay",
                    entity,
                )
                return
            await self.async_set_manual_position(entity, state)

        self._pending_close[entity] = async_call_later(
            self.hass, self._notify_delay, _apply_after_delay
        )

    @callback
    def _async_cancel_pending_close_notices(self) -> None:
        """Cancel any pending delayed close when the entry unloads."""
        for cancel in self._pending_close.values():
            cancel()
        self._pending_close.clear()

    async def async_set_manual_position(self, entity, state):
        """Call service to set cover position."""
        if self.check_position(entity, state):
            service = SERVICE_SET_COVER_POSITION
            service_data = {}
            service_data[ATTR_ENTITY_ID] = entity

            if self._cover_type == "cover_tilt":
                service = SERVICE_SET_COVER_TILT_POSITION
                service_data[ATTR_TILT_POSITION] = state
            else:
                service_data[ATTR_POSITION] = state

            self.wait_for_target[entity] = True
            self.target_call[entity] = state
            self.logger.debug(
                "Set wait for target %s and target call %s",
                self.wait_for_target,
                self.target_call,
            )
            self.logger.debug("Run %s with data %s", service, service_data)
            await self.hass.services.async_call(COVER_DOMAIN, service, service_data)

    async def _apply_security_position(self, entity: str, options) -> None:
        """Move a cover to its security position.

        Security position rules:
          - Climate mode active + branch is winter or intermediate
              → CONF_MIN_POSITION (keeps the house ventilated / slightly shaded)
          - All other cases (no climate, or climate summer)
              → 0 % (fully closed — maximum protection)

        Covers in manual override are skipped: the user's explicit action
        takes precedence over the security mode.

        Unlike ``async_set_position``, this method does NOT call
        ``manager.mark_manual_control`` — security is not a user gesture and
        must not block the automatic return to adaptive positioning when
        presence is restored.

        It also does NOT go through the pre-close notification delay: security
        mode means "nobody's home, secure the house now" — waiting out
        CONF_NOTIFY_DELAY (up to 10 minutes) would defeat the point. It DOES
        cancel any notice already counting down for this entity, so a stale
        timer can't re-apply an outdated target position after security has
        already moved the cover.
        """
        if self.manager.is_cover_manual(entity):
            self.logger.debug(
                "Security mode: skipping %s (manual override active)", entity
            )
            return

        self._cancel_pending_close(entity)

        if self._climate_mode and self.control_method in ("intermediate", "winter"):
            pos = options.get(CONF_MIN_POSITION) or 0
            self.logger.debug(
                "Security mode: %s → min_position=%s (climate branch: %s)",
                entity,
                pos,
                self.control_method,
            )
        else:
            pos = 0
            self.logger.debug(
                "Security mode: %s → 0 %% (full close — no climate or summer branch)",
                entity,
            )

        await self.async_set_manual_position(entity, pos)

    @property
    def security_active(self) -> bool:
        """True when security mode is ON and no presence detected.

        Returns False (inactive) when no presence entity is configured —
        security mode requires a presence sensor to be meaningful.
        """
        if not self._security_toggle:
            return False
        presence_entity = self.config_entry.options.get(CONF_PRESENCE_ENTITY)
        if presence_entity is None:
            return False
        active = not is_presence_detected(self.hass, presence_entity)
        self.logger.debug(
            "Security active? %s (presence_entity=%s)", active, presence_entity
        )
        return active

    def _update_options(self, options):
        """Update options."""
        self.entities = options.get(CONF_ENTITIES, [])
        self.min_change = options.get(CONF_DELTA_POSITION, 1)
        self.time_threshold = options.get(CONF_DELTA_TIME, 2)
        self.start_time = options.get(CONF_START_TIME)
        self.start_time_entity = options.get(CONF_START_ENTITY)
        self.end_time = options.get(CONF_END_TIME)
        self.end_time_entity = options.get(CONF_END_ENTITY)
        self.manual_reset = options.get(CONF_MANUAL_OVERRIDE_RESET, False)
        self.manual_duration = options.get(
            CONF_MANUAL_OVERRIDE_DURATION, {"minutes": 15}
        )
        self.manual_threshold = options.get(CONF_MANUAL_THRESHOLD)
        self.start_value = options.get(CONF_INTERP_START)
        self.end_value = options.get(CONF_INTERP_END)
        self.normal_list = options.get(CONF_INTERP_LIST)
        self.new_list = options.get(CONF_INTERP_LIST_NEW)

    def _update_manager_and_covers(self):
        self.manager.add_covers(self.entities)
        if not self._manual_toggle:
            for entity in self.manager.manual_controlled:
                self.manager.reset(entity)

    def get_blind_data(self, options):
        """Assign correct class for type of blind."""
        if self._cover_type == "cover_blind":
            cover_data = AdaptiveVerticalCover(
                self.hass,
                self.logger,
                *self.pos_sun,
                *self.common_data(options),
                *self.vertical_data(options),
            )
        if self._cover_type == "cover_awning":
            cover_data = AdaptiveHorizontalCover(
                self.hass,
                self.logger,
                *self.pos_sun,
                *self.common_data(options),
                *self.vertical_data(options),
                *self.horizontal_data(options),
            )
        if self._cover_type == "cover_tilt":
            cover_data = AdaptiveTiltCover(
                self.hass,
                self.logger,
                *self.pos_sun,
                *self.common_data(options),
                *self.tilt_data(options),
            )
        return cover_data

    @property
    def check_adaptive_time(self):
        """Check if time is within start and end times."""
        if self._start_time and self._end_time and self._start_time > self._end_time:
            self.logger.error("Start time is after end time")
        return self.before_end_time and self.after_start_time

    @property
    def after_start_time(self):
        """Check if time is after start time."""
        now = dt.datetime.now()
        if self.start_time_entity is not None:
            time = get_datetime_from_str(
                get_safe_state(self.hass, self.start_time_entity)
            )
            self.logger.debug(
                "Start time: %s, now: %s, now >= time: %s ", time, now, now >= time
            )
            self._start_time = time
            return now >= time
        if self.start_time is not None:
            time = get_datetime_from_str(self.start_time)
            self.logger.debug(
                "Start time: %s, now: %s, now >= time: %s", time, now, now >= time
            )
            self._start_time = time
            return now >= time
        return True

    @property
    def _end_time(self) -> dt.datetime | None:
        """Get end time."""
        time = None
        if self.end_time_entity is not None:
            time = get_datetime_from_str(
                get_safe_state(self.hass, self.end_time_entity)
            )
        elif self.end_time is not None:
            time = get_datetime_from_str(self.end_time)
            if time.time() == dt.time(0, 0):
                time = time + dt.timedelta(days=1)
        return time

    @property
    def before_end_time(self):
        """Check if time is before end time."""
        if self._end_time is not None:
            now = dt.datetime.now()
            self.logger.debug(
                "End time: %s, now: %s, now < time: %s",
                self._end_time,
                now,
                now < self._end_time,
            )
            return now < self._end_time
        return True

    def _get_current_position(self, entity) -> int | None:
        """Get current position of cover (single state lookup)."""
        state = self.hass.states.get(entity)
        if state is None:
            return None
        attr = "current_tilt_position" if self._cover_type == "cover_tilt" else "current_position"
        return state.attributes.get(attr)

    def check_position(self, entity, state):
        """Check if position is different as state."""
        position = self._get_current_position(entity)
        if position is not None:
            return position != state
        self.logger.debug("Cover is already at position %s", state)
        return False

    def check_position_delta(self, entity, state: int, options):
        """Check cover positions to reduce calls."""
        position = self._get_current_position(entity)
        if position is not None:
            condition = abs(position - state) >= self.min_change
            self.logger.debug(
                "Entity: %s,  position: %s, state: %s, delta position: %s, min_change: %s, condition: %s",
                entity,
                position,
                state,
                abs(position - state),
                self.min_change,
                condition,
            )
            if state in [
                options.get(CONF_SUNSET_POS),
                options.get(CONF_DEFAULT_HEIGHT),
                0,
                100,
            ]:
                condition = True
            return condition
        return True

    def check_time_delta(self, entity):
        """Check if time delta is passed."""
        now = dt.datetime.now(dt.UTC)
        last_updated = get_last_updated(entity, self.hass)
        if last_updated is not None:
            condition = now - last_updated >= dt.timedelta(minutes=self.time_threshold)
            self.logger.debug(
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
        """Fetch sun azimuth + elevation in a single state lookup."""
        state = self.hass.states.get("sun.sun")
        if state is None:
            return [None, None]
        attrs = state.attributes
        return [attrs.get("azimuth"), attrs.get("elevation")]

    def common_data(self, options):
        """Update shared parameters."""
        return [
            options.get(CONF_SUNSET_POS),
            options.get(CONF_SUNSET_OFFSET),
            options.get(CONF_SUNRISE_OFFSET, options.get(CONF_SUNSET_OFFSET)),
            self.hass.config.time_zone,
            options.get(CONF_FOV_LEFT),
            options.get(CONF_FOV_RIGHT),
            options.get(CONF_AZIMUTH),
            options.get(CONF_DEFAULT_HEIGHT),
            options.get(CONF_MAX_POSITION),
            options.get(CONF_MIN_POSITION),
            options.get(CONF_ENABLE_MAX_POSITION, False),
            options.get(CONF_ENABLE_MIN_POSITION, False),
            options.get(CONF_BLIND_SPOT_LEFT),
            options.get(CONF_BLIND_SPOT_RIGHT),
            options.get(CONF_BLIND_SPOT_ELEVATION),
            options.get(CONF_ENABLE_BLIND_SPOT, False),
            options.get(CONF_MIN_ELEVATION, None),
            options.get(CONF_MAX_ELEVATION, None),
        ]

    def get_climate_data(self, options):
        """Update climate data."""
        return [
            self.hass,
            self.logger,
            options.get(CONF_TEMP_ENTITY),
            options.get(CONF_TEMP_LOW),
            options.get(CONF_TEMP_HIGH),
            options.get(CONF_PRESENCE_ENTITY),
            options.get(CONF_WEATHER_ENTITY),
            options.get(CONF_WEATHER_STATE),
            options.get(CONF_OUTSIDETEMP_ENTITY),
            self._temp_toggle,
            self._cover_type,
            options.get(CONF_TRANSPARENT_BLIND),
            options.get(CONF_LUX_ENTITY),
            options.get(CONF_IRRADIANCE_ENTITY),
            options.get(CONF_LUX_THRESHOLD),
            options.get(CONF_IRRADIANCE_THRESHOLD),
            options.get(CONF_OUTSIDE_THRESHOLD),
            self._lux_toggle,
            self._irradiance_toggle,
        ]

    def climate_mode_data(self, options, cover_data):
        """Update climate mode data and control method."""
        climate_args = self.get_climate_data(options)
        climate = ClimateCoverData(
            hass=climate_args[0],
            logger=climate_args[1],
            temp_entity=climate_args[2],
            temp_low=climate_args[3],
            temp_high=climate_args[4],
            presence_entity=climate_args[5],
            weather_entity=climate_args[6],
            weather_condition=climate_args[7],
            outside_entity=climate_args[8],
            temp_switch=climate_args[9],
            blind_type=climate_args[10],
            transparent_blind=climate_args[11],
            lux_entity=climate_args[12],
            irradiance_entity=climate_args[13],
            lux_threshold=climate_args[14],
            irradiance_threshold=climate_args[15],
            temp_summer_outside=climate_args[16],
            _use_lux=climate_args[17],
            _use_irradiance=climate_args[18],
        )

        climate_state_obj = ClimateCoverState(cover_data, climate)
        self.climate_state = round(climate_state_obj.get_state())
        climate_data = climate_state_obj.climate_data

        if climate_data.is_summer and self.switch_mode:
            self.control_method = "summer"
        elif climate_data.is_winter and self.switch_mode:
            self.control_method = "winter"
        else:
            self.control_method = "intermediate"

        self.logger.debug(
            "Climate mode control method was set to %s", self.control_method
        )

        inside_raw = climate_data.inside_temperature
        outside_raw = climate_data.outside_temperature
        self._climate_debug = {
            "is_winter": climate_data.is_winter,
            "is_summer": climate_data.is_summer,
            "is_presence": climate_data.is_presence,
            "sun_in_window": climate_state_obj.cover.valid,
            "temp_inside": float(inside_raw) if inside_raw is not None else None,
            "temp_outside": float(outside_raw) if outside_raw is not None else None,
            "temp_used_winter": climate_data.temperature_for_winter,
            "temp_used_summer": climate_data.temperature_for_summer,
            "temp_low": climate_data.temp_low,
            "temp_high": climate_data.temp_high,
            "temp_switch": climate_data.temp_switch,
            "is_sunny": climate_data.is_sunny,
            "lux_below_threshold": climate_data.lux,
            "irradiance_below_threshold": climate_data.irradiance,
            "active_branch": self.control_method,
        }

    @staticmethod
    def vertical_data(options):
        """Update data for vertical blinds."""
        return [
            options.get(CONF_DISTANCE),
            options.get(CONF_HEIGHT_WIN),
        ]

    @staticmethod
    def horizontal_data(options):
        """Update data for horizontal blinds."""
        return [
            options.get(CONF_LENGTH_AWNING),
            options.get(CONF_AWNING_ANGLE),
        ]

    @staticmethod
    def tilt_data(options):
        """Update data for tilted blinds."""
        return [
            options.get(CONF_TILT_DISTANCE),
            options.get(CONF_TILT_DEPTH),
            options.get(CONF_TILT_MODE),
        ]

    @property
    def state(self) -> int:
        """Handle the output of the state based on mode."""
        self.logger.debug(
            "Basic position: %s; Climate position: %s; Using climate position? %s",
            self.default_state,
            self.climate_state,
            self._switch_mode,
        )
        if self._switch_mode:
            state = self.climate_state
        else:
            state = self.default_state

        if self._use_interpolation:
            self.logger.debug("Interpolating position: %s", state)
            state = self.interpolate_states(state)

        if self._inverse_state and self._use_interpolation:
            self.logger.info(
                "Inverse state is not supported with interpolation, "
                "you can inverse the state by arranging the list from high to low"
            )

        if self._inverse_state and not self._use_interpolation:
            state = inverse_state(state)
            self.logger.debug("Inversed position: %s", state)

        self.logger.debug("Final position to use: %s", state)
        return state

    def interpolate_states(self, state):
        """Interpolate states."""
        normal_range = [0, 100]
        new_range = []
        if self.start_value and self.end_value:
            new_range = [self.start_value, self.end_value]
        if self.normal_list and self.new_list:
            normal_range = list(map(int, self.normal_list))
            new_range = list(map(int, self.new_list))
        if new_range:
            state = np.interp(state, normal_range, new_range)
            if state == new_range[0]:
                state = 0
            if state == new_range[-1]:
                state = 100
        return state

    @property
    def switch_mode(self):
        """Let switch toggle climate mode."""
        return self._switch_mode

    @switch_mode.setter
    def switch_mode(self, value):
        """Set climate switch mode."""
        self._switch_mode = value

    @property
    def temp_toggle(self):
        """Let switch toggle between inside or outside temperature."""
        return self._temp_toggle

    @temp_toggle.setter
    def temp_toggle(self, value):
        """Set outside temperature toggle."""
        self._temp_toggle = value

    @property
    def control_toggle(self):
        """Toggle automation."""
        return self._control_toggle

    @control_toggle.setter
    def control_toggle(self, value):
        """Set automation control toggle."""
        self._control_toggle = value

    @property
    def manual_toggle(self):
        """Toggle automation."""
        return self._manual_toggle

    @manual_toggle.setter
    def manual_toggle(self, value):
        """Set manual override toggle."""
        self._manual_toggle = value

    @property
    def lux_toggle(self):
        """Toggle automation."""
        return self._lux_toggle

    @lux_toggle.setter
    def lux_toggle(self, value):
        """Set lux sensor toggle."""
        self._lux_toggle = value

    @property
    def irradiance_toggle(self):
        """Toggle automation."""
        return self._irradiance_toggle

    @irradiance_toggle.setter
    def irradiance_toggle(self, value):
        """Set irradiance sensor toggle."""
        self._irradiance_toggle = value

    @property
    def security_toggle(self):
        """Security mode toggle — closes covers when nobody is home."""
        return self._security_toggle

    @security_toggle.setter
    def security_toggle(self, value):
        """Set security mode toggle."""
        self._security_toggle = value


class AdaptiveCoverManager:
    """Track position changes."""

    def __init__(self, reset_duration: dict[str:int], logger) -> None:
        """Initialize the AdaptiveCoverManager."""
        self.covers: set[str] = set()

        self.manual_control: dict[str, bool] = {}
        self.manual_control_time: dict[str, dt.datetime] = {}
        self.reset_duration = dt.timedelta(**reset_duration)
        self.logger = logger

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
                self.logger.debug(
                    "Position change is less than threshold %s for %s",
                    manual_threshold,
                    entity_id,
                )
                return
            self.logger.debug(
                "Manual change detected for %s. Our state: %s, new state: %s",
                entity_id,
                our_state,
                new_position,
            )
            self.logger.debug(
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
            self.logger.debug(
                "Updating last updated for manual control to %s for %s. Allow reset:%s",
                last_updated,
                entity_id,
                allow_reset,
            )
        elif not allow_reset:
            self.logger.debug(
                "Already manual control time specified for %s, reset is not allowed by user setting:%s",
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
                self.logger.debug(
                    "Resetting manual override for %s, because duration has elapsed",
                    entity_id,
                )
                self.reset(entity_id)

    def reset(self, entity_id):
        """Reset manual control for a cover."""
        self.manual_control[entity_id] = False
        self.manual_control_time.pop(entity_id, None)
        self.logger.debug("Reset manual override for %s", entity_id)

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


def inverse_state(state: int) -> int:
    """Inverse state."""
    return 100 - state
