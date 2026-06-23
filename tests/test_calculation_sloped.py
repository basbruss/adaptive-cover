"""Unit tests for the sloped (roof / Velux) cover calculation.

These exercise the pure geometry of ``AdaptiveSlopedCover.calculate_position``
without a running Home Assistant: the math depends only on ``distance``,
``h_win``, ``sol_elev`` and ``gamma`` (derived from ``win_azi`` / ``sol_azi``),
none of which need ``sun_data``. Instances are therefore built bypassing the
dataclass ``__init__`` (which would call ``get_astral_location``).
"""

import logging
import math

import pytest

from custom_components.adaptive_cover.calculation import (
    AdaptiveSlopedCover,
    AdaptiveVerticalCover,
)


def _make(cls, *, sol_elev, win_azi, sol_azi, distance, h_win, surface_tilt=None):
    """Build a cover instance with only the fields the geometry needs."""
    obj = cls.__new__(cls)
    # calculate_percentage() emits debug logs; a plain logger satisfies the
    # ConfigContextAdapter slot without a running Home Assistant.
    obj.logger = logging.getLogger("adaptive_cover.test")
    obj.sol_elev = sol_elev
    obj.sol_azi = sol_azi
    obj.win_azi = win_azi
    obj.distance = distance
    obj.h_win = h_win
    if surface_tilt is not None:
        obj.surface_tilt = surface_tilt
    return obj


@pytest.mark.parametrize("sol_elev", [10, 30, 45, 60, 80])
@pytest.mark.parametrize("rel_azi", [0, 30, -45, 60])
def test_vertical_equivalence_at_90_degrees(sol_elev, rel_azi):
    """At surface_tilt = 90° the sloped model must match the vertical model."""
    win_azi = 180
    sol_azi = win_azi - rel_azi
    common = dict(
        sol_elev=sol_elev, win_azi=win_azi, sol_azi=sol_azi, distance=0.5, h_win=2.1
    )
    vertical = _make(AdaptiveVerticalCover, **common)
    sloped = _make(AdaptiveSlopedCover, surface_tilt=90, **common)

    assert sloped.calculate_position() == pytest.approx(
        vertical.calculate_position(), rel=1e-9
    )
    assert sloped.calculate_percentage() == vertical.calculate_percentage()


@pytest.mark.parametrize("sol_elev", [15, 35, 70])
def test_flat_skylight_maps_to_distance(sol_elev):
    """At surface_tilt = 0° the shaded depth maps directly onto glazing distance."""
    sloped = _make(
        AdaptiveSlopedCover,
        sol_elev=sol_elev,
        win_azi=180,
        sol_azi=180,
        distance=0.5,
        h_win=2.1,
        surface_tilt=0,
    )
    assert sloped.calculate_position() == pytest.approx(0.5, rel=1e-9)


def test_position_clipped_to_glazing_length():
    """Position never exceeds the glazing length (h_win)."""
    sloped = _make(
        AdaptiveSlopedCover,
        sol_elev=85,
        win_azi=180,
        sol_azi=180,
        distance=2.0,
        h_win=1.0,
        surface_tilt=90,
    )
    assert sloped.calculate_position() == pytest.approx(1.0)


def test_sun_behind_plane_covers_fully():
    """When the beam grazes / sits behind the plane, cover fully (h_win)."""
    # Low sun coming from well to the side of a steeply sloped window so the
    # denominator turns non-positive.
    sloped = _make(
        AdaptiveSlopedCover,
        sol_elev=2,
        win_azi=180,
        sol_azi=10,  # gamma ≈ 170° → cos(gamma) < 0
        distance=0.5,
        h_win=2.1,
        surface_tilt=20,
    )
    denom = math.cos(math.radians(20)) * math.tan(math.radians(2)) + math.sin(
        math.radians(20)
    ) * math.cos(math.radians((180 - 10 + 180) % 360 - 180))
    assert denom <= 0  # guard precondition for this test
    assert sloped.calculate_position() == 2.1
