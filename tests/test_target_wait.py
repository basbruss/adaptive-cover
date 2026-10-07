"""Tests for automatic target acknowledgement and manual override detection."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.adaptive_cover.coordinator import (
    AdaptiveDataUpdateCoordinator,
    AdaptiveCoverManager,
    StateChangedData,
)


def _coordinator(position, target=34.2) -> AdaptiveDataUpdateCoordinator:
    """Build the minimum coordinator state required by the event processor."""
    coordinator = object.__new__(AdaptiveDataUpdateCoordinator)
    coordinator.logger = MagicMock()
    coordinator._cover_type = "cover_blind"
    coordinator.ignore_intermediate_states = False
    coordinator.wait_for_target = {"cover.test": True}
    coordinator.target_call = {"cover.test": target}
    coordinator._target_wait_unsub = {}

    old_state = MagicMock(state="opening")
    new_state = MagicMock(state="open")
    new_state.attributes = {"current_position": position}
    coordinator.state_change_data = StateChangedData(
        "cover.test", old_state, new_state
    )
    return coordinator


@pytest.mark.parametrize(
    ("reported", "target"),
    [(35, 34.2), (33, 33.5), (37, 36.35), (28, 27.8), (24, 24.76)],
)
def test_rounded_position_acknowledges_automatic_target(reported, target):
    """Integer feedback within one point must release target waiting."""
    coordinator = _coordinator(reported, target)

    assert coordinator.process_entity_state_change() is True


def test_different_position_does_not_acknowledge_target():
    """A meaningful position difference remains eligible for manual detection."""
    coordinator = _coordinator(36, 34.2)

    assert coordinator.process_entity_state_change() is False


def test_missing_position_does_not_acknowledge_target():
    """Unavailable position feedback must not be treated as target arrival."""
    coordinator = _coordinator(None)

    assert coordinator.process_entity_state_change() is False


def test_clear_target_wait_cancels_timeout_and_removes_target():
    """Acknowledgement cleanup must release the wait and cancel its failsafe."""
    coordinator = _coordinator(35)
    cancel_timeout = MagicMock()
    coordinator._target_wait_unsub["cover.test"] = cancel_timeout

    coordinator._clear_target_wait("cover.test")

    assert coordinator.wait_for_target["cover.test"] is False
    assert "cover.test" not in coordinator.target_call
    cancel_timeout.assert_called_once_with()


def test_repeated_rounded_terminal_event_is_not_manual():
    """A second terminal event with rounded feedback must remain automatic."""
    manager = AdaptiveCoverManager({"minutes": 90}, MagicMock())
    manager.add_covers(["cover.test"])
    new_state = MagicMock()
    new_state.attributes = {"current_position": 35}
    state_change = StateChangedData("cover.test", MagicMock(), new_state)

    manager.handle_state_change(
        state_change,
        34.2,
        "cover_blind",
        False,
        {"cover.test": False},
        None,
    )

    assert manager.is_cover_manual("cover.test") is False


@pytest.mark.asyncio
async def test_reconnect_from_unavailable_is_not_manual():
    """The first usable state after a reconnect must not become a manual move."""
    coordinator = object.__new__(AdaptiveDataUpdateCoordinator)
    coordinator.logger = MagicMock()
    coordinator.state_change_data = None
    coordinator.async_refresh = AsyncMock()
    old_state = MagicMock(state="unavailable")
    new_state = MagicMock(state="open")
    event = MagicMock(
        data={
            "entity_id": "cover.test",
            "old_state": old_state,
            "new_state": new_state,
        }
    )

    await coordinator.async_check_cover_state_change(event)

    coordinator.async_refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_transition_to_unavailable_is_not_manual():
    """A cover going offline must not become a manual move."""
    coordinator = object.__new__(AdaptiveDataUpdateCoordinator)
    coordinator.logger = MagicMock()
    coordinator.state_change_data = None
    coordinator.async_refresh = AsyncMock()
    old_state = MagicMock(state="open")
    new_state = MagicMock(state="unavailable")
    event = MagicMock(
        data={
            "entity_id": "cover.test",
            "old_state": old_state,
            "new_state": new_state,
        }
    )

    await coordinator.async_check_cover_state_change(event)

    coordinator.async_refresh.assert_not_awaited()
