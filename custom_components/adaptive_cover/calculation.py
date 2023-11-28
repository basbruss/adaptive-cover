"""Generate values for all types of covers."""
from datetime import timedelta, datetime, date
import numpy as np
import pandas as pd

from homeassistant.core import split_entity_id
from numpy import cos, tan, sin
from numpy import radians as rad
from .sun import SunData

def get_domain(entity: str):
    """Get domain of entity"""
    if entity is not None:
        domain, object_id = split_entity_id(entity)
        return domain

class AdaptiveGeneralCover:
    """Collect common data."""

    def __init__(  # noqa: D107
        self,
        hass,
        sol_azi,
        sol_elev,
        sunset_pos,
        sunset_off,
        timezone,
        fov_left,
        fov_right,
        win_azi,
        h_def,
    ) -> None:
        self.hass = hass
        self.sol_azi = sol_azi
        self.sol_elev = sol_elev
        self.sunset_pos = sunset_pos
        self.sunset_off = sunset_off
        self.timezone = timezone
        self.fov_left = fov_left
        self.fov_right = fov_right
        self.win_azi = win_azi
        self.h_def = h_def
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
        condition = datetime.utcnow() > sunset + timedelta(minutes=self.sunset_off)
        return condition

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

    def calculated_state(self) -> float:
        """Placeholder for child class."""
        return 0

    def basic_state(self) -> float:
        """Convert blind height to percentage or default value."""
        state = np.where(
            (self.valid) & (not self.sunset_valid),
            self.calculated_state(),
            self.default,
        )
        result = np.clip(state, 0, 100)
        return result


class CoverStrategy(AdaptiveGeneralCover):
    """Determines the control method for climate control."""

    def __init__(
        self,
        hass,
        sol_azi,
        sol_elev,
        sunset_pos,
        sunset_off,
        timezone,
        fov_left,
        fov_right,
        win_azi,
        h_def,
        temp=None,
        temp_low=None,
        temp_high=None,
        presence=None,
        presence_entity=None
    ) -> None:
        super().__init__(
            hass,
            sol_azi,
            sol_elev,
            sunset_pos,
            sunset_off,
            timezone,
            fov_left,
            fov_right,
            win_azi,
            h_def,
        )
        self.temp = temp
        self.low_point = temp_low
        self.high_point = temp_high
        self.presence = presence
        self.presence_entity = presence_entity

    @property
    def is_presence(self):
        """Checks if people are present."""
        # set to true if no sensor is defined
        if self.presence is not None:
            domain = get_domain(self.presence_entity)
            if domain == "device_tracker":
                return self.presence == "home"
            if domain == "zone":
                return int(self.presence) > 0
            if domain == "binary_sensor":
                return bool(self.presence)
        return True

    def climate_state(self):
        """Adjust state to environment needs."""
        # glare does not matter
        if self.is_presence is False and self.temp is not None:
            # allow maximum solar radiation
            temp = float(self.temp)
            if temp < self.low_point:
                return 100
            # don't allow solar radiation
            if temp > self.high_point:
                return 0
            return self.default

        # prefer glare reduction over climate control
        # adjust according basic algorithm
        return self.basic_state()

    # @property
    # def default(self):
    #     """placeholder for default position"""
    #     pass


class AdaptiveVerticalCover(CoverStrategy):
    """Calculate state for Vertical blinds."""

    def __init__(
        self,
        hass,
        sol_azi,
        sol_elev,
        sunset_pos,
        sunset_off,
        timezone,
        fov_left,
        fov_right,
        win_azi,
        h_def,
        distance,
        h_win,
        temp=None,
        temp_low=None,
        temp_high=None,
        presence=None,
        presence_entity=None
    ) -> None:
        super().__init__(
            hass,
            sol_azi,
            sol_elev,
            sunset_pos,
            sunset_off,
            timezone,
            fov_left,
            fov_right,
            win_azi,
            h_def,
            temp,
            temp_low,
            temp_high,
            presence,
            presence_entity
        )
        self.distance = distance
        self.h_win = h_win

    def calculate_blind_height(self) -> float:
        """Calculate blind height."""
        # calculate blind height
        blind_height = np.clip(
            (self.distance / cos(rad(self.gamma))) * tan(rad(self.sol_elev)),
            0,
            self.h_win,
        )
        return blind_height

    def calculated_state(self) -> float:
        """Convert blind height to percentage or default value."""
        result = self.calculate_blind_height() / self.h_win * 100
        return result


