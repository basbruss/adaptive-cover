"""Tests for the seasonal default position (#497)."""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from custom_components.adaptive_cover.calculation import (
    AdaptiveGeneralCover,
    AdaptiveTiltCover,
    AdaptiveVerticalCover,
    ClimateCoverState,
)
from custom_components.adaptive_cover.const import (
    CONF_DEFAULT_HEIGHT_SUMMER,
    CONF_DEFAULT_HEIGHT_WINTER,
)
from custom_components.adaptive_cover.coordinator import (
    AdaptiveDataUpdateCoordinator,
)

COMMON = {
    "sol_azi": 0.0,  # sun due north, window faces south: out of view
    "sol_elev": 20.0,
    "sunset_pos": 0,
    "sunset_off": 0,
    "sunrise_off": 0,
    "timezone": "UTC",
    "fov_left": 45,
    "fov_right": 45,
    "win_azi": 180,
    "h_def": 60,
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
    with patch("custom_components.adaptive_cover.calculation.SunData"):
        yield


def _cover(sunset=False, **kwargs) -> AdaptiveVerticalCover:
    cover = AdaptiveVerticalCover(
        MagicMock(), MagicMock(), distance=0.5, h_win=2.0, **{**COMMON, **kwargs}
    )
    patcher = patch.object(
        AdaptiveGeneralCover, "sunset_valid", new_callable=PropertyMock
    )
    mock = patcher.start()
    mock.return_value = sunset
    return cover


@pytest.fixture(autouse=True)
def _stop_patches():
    yield
    patch.stopall()


def _climate(is_winter: bool, is_summer: bool) -> MagicMock:
    data = MagicMock()
    data.is_presence = True
    data.is_winter = is_winter
    data.is_summer = is_summer
    data.blind_type = "cover_blind"
    return data


@pytest.mark.parametrize(
    ("is_winter", "is_summer", "expected"),
    [
        (True, False, 100),  # winter: let ambient light in
        (False, True, 10),  # summer: keep heat out
        (False, False, 60),  # intermediate: plain default
        (True, True, 10),  # summer wins when both are true
    ],
)
def test_climate_state_switches_between_seasons(is_winter, is_summer, expected):
    """With the sun out of view the default follows the active season."""
    cover = _cover(h_def_winter=100, h_def_summer=10)
    assert not cover.valid

    state = ClimateCoverState(cover, _climate(is_winter, is_summer))

    assert state.get_state() == expected


def test_switching_season_on_the_same_cover():
    """Winter -> summer -> winter on one cover object picks the matching value."""
    cover = _cover(h_def_winter=90, h_def_summer=5)
    results = [
        ClimateCoverState(cover, _climate(w, s)).get_state()
        for w, s in [(True, False), (False, True), (True, False)]
    ]
    assert results == [90, 5, 90]


def test_unconfigured_season_falls_back_to_default():
    """None means "not configured", not zero."""
    cover = _cover(h_def_winter=None, h_def_summer=None)
    assert ClimateCoverState(cover, _climate(True, False)).get_state() == 60
    assert ClimateCoverState(cover, _climate(False, True)).get_state() == 60


def test_zero_is_a_valid_seasonal_value():
    """An explicit 0 is honored rather than treated as unset."""
    cover = _cover(h_def_summer=0)
    assert ClimateCoverState(cover, _climate(False, True)).get_state() == 0


def test_sunset_position_always_wins():
    """After sunset the sunset position overrides any seasonal default."""
    cover = _cover(sunset=True, sunset_pos=0, h_def_winter=100)
    assert cover.default_for_season(is_winter=True) == 0


def test_plain_default_property_unchanged():
    """`default` without season info behaves as before."""
    assert _cover(h_def_winter=100, h_def_summer=10).default == 60


def test_seasonal_fields_are_optional_keywords():
    """Covers can be built without seasonal values; positional order is unaffected."""
    cover = AdaptiveTiltCover(
        MagicMock(),
        MagicMock(),
        *COMMON.values(),
        5.0,
        3.0,
        "mode1",
    )
    assert cover.h_def_winter is None
    assert cover.h_def_summer is None
    assert cover.slat_distance == 5.0
    assert cover.mode == "mode1"


def test_coordinator_passes_seasonal_defaults_by_keyword():
    """The coordinator maps options onto the keyword-only fields."""
    options = {CONF_DEFAULT_HEIGHT_WINTER: 80, CONF_DEFAULT_HEIGHT_SUMMER: 15}
    assert AdaptiveDataUpdateCoordinator.seasonal_defaults(options) == {
        "h_def_winter": 80,
        "h_def_summer": 15,
    }
    assert AdaptiveDataUpdateCoordinator.seasonal_defaults({}) == {
        "h_def_winter": None,
        "h_def_summer": None,
    }
