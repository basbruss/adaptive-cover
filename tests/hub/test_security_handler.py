"""Unit tests for the SecurityHandler pipeline handler."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.adaptive_cover.pipeline.handlers.security import (
    PRIORITY,
    SecurityHandler,
)
from custom_components.adaptive_cover.pipeline.types import PipelineSnapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _snapshot(**kwargs) -> PipelineSnapshot:
    """Build a minimal PipelineSnapshot for testing."""
    defaults = dict(
        hass=MagicMock(),
        coordinator=MagicMock(),
        calculated_position=50,
        security_toggle=False,
        security_active=False,
        climate_mode=False,
        control_method="intermediate",
        min_position=None,
    )
    defaults.update(kwargs)
    return PipelineSnapshot(**defaults)


# ---------------------------------------------------------------------------
# Priority
# ---------------------------------------------------------------------------


def test_handler_priority():
    """SecurityHandler must be registered at priority 95."""
    handler = SecurityHandler()
    assert handler.priority == 95
    assert PRIORITY == 95


# ---------------------------------------------------------------------------
# No-op paths
# ---------------------------------------------------------------------------


def test_no_op_when_security_toggle_off():
    """When security_toggle is False the handler must not modify the snapshot."""
    handler = SecurityHandler()
    snap = _snapshot(security_toggle=False, security_active=True)
    result = handler.handle(snap)
    assert result.override_position is None
    assert result.handler_log == []


def test_no_op_when_presence_detected():
    """When security_active is False (someone home) the handler must not override."""
    handler = SecurityHandler()
    snap = _snapshot(security_toggle=True, security_active=False)
    result = handler.handle(snap)
    assert result.override_position is None
    assert result.handler_log == []


# ---------------------------------------------------------------------------
# Override paths
# ---------------------------------------------------------------------------


def test_full_close_no_climate():
    """Security active, no climate → position must be 0."""
    handler = SecurityHandler()
    snap = _snapshot(
        security_toggle=True,
        security_active=True,
        climate_mode=False,
        control_method="intermediate",
        calculated_position=75,
    )
    result = handler.handle(snap)
    assert result.override_position == 0
    assert result.effective_position == 0
    assert len(result.handler_log) == 1


def test_full_close_climate_summer():
    """Security active, climate summer branch → position must be 0."""
    handler = SecurityHandler()
    snap = _snapshot(
        security_toggle=True,
        security_active=True,
        climate_mode=True,
        control_method="summer",
        min_position=10,
    )
    result = handler.handle(snap)
    assert result.override_position == 0


def test_min_position_climate_winter():
    """Security active, climate winter branch → position must be min_position."""
    handler = SecurityHandler()
    snap = _snapshot(
        security_toggle=True,
        security_active=True,
        climate_mode=True,
        control_method="winter",
        min_position=15,
    )
    result = handler.handle(snap)
    assert result.override_position == 15


def test_min_position_climate_intermediate():
    """Security active, climate intermediate branch → position must be min_position."""
    handler = SecurityHandler()
    snap = _snapshot(
        security_toggle=True,
        security_active=True,
        climate_mode=True,
        control_method="intermediate",
        min_position=5,
    )
    result = handler.handle(snap)
    assert result.override_position == 5


def test_min_position_falls_back_to_zero_when_none():
    """min_position=None in climate winter → falls back to 0."""
    handler = SecurityHandler()
    snap = _snapshot(
        security_toggle=True,
        security_active=True,
        climate_mode=True,
        control_method="winter",
        min_position=None,
    )
    result = handler.handle(snap)
    assert result.override_position == 0


# ---------------------------------------------------------------------------
# PipelineSnapshot.effective_position
# ---------------------------------------------------------------------------


def test_effective_position_uses_calculated_when_no_override():
    """effective_position returns calculated_position when override_position is None."""
    snap = _snapshot(calculated_position=42)
    assert snap.effective_position == 42


def test_effective_position_uses_override_when_set():
    """effective_position returns override_position when it is set."""
    snap = _snapshot(calculated_position=42)
    snap.override_position = 0
    assert snap.effective_position == 0


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_handler_is_idempotent():
    """Calling handle twice must not double-append to handler_log."""
    handler = SecurityHandler()
    snap = _snapshot(security_toggle=True, security_active=True)
    handler.handle(snap)
    first_log = list(snap.handler_log)
    handler.handle(snap)
    # Log grows by 1 on each call — that is expected — but override stays same
    assert snap.override_position == 0
    assert len(snap.handler_log) == len(first_log) + 1
