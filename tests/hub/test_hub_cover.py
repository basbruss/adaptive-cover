"""Integration tests for the hub cover entity (AdaptiveCoverAll).

These tests exercise the aggregate cover without spinning up a full HA
instance — coordinators are replaced by lightweight mocks.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_coord(entities: list[str], position: int = 50) -> MagicMock:
    """Build a minimal coordinator mock."""
    coord = MagicMock()
    coord.entities = entities
    coord.control_toggle = True
    coord.security_toggle = False
    coord.async_refresh = AsyncMock()
    coord.async_set_position = AsyncMock()
    coord.async_set_manual_position = AsyncMock()
    manager = MagicMock()
    manager.binary_cover_manual = False
    manager.reset = MagicMock()
    manager.mark_manual_control = MagicMock()
    coord.manager = manager
    return coord


def _make_hass(coordinators: list, cover_positions: dict[str, int]) -> MagicMock:
    """Build a minimal hass mock that serves coordinator and state data."""
    hass = MagicMock()

    # Wire up hass.data[DOMAIN] so _iter_coordinators works
    from custom_components.adaptive_cover.const import DOMAIN
    hass.data = {DOMAIN: {str(i): c for i, c in enumerate(coordinators)}}

    def _get_state(entity_id):
        pos = cover_positions.get(entity_id)
        if pos is None:
            return None
        state = MagicMock()
        state.attributes = {"current_position": pos}
        return state

    hass.states = MagicMock()
    hass.states.get = _get_state
    return hass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAdaptiveCoverAllPosition:
    """current_cover_position and is_closed behaviour."""

    def _cover(self, hass, config_entry):
        from custom_components.adaptive_cover.cover import AdaptiveCoverAll
        c = AdaptiveCoverAll(hass, config_entry)
        return c

    def _entry(self):
        entry = MagicMock()
        entry.entry_id = "hub_entry"
        return entry

    def test_average_position(self):
        coords = [
            _make_coord(["cover.a", "cover.b"]),
            _make_coord(["cover.c"]),
        ]
        hass = _make_hass(coords, {"cover.a": 100, "cover.b": 0, "cover.c": 50})
        cover = self._cover(hass, self._entry())
        # (100 + 0 + 50) / 3 = 50
        assert cover.current_cover_position == 50

    def test_is_closed_all_zero(self):
        coords = [_make_coord(["cover.a", "cover.b"])]
        hass = _make_hass(coords, {"cover.a": 0, "cover.b": 0})
        cover = self._cover(hass, self._entry())
        assert cover.is_closed is True

    def test_is_closed_not_all_zero(self):
        coords = [_make_coord(["cover.a", "cover.b"])]
        hass = _make_hass(coords, {"cover.a": 0, "cover.b": 50})
        cover = self._cover(hass, self._entry())
        assert cover.is_closed is False

    def test_no_covers_returns_none(self):
        hass = _make_hass([], {})
        cover = self._cover(hass, self._entry())
        assert cover.current_cover_position is None
        assert cover.is_closed is None


class TestAdaptiveCoverAllAttributes:
    """extra_state_attributes reflect coordinator state."""

    def _cover(self, hass, config_entry):
        from custom_components.adaptive_cover.cover import AdaptiveCoverAll
        return AdaptiveCoverAll(hass, config_entry)

    def _entry(self):
        entry = MagicMock()
        entry.entry_id = "hub_entry"
        return entry

    def test_adaptive_control_true_when_all_on(self):
        coords = [_make_coord(["cover.a"])]
        coords[0].control_toggle = True
        hass = _make_hass(coords, {"cover.a": 50})
        cover = self._cover(hass, self._entry())
        attrs = cover.extra_state_attributes
        assert attrs["adaptive_control"] is True

    def test_adaptive_control_false_when_any_off(self):
        c1 = _make_coord(["cover.a"])
        c1.control_toggle = True
        c2 = _make_coord(["cover.b"])
        c2.control_toggle = False
        hass = _make_hass([c1, c2], {"cover.a": 50, "cover.b": 50})
        cover = self._cover(hass, self._entry())
        attrs = cover.extra_state_attributes
        assert attrs["adaptive_control"] is False

    def test_empty_domain_data(self):
        from custom_components.adaptive_cover.const import DOMAIN
        hass = MagicMock()
        hass.data = {DOMAIN: {}}
        cover = self._cover(hass, self._entry())
        attrs = cover.extra_state_attributes
        assert attrs["config_entries"] == 0
        assert attrs["covers"] == []
