"""Fetch sun data."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
from homeassistant.core import HomeAssistant
from homeassistant.helpers.sun import get_astral_location


class SunData:
    """Access local sun data."""

    def __init__(self, timezone: str, hass: HomeAssistant) -> None:
        """Initialise location, elevation and timezone from HA config."""
        self.hass = hass
        self.location, self.elevation = get_astral_location(self.hass)
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
    def solar_azimuth(self) -> list[float]:
        """Return solar azimuth for each 5-minute slot today."""
        # OPTIM: list comprehension — eliminates manual index for-loop
        return [
            self.location.solar_azimuth(t, self.elevation)
            for t in self.times
        ]

    @property
    def solar_elevation(self) -> list[float]:
        """Return solar elevation for each 5-minute slot today."""
        # OPTIM: list comprehension — eliminates manual index for-loop
        return [
            self.location.solar_elevation(t, self.elevation)
            for t in self.times
        ]

    def sunset(self) -> datetime:
        """Return today's sunset time (UTC)."""
        return self.location.sunset(date.today(), local=False)

    def sunrise(self) -> datetime:
        """Return today's sunrise time (UTC)."""
        return self.location.sunrise(date.today(), local=False)
