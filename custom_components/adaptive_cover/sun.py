"""Fetch sun data."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pandas as pd
from astral import Observer
from astral import sun as astral_sun
from homeassistant.core import HomeAssistant


class SunData:
    """Access local sun data."""

    def __init__(self, timezone: str, hass: HomeAssistant) -> None:
        """Initialise observer, elevation and timezone from HA config.

        Builds the astral ``Observer`` directly from the HA config instead of
        calling ``homeassistant.helpers.sun.get_astral_location`` (deprecated in
        HA 2026.7, removed in 2027.7). ``get_astral_observer`` would do the same,
        but only exists since 2026.7 and this integration supports 2026.5+.
        """
        self.hass = hass
        latitude = hass.config.latitude
        longitude = hass.config.longitude
        self.elevation = hass.config.elevation
        self.observer = Observer(latitude, longitude, self.elevation)
        # Sunrise/sunset were computed at sea level (astral's
        # Location.sunrise/sunset default observer_elevation=0); keep that.
        self._horizon_observer = Observer(latitude, longitude, 0)
        self.timezone = timezone

    @property
    def times(self) -> pd.DatetimeIndex:
        """Define 5-minute time interval for today."""
        start_date = date.today()
        return pd.date_range(
            start=start_date,
            end=start_date + timedelta(days=1),
            freq="5min",
            tz=self.timezone,
            name="time",
        )

    @property
    def _utc_times(self) -> list[datetime]:
        """Today's slots in UTC.

        astral.sun gives wrong results for local times whose UTC date differs
        (e.g. 19:00 in New York); astral's Location converted to UTC first, so
        do the same.
        """
        return [t.astimezone(UTC) for t in self.times]

    @property
    def solar_azimuth(self) -> list[float]:
        """Return solar azimuth for each 5-minute slot today."""
        return [astral_sun.azimuth(self.observer, t) for t in self._utc_times]

    @property
    def solar_elevation(self) -> list[float]:
        """Return solar elevation for each 5-minute slot today."""
        return [astral_sun.elevation(self.observer, t) for t in self._utc_times]

    def sunset(self) -> datetime:
        """Return today's sunset time (UTC)."""
        return astral_sun.sunset(self._horizon_observer, date.today())

    def sunrise(self) -> datetime:
        """Return today's sunrise time (UTC)."""
        return astral_sun.sunrise(self._horizon_observer, date.today())
