"""Generate values for all types of covers."""
from datetime import timedelta, datetime
import numpy as np
import pandas as pd

from numpy import cos, tan, sin
from numpy import radians as rad
from .sun import SunData


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
        self.sun_data = SunData(self.hass, timezone)

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
        """Determine if sun infront of window."""
        # clip azi_min and azi_max to 90
        azi_min = min(self.fov_left, 90)
        azi_max = min(self.fov_right, 90)

        # valid sun positions are those within the blind's azimuth range and above the horizon (FOV)
        valid = (self.gamma < azi_min) & (self.gamma > -azi_max) & (self.sol_elev >= 0)
        return valid

    @property
    def default_pos(self) -> tuple:
        """Change default position at sunset."""
        default = self.h_def
        sunset = self.sun_data.sunset().replace(tzinfo=None)
        condition = datetime.utcnow() > sunset + timedelta(minutes=self.sunset_off)
        if condition:
            default = self.sunset_pos
        return default, condition

    def fov(self) -> list:
        """Return field of view."""
        return [self.azi_min_abs, self.azi_max_abs]


class AdaptiveVerticalCover(AdaptiveGeneralCover):
    """Calculate state for Vertical blinds."""

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
        distance,
        h_win,
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

    def blind_state_perc(self) -> float:
        """Convert blind height to percentage or default value."""
        default_pos, time_con = self.default_pos
        blind_height = np.where(
            (self.valid) & (not time_con),
            self.calculate_blind_height() / self.h_win * 100,
            default_pos,
        )
        result = np.clip(blind_height, 0, 100)
        return result


class AdaptiveHorizontalCover(AdaptiveVerticalCover):
    """Calculate state for Horizontal blinds."""

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
        distance,
        h_win,
        awn_length,
        awn_angle,
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

    def awn_state_perc(self) -> float:
        """Convert awn length to percentage or default value."""
        default_pos, time_con = self.default_pos
        awn_length = np.where(
            (self.valid) & (not time_con),
            self.calculate_awning_length / self.awn_length * 100,
            default_pos,
        )
        result = np.clip(awn_length, 0, 100)
        return result


class AdaptiveTiltCover(AdaptiveGeneralCover):
    """Calculate state for tilted blinds."""

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
        slat_distance,
        depth,
        mode,
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
        self.slat_distance = slat_distance
        self.depth = depth
        self.mode = mode

    @property
    def calculate_tilt_angle(self) -> float:
        """Calculate tilt angle of venetian blinds.

        https://www.mdpi.com/1996-1073/13/7/1731
        """
        beta = np.arctan(tan(rad(self.sol_elev)) / cos(rad(self.gamma)))

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

    def tilt_state_perc(self):
        """Convert tilt angle to percentages or default value."""
        default_pos, time_con = self.default_pos
        # 0 degrees is closed, 90 degrees is open, 180 degrees is closed
        percentage_single = self.calculate_tilt_angle / 90 * 100  # single directional
        percentage_bi = self.calculate_tilt_angle / 180 * 100  # bi-directional

        if self.mode == "mode1":
            percentage = percentage_single
        else:
            percentage = percentage_bi

        angle = np.where((self.valid) & (not time_con), percentage, default_pos)
        result = np.clip(angle, 0, 100)
        return result
