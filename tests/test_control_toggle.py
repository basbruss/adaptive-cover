"""Tests for the Toggle Control switch's resume-on-turn-on behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.adaptive_cover.switch import AdaptiveCoverSwitch

COVER = "cover.test"


def _switch(*, control_on: bool) -> tuple[AdaptiveCoverSwitch, MagicMock]:
    """Return a Toggle Control switch over a coordinator with control *control_on*."""
    coordinator = MagicMock()
    coordinator.control_toggle = control_on
    coordinator.entities = [COVER]
    coordinator.state = 40
    coordinator.check_adaptive_time = True
    coordinator.manager.is_cover_manual.return_value = False
    coordinator.async_set_adaptive_position = AsyncMock()
    coordinator.async_refresh = AsyncMock()

    switch = object.__new__(AdaptiveCoverSwitch)
    switch.coordinator = coordinator
    switch._key = "control_toggle"
    switch._attr_is_on = control_on
    switch.schedule_update_ha_state = MagicMock()
    return switch, coordinator


@pytest.mark.asyncio
async def test_turning_control_on_resumes_the_covers():
    """Off -> on moves each cover to the computed position, as before."""
    switch, coordinator = _switch(control_on=False)
    await switch.async_turn_on()
    coordinator.async_set_adaptive_position.assert_awaited_once_with(COVER, 40)
    assert coordinator.control_toggle is True


@pytest.mark.asyncio
async def test_turning_on_a_switch_already_on_does_not_move_the_covers():
    """A repeated turn_on (an automation re-asserting state) is not a resume."""
    switch, coordinator = _switch(control_on=True)
    await switch.async_turn_on()
    coordinator.async_set_adaptive_position.assert_not_awaited()
    coordinator.async_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_control_turned_off_by_the_hub_still_resumes():
    """Control turned off by the All Blinds switch still resumes on turn_on.

    The hub clears coordinator.control_toggle without touching this entity, so
    the entity can still read on. Turning it on must resume.
    """
    switch, coordinator = _switch(control_on=False)
    switch._attr_is_on = True  # stale: the hub turned control off underneath it
    await switch.async_turn_on()
    coordinator.async_set_adaptive_position.assert_awaited_once_with(COVER, 40)


@pytest.mark.asyncio
async def test_control_turned_on_by_the_hub_still_resumes_from_the_entity():
    """Control turned on by the hub, entity still off: turning it on resumes.

    The hub can also set coordinator.control_toggle on while this entity reads
    off. To the user that's an off -> on, so the covers resume as they did
    before this check existed.
    """
    switch, coordinator = _switch(control_on=True)
    switch._attr_is_on = False  # stale: the hub turned control on underneath it
    await switch.async_turn_on()
    coordinator.async_set_adaptive_position.assert_awaited_once_with(COVER, 40)


@pytest.mark.asyncio
async def test_restoring_state_on_startup_never_moves_the_covers():
    """async_added_to_hass restores with added=True; that path stays a no-op."""
    switch, coordinator = _switch(control_on=False)
    await switch.async_turn_on(added=True)
    coordinator.async_set_adaptive_position.assert_not_awaited()
