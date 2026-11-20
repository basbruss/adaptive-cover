"""Tests for SunData after moving off the deprecated get_astral_location.

The values must stay identical to the previous implementation, which used
``astral.location.Location`` built from the HA config: azimuth/elevation with
the HA elevation, sunrise/sunset at sea level (Location's default).
"""

from datetime import date
from types import SimpleNamespace

import pytest
from astral import LocationInfo
from astral.location import Location

from custom_components.adaptive_cover.sun import SunData

LOCATIONS = [
    # latitude, longitude, elevation, timezone
    (52.52, 13.40, 34, "Europe/Berlin"),
    (47.42, 10.98, 2962, "Europe/Berlin"),
    (-33.87, 151.21, 58, "Australia/Sydney"),
    (40.71, -74.01, 10, "America/New_York"),
]


def _hass(lat, lon, elev):
    return SimpleNamespace(
        config=SimpleNamespace(latitude=lat, longitude=lon, elevation=elev)
    )


def _old_location(lat, lon, tz):
    return Location(LocationInfo("", "", tz, lat, lon))


@pytest.mark.parametrize(("lat", "lon", "elev", "tz"), LOCATIONS)
def test_azimuth_and_elevation_match_previous_implementation(lat, lon, elev, tz):
    """Azimuth and elevation equal the old Location-based values."""
    sun = SunData(tz, _hass(lat, lon, elev))
    old = _old_location(lat, lon, tz)
    times = list(sun.times)

    assert sun.solar_azimuth == [old.solar_azimuth(t, elev) for t in times]
    assert sun.solar_elevation == [old.solar_elevation(t, elev) for t in times]


@pytest.mark.parametrize(("lat", "lon", "elev", "tz"), LOCATIONS)
def test_sunrise_and_sunset_match_previous_implementation(lat, lon, elev, tz):
    """Sunrise and sunset equal the old Location-based values (sea level)."""
    sun = SunData(tz, _hass(lat, lon, elev))
    old = _old_location(lat, lon, tz)

    assert sun.sunrise() == old.sunrise(date.today(), local=False)
    assert sun.sunset() == old.sunset(date.today(), local=False)


def test_elevation_attribute_kept():
    """The HA elevation stays available as SunData.elevation."""
    sun = SunData("Europe/Berlin", _hass(52.52, 13.40, 34))
    assert sun.elevation == 34
