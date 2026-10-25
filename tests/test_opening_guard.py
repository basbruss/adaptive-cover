"""Tests for the window/door opening guard (#498) and the algorithmic entry point."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.adaptive_cover.const import CONF_OPENING_ENTITY
from custom_components.adaptive_cover.coordinator import (
    AdaptiveCoverManager,
    AdaptiveDataUpdateCoordinator,
)
from custom_components.adaptive_cover.helpers import is_opening_open

COVER = "cover.terrace"
SENSOR = "binary_sensor.terrace_door"


def _hass(states: dict[str, object]) -> MagicMock:
    """Return a hass mock serving *states* ({entity_id: state or (state, attrs)})."""
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
    *, position: int | None, door: str | None, inverse: bool = False
) -> AdaptiveDataUpdateCoordinator:
    states: dict[str, object] = {}
    if position is not None:
        states[COVER] = ("open", {"current_position": position})
    if door is not None:
        states[SENSOR] = door
    coordinator = object.__new__(AdaptiveDataUpdateCoordinator)
    coordinator.hass = _hass(states)
    coordinator.logger = MagicMock()
    coordinator._cover_type = "cover_blind"
    coordinator._inverse_state = inverse
    coordinator.config_entry = MagicMock(options={CONF_OPENING_ENTITY: SENSOR})
    coordinator.async_set_manual_position = AsyncMock()
    coordinator._notify_delay = 0
    coordinator._notify_threshold = 20
    coordinator._pending_close = {}
    return coordinator


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("off", False),
        ("on", True),
        ("On", True),
        ("unknown", True),
        ("unavailable", True),
        ("", True),
        (None, True),  # entity missing
    ],
)
def test_is_opening_open_fail_safe(state, expected):
    """Only an exact "off" means closed; anything unclear counts as open."""
    hass = _hass({} if state is None else {SENSOR: state})
    assert is_opening_open(hass, SENSOR) is expected


def test_is_opening_open_without_sensor_never_blocks():
    """No sensor configured means nothing to guard."""
    assert is_opening_open(_hass({}), None) is False


@pytest.mark.parametrize(
    ("inverse", "current", "target", "closing"),
    [
        (False, 80, 20, True),
        (False, 20, 80, False),
        (False, 50, 50, False),
        (True, 20, 80, True),  # inverted: 100 = closed
        (True, 80, 20, False),
        (True, 50, 50, False),
    ],
)
def test_is_closing_move_respects_inverse_state(inverse, current, target, closing):
    """The closing direction flips with CONF_INVERSE_STATE."""
    coordinator = _coordinator(position=current, door="off", inverse=inverse)
    assert coordinator.is_closing_move(current, target) is closing


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("inverse", "current", "target", "sent"),
    [
        (False, 80, 10, False),  # closing onto open door: withheld
        (False, 10, 80, True),  # opening: always allowed
        (True, 20, 90, False),  # inverted closing: withheld
        (True, 90, 20, True),  # inverted opening: allowed
    ],
)
async def test_adaptive_move_guarded_when_door_open(inverse, current, target, sent):
    """Algorithmic closing moves are withheld while the door is open."""
    coordinator = _coordinator(position=current, door="on", inverse=inverse)

    result = await coordinator.async_set_adaptive_position(COVER, target)

    assert result is sent
    assert coordinator.async_set_manual_position.await_count == (1 if sent else 0)


@pytest.mark.asyncio
async def test_adaptive_move_passes_when_door_closed():
    """With the door closed the guard is transparent."""
    coordinator = _coordinator(position=80, door="off")

    assert await coordinator.async_set_adaptive_position(COVER, 0) is True
    coordinator.async_set_manual_position.assert_awaited_once_with(COVER, 0)


@pytest.mark.asyncio
async def test_unknown_current_position_is_not_blocked():
    """Unknown position is left to check_position, which sends nothing anyway."""
    coordinator = _coordinator(position=None, door="on")

    assert await coordinator.async_set_adaptive_position(COVER, 0) is True


@pytest.mark.asyncio
async def test_user_initiated_move_ignores_door():
    """async_set_position (cover entity, scenes, select) is never guarded."""
    coordinator = _coordinator(position=80, door="on")

    await coordinator.async_set_position(COVER, 0)

    coordinator.async_set_manual_position.assert_awaited_once_with(COVER, 0)


@pytest.mark.asyncio
async def test_never_auto_correct_cover_is_left_alone_by_security():
    """A cover held by never_auto_correct (#501) stays manual under security mode."""
    coordinator = _coordinator(position=80, door="off")
    coordinator.manager = AdaptiveCoverManager({"minutes": 15}, MagicMock())
    coordinator.manager.add_covers([COVER])
    coordinator.manager.mark_manual_control(COVER)
    coordinator.never_auto_correct = True
    coordinator._climate_mode = False

    await coordinator._apply_security_position(COVER, coordinator.config_entry.options)

    coordinator.async_set_manual_position.assert_not_awaited()
