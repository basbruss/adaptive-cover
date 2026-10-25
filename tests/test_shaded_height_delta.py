"""Tests for the shaded-area height adjustment on vertical blinds."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from numpy import radians, tan

from custom_components.adaptive_cover.calculation import (
    AdaptiveHorizontalCover,
    AdaptiveVerticalCover,
)
from custom_components.adaptive_cover.config_flow import (
    HORIZONTAL_OPTIONS,
    VERTICAL_OPTIONS,
)
from custom_components.adaptive_cover.const import CONF_SHADED_HEIGHT_DELTA
from custom_components.adaptive_cover.coordinator import (
    AdaptiveDataUpdateCoordinator,
)

COMMON = {
    "sol_azi": 180,
    "sol_elev": 30,
    "sunset_pos": 0,
    "sunset_off": 0,
    "sunrise_off": 0,
    "timezone": "UTC",
    "fov_left": 90,
    "fov_right": 90,
    "win_azi": 180,
    "h_def": 0,
    "max_pos": 100,
    "min_pos": 0,
    "max_pos_bool": False,
    "min_pos_bool": False,
    "blind_spot_left": None,
    "blind_spot_right": None,
    "blind_spot_elevation": None,
    "blind_spot_on": False,
    "min_elevation": None,
    "max_elevation": None,
}


@pytest.fixture(autouse=True)
def _no_sun_data():
    """Avoid touching HA's astral location."""
    with patch("custom_components.adaptive_cover.calculation.SunData"):
        yield


def _vertical(**kwargs) -> AdaptiveVerticalCover:
    return AdaptiveVerticalCover(
        MagicMock(), MagicMock(), **COMMON, distance=1.0, h_win=2.0, **kwargs
    )


def test_default_is_unchanged():
    """Without the option the original formula is used."""
    expected = 1.0 * tan(radians(30))
    assert _vertical().calculate_position() == pytest.approx(expected)


@pytest.mark.parametrize("delta", [0.5, -0.3])
def test_delta_is_added_to_shaded_height(delta):
    """The delta shifts the blind height by the same amount (#412 sign)."""
    base = _vertical().calculate_position()
    assert _vertical(shaded_height_delta=delta).calculate_position() == (
        pytest.approx(base + delta)
    )


def test_delta_is_clipped_to_window():
    """The result stays within 0..h_win."""
    assert _vertical(shaded_height_delta=5).calculate_position() == 2.0
    assert _vertical(shaded_height_delta=-5).calculate_position() == 0.0


def test_option_only_offered_for_vertical_blinds():
    """Awnings must not get the field (HORIZONTAL_OPTIONS builds on vertical)."""
    assert CONF_SHADED_HEIGHT_DELTA in VERTICAL_OPTIONS.schema
    assert CONF_SHADED_HEIGHT_DELTA not in HORIZONTAL_OPTIONS.schema
    assert VERTICAL_OPTIONS({})[CONF_SHADED_HEIGHT_DELTA] == 0.0


def _coordinator(cover_type: str):
    coordinator = object.__new__(AdaptiveDataUpdateCoordinator)
    coordinator.hass = MagicMock()
    coordinator.hass.states.get.return_value.attributes = {
        "azimuth": 180,
        "elevation": 30,
    }
    coordinator.logger = MagicMock()
    coordinator._cover_type = cover_type
    coordinator.common_data = lambda options: [COMMON[k] for k in list(COMMON)[2:]]
    return coordinator


def test_existing_entries_without_option_still_work():
    """Old config entries lack the key; the coordinator defaults it to 0."""
    options = {"distance_shaded_area": 1.0, "window_height": 2.0}
    cover = _coordinator("cover_blind").get_blind_data(options)
    assert isinstance(cover, AdaptiveVerticalCover)
    assert cover.shaded_height_delta == 0.0

    options[CONF_SHADED_HEIGHT_DELTA] = 0.4
    cover = _coordinator("cover_blind").get_blind_data(options)
    assert cover.shaded_height_delta == 0.4


def test_awning_ignores_option():
    """Awnings are built without the delta even if the key is present."""
    options = {
        "distance_shaded_area": 1.0,
        "window_height": 2.0,
        "length_awning": 2.1,
        "angle": 0,
        CONF_SHADED_HEIGHT_DELTA: 0.4,
    }
    cover = _coordinator("cover_awning").get_blind_data(options)
    assert isinstance(cover, AdaptiveHorizontalCover)
    assert cover.shaded_height_delta == 0.0
