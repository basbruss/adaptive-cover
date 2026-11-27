"""Explicit aggregate commands must create expiring manual overrides."""

from __future__ import annotations

import asyncio
import datetime as dt
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.adaptive_cover.coordinator import (
    AdaptiveCoverManager,
    AdaptiveDataUpdateCoordinator,
)
from custom_components.adaptive_cover.cover import AdaptiveCoverAll


def test_all_blinds_command_expires_after_configured_duration():
    manager = AdaptiveCoverManager({"minutes": 90}, MagicMock())
    coordinator = SimpleNamespace(
        entities=["cover.blind"],
        manager=manager,
        manual_reset=False,
        async_set_manual_position=AsyncMock(),
    )

    async def set_position(entity, position):
        await AdaptiveDataUpdateCoordinator.async_set_position(coordinator, entity, position)

    coordinator.async_set_position = set_position
    hub = SimpleNamespace(hass=MagicMock(), async_write_ha_state=MagicMock())
    with patch("custom_components.adaptive_cover.cover._iter_coordinators", return_value=[coordinator]):
        asyncio.run(AdaptiveCoverAll._move_all(hub, 100))

    assert manager.is_cover_manual("cover.blind")
    assert "cover.blind" in manager.manual_control_time
    coordinator.async_set_manual_position.assert_awaited_once_with("cover.blind", 100)

    manager.manual_control_time["cover.blind"] = (
        dt.datetime.now(dt.UTC) - dt.timedelta(minutes=91)
    )
    asyncio.run(manager.reset_if_needed())

    assert not manager.is_cover_manual("cover.blind")
    assert "cover.blind" not in manager.manual_control_time


def test_explicit_command_respects_reset_timer_option():
    manager = AdaptiveCoverManager({"minutes": 90}, MagicMock())
    old_start = dt.datetime.now(dt.UTC) - dt.timedelta(minutes=20)
    manager.manual_control_time["cover.blind"] = old_start

    manager.start_manual_control("cover.blind", allow_reset=False)
    assert manager.manual_control_time["cover.blind"] == old_start

    manager.start_manual_control("cover.blind", allow_reset=True)
    assert manager.manual_control_time["cover.blind"] > old_start
