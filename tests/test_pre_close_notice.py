"""Tests for the pre-close notification (#494) on the algorithmic entry point."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.adaptive_cover.const import CONF_OPENING_ENTITY, EVENT_WILL_CLOSE
from custom_components.adaptive_cover.coordinator import (
    AdaptiveCoverManager,
    AdaptiveDataUpdateCoordinator,
)

COVER = "cover.terrace"
SENSOR = "binary_sensor.terrace_door"
CALL_LATER = "custom_components.adaptive_cover.coordinator.async_call_later"


def _hass(states: dict) -> MagicMock:
    hass = MagicMock()

    def _get(entity_id):
        if entity_id not in states:
            return None
        value = states[entity_id]
        state = MagicMock()
        if isinstance(value, tuple):
            state.state, state.attributes = value
        else:
            state.state, state.attributes = value, {}
        return state

    hass.states.get = _get
    return hass


def _coordinator(
    position: int | None = 100,
    *,
    delay: int = 60,
    threshold: int = 20,
    inverse: bool = False,
    door: str | None = None,
):
    states: dict = {}
    if position is not None:
        states[COVER] = ("open", {"current_position": position})
    if door is not None:
        states[SENSOR] = door
    coordinator = object.__new__(AdaptiveDataUpdateCoordinator)
    coordinator.hass = _hass(states)
    coordinator.logger = MagicMock()
    coordinator._cover_type = "cover_blind"
    coordinator._inverse_state = inverse
    coordinator._notify_delay = delay
    coordinator._notify_threshold = threshold
    coordinator._pending_close = {}
    coordinator._target_wait_unsub = {}
    coordinator.wait_for_target = {}
    coordinator.target_call = {}
    coordinator.control_method = "summer"
    coordinator._control_toggle = True
    coordinator.manager = AdaptiveCoverManager({"minutes": 15}, MagicMock())
    coordinator.manager.add_covers([COVER])
    coordinator.config_entry = MagicMock(
        options={CONF_OPENING_ENTITY: SENSOR} if door is not None else {}
    )
    coordinator.hass.services.async_call = AsyncMock()
    return coordinator


def _sent_positions(coordinator) -> list[int]:
    return [
        call.args[2].get("position")
        for call in coordinator.hass.services.async_call.await_args_list
    ]


class _Timers:
    """Capture async_call_later callbacks instead of scheduling them."""

    def __init__(self) -> None:
        self.callbacks: list = []
        self.cancelled: list = []

    def __call__(self, _hass, _delay, action):
        self.callbacks.append(action)
        cancel = MagicMock()
        self.cancelled.append(cancel)
        return cancel

    def pending_close(self):
        # The target-wait failsafe is a functools.partial; the close notice
        # is a plain coroutine function.
        return [cb for cb in self.callbacks if not hasattr(cb, "func")]


@pytest.mark.asyncio
async def test_automatic_close_fires_event_and_waits():
    coordinator = _coordinator(position=100)
    timers = _Timers()
    with patch(CALL_LATER, timers):
        sent = await coordinator.async_set_adaptive_position(COVER, 0)

        assert sent is False
        assert _sent_positions(coordinator) == []
        coordinator.hass.bus.async_fire.assert_called_once_with(
            EVENT_WILL_CLOSE,
            {
                "entity_id": COVER,
                "target_position": 0,
                "reason": "summer",
                "delay_seconds": 60,
            },
        )

        await timers.pending_close()[0](None)

    assert _sent_positions(coordinator) == [0]
    assert COVER not in coordinator._pending_close


@pytest.mark.asyncio
async def test_repeated_refresh_does_not_collapse_the_delay():
    coordinator = _coordinator(position=100)
    with patch(CALL_LATER, _Timers()):
        await coordinator.async_set_adaptive_position(COVER, 0)
        await coordinator.async_set_adaptive_position(COVER, 5)

    assert _sent_positions(coordinator) == []
    assert coordinator.hass.bus.async_fire.call_count == 1


@pytest.mark.asyncio
async def test_open_decision_cancels_pending_close():
    coordinator = _coordinator(position=100)
    timers = _Timers()
    with patch(CALL_LATER, timers):
        await coordinator.async_set_adaptive_position(COVER, 0)
        cancel = coordinator._pending_close[COVER]
        await coordinator.async_set_adaptive_position(COVER, 70)

    cancel.assert_called_once_with()
    assert COVER not in coordinator._pending_close
    assert _sent_positions(coordinator) == [70]


@pytest.mark.asyncio
async def test_disabled_by_default():
    coordinator = _coordinator(position=100, delay=0)
    with patch(CALL_LATER, _Timers()):
        assert await coordinator.async_set_adaptive_position(COVER, 0) is True
    assert _sent_positions(coordinator) == [0]
    coordinator.hass.bus.async_fire.assert_not_called()


@pytest.mark.asyncio
async def test_already_in_close_zone_does_not_notify():
    coordinator = _coordinator(position=15)
    with patch(CALL_LATER, _Timers()):
        await coordinator.async_set_adaptive_position(COVER, 0)
    assert _sent_positions(coordinator) == [0]
    coordinator.hass.bus.async_fire.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("current", "target", "notifies"),
    [
        (0, 100, True),  # inverted: 100 = closed, 0 -> 100 enters zone
        (0, 85, True),  # 85 >= 100 - 20
        (0, 70, False),  # not in close zone
        (90, 100, False),  # already in close zone
    ],
)
async def test_threshold_respects_inverse_state(current, target, notifies):
    coordinator = _coordinator(position=current, inverse=True)
    with patch(CALL_LATER, _Timers()):
        await coordinator.async_set_adaptive_position(COVER, target)
    assert coordinator.hass.bus.async_fire.called is notifies
    assert _sent_positions(coordinator) == ([] if notifies else [target])


@pytest.mark.asyncio
async def test_user_initiated_move_is_immediate_and_cancels_notice():
    """async_set_position (scene.py / select.py / cover entity) never waits."""
    coordinator = _coordinator(position=100)
    with patch(CALL_LATER, _Timers()):
        await coordinator.async_set_adaptive_position(COVER, 0)
        cancel = coordinator._pending_close[COVER]

        await coordinator.async_set_position(COVER, 0)

    assert _sent_positions(coordinator) == [0]
    cancel.assert_called_once_with()
    assert coordinator.hass.bus.async_fire.call_count == 1


@pytest.mark.asyncio
async def test_scene_and_select_do_not_wait():
    """Hub scene and select close immediately even with a notice delay set."""
    from custom_components.adaptive_cover import scene, select

    coordinator = _coordinator(position=100)
    coordinator.entities = [COVER]
    coordinator.async_refresh = AsyncMock()
    hass = MagicMock()

    with patch(CALL_LATER, _Timers()), patch.object(
        scene, "iter_regular_coordinators", return_value=[coordinator]
    ), patch.object(select, "iter_regular_coordinators", return_value=[coordinator]):
        sc = object.__new__(scene.AdaptiveCoverScene)
        sc.hass, sc._mode = hass, "all_closed"
        sc.async_write_ha_state = MagicMock()
        await sc.async_activate()

        sel = object.__new__(select.AdaptiveControlModeSelect)
        sel.hass = hass
        await sel._apply_position(0)

    assert _sent_positions(coordinator) == [0, 0]
    coordinator.hass.bus.async_fire.assert_not_called()


@pytest.mark.asyncio
async def test_security_mode_skips_the_delay():
    coordinator = _coordinator(position=100)
    coordinator._climate_mode = False
    with patch(CALL_LATER, _Timers()):
        await coordinator._apply_security_position(COVER, {})
    assert _sent_positions(coordinator) == [0]
    coordinator.hass.bus.async_fire.assert_not_called()


@pytest.mark.asyncio
async def test_delayed_close_skipped_when_manual_override_starts():
    coordinator = _coordinator(position=100)
    timers = _Timers()
    with patch(CALL_LATER, timers):
        await coordinator.async_set_adaptive_position(COVER, 0)
        coordinator.manager.mark_manual_control(COVER)
        await timers.pending_close()[0](None)
    assert _sent_positions(coordinator) == []


@pytest.mark.asyncio
async def test_delayed_close_skipped_when_control_turned_off():
    coordinator = _coordinator(position=100)
    timers = _Timers()
    with patch(CALL_LATER, timers):
        await coordinator.async_set_adaptive_position(COVER, 0)
        coordinator._control_toggle = False
        await timers.pending_close()[0](None)
    assert _sent_positions(coordinator) == []


@pytest.mark.asyncio
async def test_delayed_close_rechecks_opening_sensor():
    """A door opened during the notice still blocks the delayed close."""
    coordinator = _coordinator(position=100, door="off")
    timers = _Timers()
    with patch(CALL_LATER, timers):
        await coordinator.async_set_adaptive_position(COVER, 0)
        coordinator.hass = _hass(
            {COVER: ("open", {"current_position": 100}), SENSOR: "on"}
        )
        coordinator.hass.services.async_call = AsyncMock()
        await timers.pending_close()[0](None)
    coordinator.hass.services.async_call.assert_not_awaited()


@pytest.mark.asyncio
async def test_open_door_withholds_before_notifying():
    """No event is fired for a close the opening guard would block anyway."""
    coordinator = _coordinator(position=100, door="on")
    with patch(CALL_LATER, _Timers()):
        assert await coordinator.async_set_adaptive_position(COVER, 0) is False
    coordinator.hass.bus.async_fire.assert_not_called()
    assert coordinator._pending_close == {}


def test_unload_cancels_pending_notices():
    coordinator = _coordinator()
    cancel = MagicMock()
    coordinator._pending_close = {COVER: cancel}
    coordinator._async_cancel_pending_close_notices()
    cancel.assert_called_once_with()
    assert coordinator._pending_close == {}
