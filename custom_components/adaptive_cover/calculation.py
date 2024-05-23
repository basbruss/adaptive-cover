"""Generate values for all types of covers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import state_attr
from numpy import cos, sin, tan
from numpy import radians as rad

from .helpers import get_domain, get_safe_state
from .sun import SunData


@dataclass
class AdaptiveGeneralCover(ABC):
    """Collect common data."""

    hass: HomeAssistant
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
    blind_spot_left: int
    blind_spot_right: int
    blind_spot_elevation: int
    blind_spot_on: bool
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
        else:
            return (
                solpos[frame].index[0].to_pydatetime(),
                solpos[frame].index[-1].to_pydatetime(),
            )

    @property
    def _get_azimuth_edges(self) -> tuple[int,int]:
        """Calculate azimuth edges."""
        return self.fov_left + self.fov_right

    @property
    def is_sun_in_blind_spot(self) -> bool:
        """Check if sun is in blind spot."""
        if self.blind_spot_left is not None and self.blind_spot_right is not None and self.blind_spot_on:
            left_edge = self.fov_left - self.blind_spot_left
            right_edge = self.fov_left - self.blind_spot_right
            blindspot = (self.gamma <= left_edge) & (self.gamma >= right_edge)
            if self.blind_spot_elevation is not None:
                blindspot = blindspot & (self.sol_elev <= self.blind_spot_elevation)
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
    def valid(self) -> bool:
        """Determine if sun is in front of window."""
        # clip azi_min and azi_max to 90
        azi_min = min(self.fov_left, 90)
        azi_max = min(self.fov_right, 90)

        # valid sun positions are those within the blind's azimuth range and above the horizon (FOV)
        valid = (self.gamma < azi_min) & (self.gamma > -azi_max) & (self.sol_elev >= 0)
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
        state = np.where(
            (self.cover.valid) & (not self.cover.sunset_valid) & (not self.cover.is_sun_in_blind_spot),
            self.cover.calculate_percentage(),
            self.cover.default,
        )
        result = np.clip(state, 0, 100)
        if result > self.cover.max_pos:
            return self.cover.max_pos
        return result


@dataclass
class ClimateCoverData:
    """Fetch additional data."""

    hass: HomeAssistant
    temp_entity: str
    temp_low: float
    temp_high: float
    presence_entity: str
    weather_entity: str
    weather_condition: list[str]
    outside_entity: str
    temp_switch: bool
    blind_type: str

    @property
    def outside_temperature(self):
        """Get outside temperature."""
        temp = None
        if self.weather_entity:
            temp = state_attr(self.hass, self.weather_entity, "temperature")
        if self.outside_entity:
            temp = get_safe_state(
                self.hass,
                self.outside_entity,
            )
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
    def get_current_temperature(self) -> float:
        """Get temperature."""
        if self.temp_switch:
            if self.outside_temperature:
                return float(self.outside_temperature)
        if self.inside_temperature:
            return float(self.inside_temperature)

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
        """Check if temperature is below threshold."""
        if self.temp_low is not None and self.get_current_temperature is not None:
            return self.get_current_temperature < self.temp_low
        return False

    @property
    def is_summer(self) -> bool:
        """Check if temperature is over threshold."""
        if self.temp_high is not None and self.get_current_temperature is not None:
            return self.get_current_temperature > self.temp_high
        return False

    @property
    def is_sunny(self) -> bool:
        """Check if condition can contain radiation in winter."""
        weather_state = None
        if self.weather_entity is not None:
            weather_state = get_safe_state(self.hass, self.weather_entity)
        if self.weather_condition is not None:
            return weather_state in self.weather_condition
        return True


@dataclass
class ClimateCoverState(NormalCoverState):
    """Compute state for climate control operation."""

    climate_data: ClimateCoverData

    def normal_type_cover(self) -> int:
        """Determine state for horizontal and vertical covers."""
        # glare does not matter
        if self.climate_data.is_presence is False and self.cover.sol_elev > 0:
            # allow maximum solar radiation
            if self.climate_data.is_winter:
                return 100
            # don't allow solar radiation
            if self.climate_data.is_summer:
                return 0
            return self.cover.default

        # prefer glare reduction over climate control
        # adjust according basic algorithm
        if not self.climate_data.is_sunny and not self.climate_data.is_summer:
            return self.cover.default
        return super().get_state()

    def control_method_tilt_single(self):
        """Single direction control schema."""
        if self.climate_data.is_presence:
            if self.climate_data.is_winter and self.climate_data.is_sunny:
                return super().get_state()
            if self.climate_data.is_summer:
                return 45 / 90 * 100
            # 80 degrees is optimal by no need to shield or use solar contribution
            if self.cover.valid and self.climate_data.is_sunny:
                return super().get_state()
            return 80 / 90 * 100
        else:
            if self.climate_data.is_winter:
                return 100
            if self.climate_data.is_summer:
                return 0
            # 80 degrees is optimal by no need to shield or use solar contribution
            return 80 / 90 * 100

    def control_method_tilt_bi(self):
        """bi-directional control schema."""
        beta = np.rad2deg(self.cover.beta)
        if self.climate_data.is_presence:
            if self.climate_data.is_winter and self.climate_data.is_sunny:
                return super().get_state()
            if self.climate_data.is_summer:
                return 45 / 180 * 100
            # 80 degrees is optimal by no need to shield or use solar contribution
            if self.cover.valid and self.climate_data.is_sunny:
                return super().get_state()
            return 80 / 180 * 100
        else:
            if self.climate_data.is_winter:
                # parallel to sun beams
                if self.cover.valid:
                    return (beta + 90) / 180 * 100
                return 110 / 180 * 100
            if self.climate_data.is_summer:
                return 0
            # 80 degrees is optimal by no need to shield or use solar contribution
            return 80 / 180 * 100

    def tilt_state(self):
        """Add tilt specific controls."""
        if (
            self.climate_data.get_current_temperature is not None
            and self.cover.sol_elev > 0
        ):
            if self.cover.mode == "mode1":
                self.control_method_tilt_single()
            if self.cover.mode == "mode2":
                return self.control_method_tilt_bi()
        return super().get_state()

    def get_state(self) -> int:
        """Return state."""
        result = self.normal_type_cover()
        if self.climate_data.blind_type == "cover_tilt":
            result = self.tilt_state()
        if result > self.cover.max_pos:
            return self.cover.max_pos
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
        result = self.calculate_position() / self.h_win * 100
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

        length = (
            (self.h_win - super().calculate_position()) * sin(rad(a_angle))
        ) / sin(rad(c_angle))
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
