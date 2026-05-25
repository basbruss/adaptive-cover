"""Generate values for all types of covers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from homeassistant.core import HomeAssistant
from numpy import cos, sin, tan
from numpy import radians as rad

from .helpers import get_domain, get_safe_state, state_attr
from .sun import SunData
from .config_context_adapter import ConfigContextAdapter


@dataclass
class AdaptiveGeneralCover(ABC):
    """Collect common data."""

    hass: HomeAssistant
    logger: ConfigContextAdapter
    sol_azi: float
    sol_elev: float
    sunset_pos: int
    sunset_off: int
    sunrise_off: int
    timezone: str
    fov_left: int
    fov_right: int
    win_azi: int
    h_def: int
    max_pos: int
    min_pos: int
    max_pos_bool: bool
    min_pos_bool: bool
    blind_spot_left: int
    blind_spot_right: int
    blind_spot_elevation: int
    blind_spot_on: bool
    min_elevation: int
    max_elevation: int
    sun_data: SunData = field(init=False)

    def __post_init__(self):
        """Add solar data to dataset."""
        self.sun_data = SunData(self.timezone, self.hass)

    def solar_times(self):
        """Determine start/end times."""
        df_today = pd.DataFrame(
            {
                "azimuth": self.sun_data.solar_azimuth,
                "elevation": self.sun_data.solar_elevation,
            }
        )
        solpos = df_today.set_index(self.sun_data.times)

        alpha = solpos["azimuth"]
        frame = (
            (alpha - self.azi_min_abs) % 360
            <= (self.azi_max_abs - self.azi_min_abs) % 360
        ) & (solpos["elevation"] > 0)

        if solpos[frame].empty:
            return None, None
        return (
            solpos[frame].index[0].to_pydatetime(),
            solpos[frame].index[-1].to_pydatetime(),
        )

    @property
    def _get_azimuth_edges(self) -> tuple[int, int]:
        """Calculate azimuth edges."""
        return self.fov_left + self.fov_right

    @property
    def is_sun_in_blind_spot(self) -> bool:
        """Check if sun is in blind spot."""
        if (
            self.blind_spot_left is not None
            and self.blind_spot_right is not None
            and self.blind_spot_on
        ):
            left_edge = self.fov_left - self.blind_spot_left
            right_edge = self.fov_left - self.blind_spot_right
            blindspot = (self.gamma <= left_edge) & (self.gamma >= right_edge)
            if self.blind_spot_elevation is not None:
                blindspot = blindspot & (self.sol_elev <= self.blind_spot_elevation)
            self.logger.debug("Is sun in blind spot? %s", blindspot)
            return blindspot
        return False

    @property
    def azi_min_abs(self) -> int:
        """Calculate min azimuth."""
        azi_min_abs = (self.win_azi - self.fov_left + 360) % 360
        return azi_min_abs

    @property
    def azi_max_abs(self) -> int:
        """Calculate max azimuth."""
        azi_max_abs = (self.win_azi + self.fov_right + 360) % 360
        return azi_max_abs

    @property
    def gamma(self) -> float:
        """Calculate Gamma."""
        # surface solar azimuth
        gamma = (self.win_azi - self.sol_azi + 180) % 360 - 180
        return gamma

    @property
    def valid_elevation(self) -> bool:
        """Check if elevation is within range."""
        if self.min_elevation is None and self.max_elevation is None:
            return self.sol_elev >= 0
        if self.min_elevation is None:
            return self.sol_elev <= self.max_elevation
        if self.max_elevation is None:
            return self.sol_elev >= self.min_elevation
        within_range = self.min_elevation <= self.sol_elev <= self.max_elevation
        self.logger.debug("elevation within range? %s", within_range)
        return within_range

    @property
    def valid(self) -> bool:
        """Determine if sun is in front of window."""
        # clip azi_min and azi_max to 90
        azi_min = min(self.fov_left, 90)
        azi_max = min(self.fov_right, 90)

        # valid sun positions are those within the blind's azimuth range and above the horizon (FOV)
        valid = (
            (self.gamma < azi_min) & (self.gamma > -azi_max) & (self.valid_elevation)
        )
        self.logger.debug("Sun in front of window (ignoring blindspot)? %s", valid)
        return valid

    @property
    def sunset_valid(self) -> bool:
        """Determine if it is after sunset plus offset."""
        sunset = self.sun_data.sunset().replace(tzinfo=None)
        sunrise = self.sun_data.sunrise().replace(tzinfo=None)
        after_sunset = datetime.utcnow() > (sunset + timedelta(minutes=self.sunset_off))
        before_sunrise = datetime.utcnow() < (
            sunrise + timedelta(minutes=self.sunrise_off)
        )
        self.logger.debug(
            "After sunset plus offset? %s", (after_sunset or before_sunrise)
        )
        return after_sunset or before_sunrise

    @property
    def default(self) -> float:
        """Change default position at sunset."""
        default = self.h_def
        if self.sunset_valid:
            default = self.sunset_pos
        return default

    def fov(self) -> list:
        """Return field of view."""
        return [self.azi_min_abs, self.azi_max_abs]

    @property
    def apply_min_position(self) -> bool:
        """Check if min position is applied."""
        if self.min_pos is not None and self.min_pos != 0:  # noqa: C0121 — int comparison, not None/True/False
            if self.min_pos_bool:
                return self.direct_sun_valid
            return True
        return False

    @property
    def apply_max_position(self) -> bool:
        """Check if max position is applied."""
        if self.max_pos is not None and self.max_pos != 100:
            if self.max_pos_bool:
                return self.direct_sun_valid
            return True
        return False

    @property
    def direct_sun_valid(self) -> bool:
        """Check if sun is directly in front of window."""
        return (self.valid) & (not self.sunset_valid) & (not self.is_sun_in_blind_spot)

    @abstractmethod
    def calculate_position(self) -> float:
        """Calculate the position of the blind."""

    @abstractmethod
    def calculate_percentage(self) -> int:
        """Calculate percentage from position."""


@dataclass
class NormalCoverState:
    """Compute state for normal operation."""

    cover: AdaptiveGeneralCover

    def get_state(self) -> int:
        """Return state."""
        self.cover.logger.debug("Determining normal position")
        dsv = self.cover.direct_sun_valid
        self.cover.logger.debug(
            "Sun directly in front of window & before sunset + offset? %s", dsv
        )
        if dsv:
            state = self.cover.calculate_percentage()
            self.cover.logger.debug(
                "Yes sun in window: using calculated percentage (%s)", state
            )
        else:
            state = self.cover.default
            self.cover.logger.debug("No sun in window: using default value (%s)", state)

        result = np.clip(state, 0, 100)
        if self.cover.apply_max_position and result > self.cover.max_pos:
            return self.cover.max_pos
        if self.cover.apply_min_position and result < self.cover.min_pos:
            return self.cover.min_pos
        return result


@dataclass
class ClimateCoverData:  # pylint: disable=too-many-instance-attributes
    """Fetch additional data."""

    hass: HomeAssistant
    logger: ConfigContextAdapter
    temp_entity: str
    temp_low: float
    temp_high: float
    presence_entity: str
    weather_entity: str
    weather_condition: list[str]
    outside_entity: str
    temp_switch: bool
    blind_type: str
    transparent_blind: bool
    lux_entity: str
    irradiance_entity: str
    lux_threshold: int
    irradiance_threshold: int
    temp_summer_outside: float
    _use_lux: bool
    _use_irradiance: bool

    @property
    def outside_temperature(self):
        """Get outside temperature."""
        temp = None
        if self.outside_entity:
            temp = get_safe_state(
                self.hass,
                self.outside_entity,
            )
        elif self.weather_entity:
            temp = state_attr(self.hass, self.weather_entity, "temperature")
        return temp

    @property
    def inside_temperature(self):
        """Get inside temp from entity."""
        if self.temp_entity is not None:
            if get_domain(self.temp_entity) != "climate":
                temp = get_safe_state(
                    self.hass,
                    self.temp_entity,
                )
            else:
                temp = state_attr(self.hass, self.temp_entity, "current_temperature")
            return temp

    @property
    def get_current_temperature(self) -> float | None:
        """Return current temperature as float, or None if unavailable.

        Uses `is not None` rather than a truthy check to correctly handle
        a temperature of 0.0°C (which is falsy but perfectly valid).

        .. deprecated::
            Prefer `temperature_for_winter` / `temperature_for_summer` which
            apply the correct sensor source for each seasonal check.
        """
        if self.temp_switch:
            outside = self.outside_temperature
            if outside is not None:
                return float(outside)
        inside = self.inside_temperature
        if inside is not None:
            return float(inside)
        return None

    @property
    def temperature_for_winter(self) -> float | None:
        """Temperature used for the winter (heating) check.

        Always prefers the **inside** sensor: the room must actually be cold
        before we open the blind to capture solar heat.
        Falls back to outside temperature only when no inside sensor is set.
        """
        inside = self.inside_temperature
        if inside is not None:
            return float(inside)
        outside = self.outside_temperature
        if outside is not None:
            return float(outside)
        return None

    @property
    def temperature_for_summer(self) -> float | None:
        """Temperature used for the summer (cooling) check.

        When `temp_switch=True` uses the **outside** sensor: external heat is
        what we are guarding against, even if the room is still comfortable.
        Falls back to inside temperature when no outside sensor is available.
        """
        if self.temp_switch:
            outside = self.outside_temperature
            if outside is not None:
                return float(outside)
        inside = self.inside_temperature
        if inside is not None:
            return float(inside)
        return None

    @property
    def is_presence(self):
        """Checks if people are present."""
        presence = None
        if self.presence_entity is not None:
            presence = get_safe_state(self.hass, self.presence_entity)
        # set to true if no sensor is defined
        if presence is not None:
            domain = get_domain(self.presence_entity)
            if domain == "device_tracker":
                return presence == "home"
            if domain == "zone":
                return int(presence) > 0
            if domain in ["binary_sensor", "input_boolean"]:
                return presence == "on"
        return True

    @property
    def is_winter(self) -> bool:
        """Check if the room temperature is below the heating threshold.

        Uses `temperature_for_winter` (inside sensor preferred) so that a cold
        outdoor temperature cannot trigger a 100 % open when the room is
        already warm.
        """
        temp = self.temperature_for_winter
        if self.temp_low is not None and temp is not None:
            is_it = temp < self.temp_low
        else:
            is_it = False

        self.logger.debug(
            "is_winter(): inside_temp < temp_low: %s < %s = %s",
            temp,
            self.temp_low,
            is_it,
        )
        return is_it

    @property
    def outside_high(self) -> bool:
        """Check if outdoor temperature is above threshold."""
        if (
            self.temp_summer_outside is not None
            and self.outside_temperature is not None
        ):
            return float(self.outside_temperature) > self.temp_summer_outside
        return True

    @property
    def is_summer(self) -> bool:
        """Check if temperature exceeds the cooling threshold.

        Uses `temperature_for_summer` (outside sensor when temp_switch=True)
        so that incoming external heat is detected even before the room warms up.
        """
        temp = self.temperature_for_summer
        if self.temp_high is not None and temp is not None:
            is_it = temp > self.temp_high and self.outside_high
        else:
            is_it = False

        self.logger.debug(
            "is_summer(): temp > temp_high and outside_high?: %s > %s and %s = %s",
            temp,
            self.temp_high,
            self.outside_high,
            is_it,
        )
        return is_it

    @property
    def is_sunny(self) -> bool:
        """Check if condition can contain radiation in winter."""
        weather_state = None
        if self.weather_entity is not None:
            weather_state = get_safe_state(self.hass, self.weather_entity)
        else:
            self.logger.debug("is_sunny(): No weather entity defined")
            return True
        if self.weather_condition is not None:
            matches = weather_state in self.weather_condition
            self.logger.debug("is_sunny(): Weather: %s = %s", weather_state, matches)
            return matches

    @property
    def lux(self) -> bool:
        """Get lux value and compare to threshold."""
        if not self._use_lux:
            return False
        if self.lux_entity is not None and self.lux_threshold is not None:
            value = get_safe_state(self.hass, self.lux_entity)
            if value is None:
                return False
            return float(value) <= self.lux_threshold
        return False

    @property
    def irradiance(self) -> bool:
        """Get irradiance value and compare to threshold."""
        if not self._use_irradiance:
            return False
        if self.irradiance_entity is not None and self.irradiance_threshold is not None:
            value = get_safe_state(self.hass, self.irradiance_entity)
            if value is None:
                return False
            return float(value) <= self.irradiance_threshold
        return False


@dataclass
class ClimateCoverState(NormalCoverState):
    """Compute state for climate control operation."""

    climate_data: ClimateCoverData

    def normal_type_cover(self) -> int:
        """Determine state for horizontal and vertical covers."""

        self.cover.logger.debug("Is presence? %s", self.climate_data.is_presence)

        if self.climate_data.is_presence:
            return self.normal_with_presence()

        return self.normal_without_presence()

    def normal_with_presence(self) -> int:
        """Determine state for horizontal and vertical covers with occupants.

        Priority tree (presence=True):

        1. Sun NOT in window (cover.valid=False)
               → default position  (no action needed)

        2. Sun in window (cover.valid=True)
           a. WINTER  (T° < low threshold)
                  → 100% open  (capture solar heat regardless of lux/weather)
           b. SUMMER  (T° > high threshold)
                  transparent_blind=True  → basic calculated  (sheer: shade only)
                  transparent_blind=False → 0% closed         (opaque: preserve cool)
           c. INTERMEDIATE
                  overcast / low lux / low irradiance → default position
                  sunny                               → basic calculated (shade only)
        """

        is_summer = self.climate_data.is_summer

        # ── Step 1: sun not in window → default regardless of season ──────────
        if not self.cover.valid:
            self.cover.logger.debug(
                "n_w_p(): sun not in window → default"
            )
            return self.cover.default

        # ── Step 2a: WINTER + sun in window → open fully ──────────────────────
        # Winter check precedes lux/weather filter: even on a clear sunny day
        # in winter, the goal is to capture as much solar heat as possible.
        if not is_summer and self.climate_data.is_winter:
            self.cover.logger.debug(
                "n_w_p(): Winter and sun is in front of window = use 100"
            )
            return 100

        # ── Step 2b: SUMMER + sun in window ───────────────────────────────────
        if is_summer:
            if self.climate_data.transparent_blind:
                # Sheer / voile curtain: cannot fully block anyway → shade only
                self.cover.logger.debug(
                    "n_w_p(): Summer + transparent blind → basic (shade only)"
                )
                return super().get_state()
            # Opaque blind: close fully to preserve indoor cool
            self.cover.logger.debug(
                "n_w_p(): Summer + opaque blind → 0% (fully closed)"
            )
            return 0

        # ── Step 2c: INTERMEDIATE + sun in window ─────────────────────────────
        # Overcast / low lux / low irradiance → no direct sun → default position
        if (
            self.climate_data.lux
            or self.climate_data.irradiance
            or not self.climate_data.is_sunny
        ):
            self.cover.logger.debug(
                "n_w_p(): Intermediate + no direct sun → default"
            )
            return self.cover.default

        # Sunny intermediate: calculate shade position to reduce glare
        self.cover.logger.debug(
            "n_w_p(): Intermediate + sunny → basic calculated (shade only)"
        )
        return super().get_state()

    def normal_without_presence(self) -> int:
        """Determine state for horizontal and vertical covers without occupants.

        When nobody is home covers are always closed (0 %) — regardless of
        sun position, season or temperature thresholds.
        """
        return 0

    def tilt_with_presence(self, degrees: int) -> int:
        """Determine state for tilted blinds with occupants."""
        if self.cover.valid and (
            self.climate_data.lux
            or self.climate_data.irradiance
            or not self.climate_data.is_sunny
        ):
            if self.climate_data.is_summer:
                # If it's summer, return 45 degrees
                return 45 / degrees * 100
            return super().get_state()
        return 80 / degrees * 100

    def tilt_without_presence(self, degrees: int) -> int:
        """Determine state for tilted blinds without occupants.

        When nobody is home slats are always closed (0 %) — regardless of
        sun position, season or temperature thresholds.
        """
        # assert isinstance: tilt_without_presence is only called
        # when blind_type == "cover_tilt", so self.cover is always
        # AdaptiveTiltCover (has beta and mode). The assert lets the linter
        # (pylint/mypy) narrow the type without using cast().
        assert isinstance(self.cover, AdaptiveTiltCover)
        return 0

    def tilt_state(self):
        """Add tilt specific controls."""
        assert isinstance(self.cover, AdaptiveTiltCover), (
            "tilt_state requires AdaptiveTiltCover"
        )
        degrees = 90
        if self.cover.mode == "mode2":
            degrees = 180
        if self.climate_data.is_presence:
            return self.tilt_with_presence(degrees)
        return self.tilt_without_presence(degrees)

    def get_state(self) -> int:
        """Return state."""
        result = self.normal_type_cover()
        if self.climate_data.blind_type == "cover_tilt":
            result = self.tilt_state()
        if self.cover.apply_max_position and result > self.cover.max_pos:
            self.cover.logger.debug(
                "Climate state: Max position applied (%s > %s)",
                result,
                self.cover.max_pos,
            )
            return self.cover.max_pos
        if self.cover.apply_min_position and result < self.cover.min_pos:
            self.cover.logger.debug(
                "Climate state: Min position applied (%s < %s)",
                result,
                self.cover.min_pos,
            )
            return self.cover.min_pos
        return result


@dataclass
class AdaptiveVerticalCover(AdaptiveGeneralCover):
    """Calculate state for Vertical blinds."""

    distance: float
    h_win: float

    def calculate_position(self) -> float:
        """Calculate blind height."""
        # calculate blind height
        blind_height = np.clip(
            (self.distance / cos(rad(self.gamma))) * tan(rad(self.sol_elev)),
            0,
            self.h_win,
        )
        return blind_height

    def calculate_percentage(self) -> float:
        """Convert blind height to percentage or default value."""
        position = self.calculate_position()
        self.logger.debug(
            "Converting height to percentage: %s / %s * 100", position, self.h_win
        )
        result = position / self.h_win * 100
        return round(result)


@dataclass
class AdaptiveHorizontalCover(AdaptiveVerticalCover):
    """Calculate state for Horizontal blinds."""

    awn_length: float
    awn_angle: float

    def calculate_position(self) -> float:
        """Calculate awn length from blind height."""
        awn_angle = 90 - self.awn_angle
        a_angle = 90 - self.sol_elev
        c_angle = 180 - awn_angle - a_angle

        vertical_position = super().calculate_position()
        length = ((self.h_win - vertical_position) * sin(rad(a_angle))) / sin(
            rad(c_angle)
        )
        # return np.clip(length, 0, self.awn_length)
        return length

    def calculate_percentage(self) -> float:
        """Convert awn length to percentage or default value."""
        result = self.calculate_position() / self.awn_length * 100
        return round(result)


@dataclass
class AdaptiveTiltCover(AdaptiveGeneralCover):
    """Calculate state for tilted blinds."""

    slat_distance: float
    depth: float
    mode: str

    @property
    def beta(self):
        """Calculate beta."""
        beta = np.arctan(tan(rad(self.sol_elev)) / cos(rad(self.gamma)))
        return beta

    def calculate_position(self) -> float:
        """Calculate position of venetian blinds.

        https://www.mdpi.com/1996-1073/13/7/1731
        """
        beta = self.beta

        slat = 2 * np.arctan(
            (
                tan(beta)
                + np.sqrt(
                    (tan(beta) ** 2) - ((self.slat_distance / self.depth) ** 2) + 1
                )
            )
            / (1 + self.slat_distance / self.depth)
        )
        result = np.rad2deg(slat)

        return result

    def calculate_percentage(self):
        """Convert tilt angle to percentages or default value."""
        # 0 degrees is closed, 90 degrees is open, 180 degrees is closed
        percentage_single = self.calculate_position() / 90 * 100  # single directional
        percentage_bi = self.calculate_position() / 180 * 100  # bi-directional

        if self.mode == "mode1":
            percentage = percentage_single
        else:
            percentage = percentage_bi

        return round(percentage)
