"""Tests for awning (horizontal cover) behaviour with FOV beyond 90°."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.adaptive_cover.calculation import (
    AdaptiveHorizontalCover,
    AdaptiveTiltCover,
    AdaptiveVerticalCover,
)

WIN_AZI = 180


def _common(gamma: float, fov: int, elev: float = 20) -> dict:
    """Return constructor kwargs placing the sun at surface azimuth ``gamma``."""
    return {
        "hass": MagicMock(),
        "logger": MagicMock(),
        # gamma = win_azi - sol_azi
        "sol_azi": WIN_AZI - gamma,
        "sol_elev": elev,
        "sunset_pos": 0,
        "sunset_off": 0,
        "sunrise_off": 0,
        "timezone": "UTC",
        "fov_left": fov,
        "fov_right": fov,
        "win_azi": WIN_AZI,
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


def _awning(
    gamma: float, fov: int = 120, elev: float = 45
) -> AdaptiveHorizontalCover:
    return AdaptiveHorizontalCover(
        **_common(gamma, fov, elev),
        distance=0.5,
        h_win=2.1,
        awn_length=2.1,
        awn_angle=0,
    )


def _vertical(gamma: float, fov: int = 90) -> AdaptiveVerticalCover:
    return AdaptiveVerticalCover(**_common(gamma, fov), distance=0.5, h_win=2.1)


def _tilt(gamma: float, fov: int = 90) -> AdaptiveTiltCover:
    return AdaptiveTiltCover(
        **_common(gamma, fov), slat_distance=2, depth=3, mode="mode2"
    )


@pytest.mark.parametrize("sign", [1, -1])
@pytest.mark.parametrize(
    ("gamma", "valid", "percentage"),
    [(85, True, 50), (90, True, 100), (105, True, 100)],
)
def test_awning_terrace_mode(sign, gamma, valid, percentage):
    """With FOV > 90° the awning is valid past 90° and shades the terrace."""
    cover = _awning(sign * gamma)
    assert cover.valid is valid
    assert cover.calculate_percentage() == percentage


@pytest.mark.parametrize(
    ("gamma", "percentage"), [(85, 100), (89, 100), (90, 100), (90.1, 100)]
)
def test_awning_review_case_no_jump(gamma, percentage):
    """Review case d=0.5, ε=20°: was 85°→2 %, 89°→0 %, 90.1°→100 %."""
    assert _awning(gamma, elev=20).calculate_percentage() == percentage


def test_awning_outside_extended_fov_is_invalid():
    """Sun beyond the extended FOV is still rejected."""
    assert _awning(125).valid is False


def test_awning_transition_is_continuous_and_monotonic():
    """No sign-flip jump around 90°: extension rises smoothly to 100 %."""
    gammas = [60 + i * 0.1 for i in range(0, 401)]  # 60° .. 100°
    values = [_awning(g).calculate_position() for g in gammas]
    steps = [b - a for a, b in zip(values, values[1:])]
    # Continuous everywhere: old model jumped ~2 m between 90° and 90.1°.
    assert max(abs(step) for step in steps) < 0.05
    # Monotonic inside the transition band (80°..100°): no retract/re-extend.
    assert all(step >= -1e-9 for step in steps[200:])
    assert values[-1] == pytest.approx(2.1)


def test_awning_below_band_matches_window_model():
    """Outside the transition band the window-zone model is unchanged."""
    with_terrace = _awning(60, fov=120).calculate_position()
    without = _awning(60, fov=90).calculate_position()
    assert 0 < with_terrace < 2.1
    assert with_terrace == pytest.approx(without)


def test_awning_without_terrace_mode_keeps_90_cap():
    """FOV ≤ 90° keeps the window-only behaviour (no terrace extension)."""
    assert _awning(85, fov=90, elev=20).valid is True
    assert _awning(85, fov=90, elev=20).calculate_percentage() == 2
    assert _awning(89, fov=90, elev=20).calculate_percentage() == 0
    assert _awning(90, fov=90).valid is False
    assert _awning(105, fov=90).valid is False
    assert _awning(105, fov=90).calculate_position() == 0.0


@pytest.mark.parametrize("gamma", [0, 30, 60, 85])
def test_vertical_unchanged(gamma):
    """Vertical covers keep the 90° cap and the original formula."""
    from numpy import cos, radians, tan

    cover = _vertical(gamma, fov=120)
    expected = min(max(0.5 / cos(radians(gamma)) * tan(radians(20)), 0), 2.1)
    assert cover.calculate_position() == pytest.approx(expected)
    assert cover.valid is True


@pytest.mark.parametrize("gamma", [90, 105])
def test_vertical_and_tilt_still_capped_at_90(gamma):
    """Vertical and tilt covers never accept sun behind the window plane."""
    assert _vertical(gamma, fov=120).valid is False
    assert _tilt(gamma, fov=120).valid is False


def test_tilt_unchanged():
    """Tilt covers are not affected by the awning change."""
    assert _tilt(30).valid is True
    # Value computed with the unmodified main-branch implementation.
    assert _tilt(30).calculate_percentage() == 42