class AdaptiveHorizontalCover(AdaptiveVerticalCover):
    """Calculate state for Horizontal blinds."""

    def __init__(
        self,
        hass,
        sol_azi,
        sol_elev,
        sunset_pos,
        sunset_off,
        timezone,
        fov_left,
        fov_right,
        win_azi,
        h_def,
        distance,
        h_win,
        awn_length,
        awn_angle,
        temp=None,
        temp_low=None,
        temp_high=None,
        presence=None,
        presence_entity=None
    ) -> None:
        super().__init__(
            hass,
            sol_azi,
            sol_elev,
            sunset_pos,
            sunset_off,
            timezone,
            fov_left,
            fov_right,
            win_azi,
            h_def,
            distance,
            h_win,
            temp,
            temp_low,
            temp_high,
            presence,
            presence_entity
        )
        self.awn_length = awn_length
        self.awn_angle = awn_angle

    @property
    def calculate_awning_length(self) -> float:
        """Calculate awn length from blind height."""
        awn_angle = 90 - self.awn_angle
        a_angle = 90 - self.sol_elev
        c_angle = 180 - awn_angle - a_angle

        length = (
            (self.h_win - self.calculate_blind_height()) * sin(rad(a_angle))
        ) / sin(rad(c_angle))
        return length

    def calculated_state(self) -> float:
        """Convert awn length to percentage or default value."""
        result = self.calculate_awning_length / self.awn_length * 100
        return result


class AdaptiveTiltCover(CoverStrategy):
    """Calculate state for tilted blinds."""

    def __init__(
        self,
        hass,
        sol_azi,
        sol_elev,
        sunset_pos,
        sunset_off,
        timezone,
        fov_left,
        fov_right,
        win_azi,
        h_def,
        slat_distance,
        depth,
        mode,
        temp=None,
        temp_low=None,
        temp_high=None,
        presence=None,
        presence_entity=None
    ) -> None:
        super().__init__(
            hass,
            sol_azi,
            sol_elev,
            sunset_pos,
            sunset_off,
            timezone,
            fov_left,
            fov_right,
            win_azi,
            h_def,
            temp,
            temp_low,
            temp_high,
            presence,
            presence_entity
        )
        self.slat_distance = slat_distance
        self.depth = depth
        self.mode = mode

    @property
    def beta(self):
        """Calculate beta."""
        beta = np.arctan(tan(rad(self.sol_elev)) / cos(rad(self.gamma)))
        return beta

    @property
    def calculate_tilt_angle(self) -> float:
        """Calculate tilt angle of venetian blinds.

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

    def calculated_state(self):
        """Convert tilt angle to percentages or default value."""
        # 0 degrees is closed, 90 degrees is open, 180 degrees is closed
        percentage_single = self.calculate_tilt_angle / 90 * 100  # single directional
        percentage_bi = self.calculate_tilt_angle / 180 * 100  # bi-directional

        if self.mode == "mode1":
            percentage = percentage_single
        else:
            percentage = percentage_bi

        return percentage

    def control_method_tilt_single(self):
        """Single direction control schema."""
        temp = float(self.temp)
        if self.is_presence is False:
            if temp < self.low_point:
                return 100
            if temp > self.high_point:
                return 0
            # 80 degrees is optimal by no need to shield or use solar contribution
            return 80 / 90 * 100
        if self.is_presence:
            if temp < self.low_point:
                return self.basic_state()
            if temp > self.high_point:
                return 45 / 90 * 100
            # 80 degrees is optimal by no need to shield or use solar contribution
            if self.valid:
                return self.basic_state()
            return 80 / 90 * 100

    def control_method_tilt_bi(self):
        """bi-directional control schema."""
        beta = np.rad2deg(self.beta)
        temp = float(self.temp)
        if self.is_presence is False:
            if temp < self.low_point:
                # parallel to sun beams
                if self.valid:
                    return (beta + 90) / 180 * 100
                return 110 / 180 * 100
            if temp > self.high_point:
                return 0
            # 80 degrees is optimal by no need to shield or use solar contribution
            return 80 / 180 * 100
        if self.is_presence:
            if temp < self.low_point:
                return self.basic_state()
            if temp > self.high_point:
                return 45 / 180 * 100
            # 80 degrees is optimal by no need to shield or use solar contribution
            if self.valid:
                return self.basic_state()
            return 80 / 180 * 100

    def climate_state(self):
        """Add tilt specific controls."""
        if self.temp is not None:
            if self.mode == "mode1":
                self.control_method_tilt_single()
            if self.mode == "mode2":
                return self.control_method_tilt_bi()
        return self.basic_state()
