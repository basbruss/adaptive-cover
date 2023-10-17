import numpy as np
from datetime import date, timedelta, datetime
from numpy import cos, tan, sin
from numpy import radians as rad
from .sun import SunData

# from pvlib import solarposition
import pandas as pd


class AdaptiveCoverCalculator(

):
    """Calculate variables"""

    def __init__(
        self,
        hass,
        timezone,
        lat,
        lon,
        sol_azi,
        sol_elev,
        win_azi,
        h_win,
        distance,
        fov_left,
        fov_right,
        def_height,
        angle,
        l_awn,
        sunset_pos,
        sunset_off,
        slat_distance,
        depth,
        mode: 'mode2'
    ) -> None:
        self.hass = hass
        self.timezone = timezone
        self.lat = lat
        self.lon = lon
        self.sol_azi = sol_azi
        self.sol_elev = sol_elev
        self.win_azi = win_azi
        self.h_win = h_win
        self.distance = distance
        self.azi_left = fov_left
        self.azi_right = fov_right
        self.h_def = def_height
        self.angle = angle
        self.l_awn = l_awn
        self.sunset_pos = sunset_pos
        self.sunset_off = sunset_off
        self.slat_distance = slat_distance
        self.depth = depth
        self.sun_data = SunData(self.hass,timezone)
        self.mode = mode


    def solar_times(self):
        """Determine start/end times"""
        df_today = pd.DataFrame({"azimuth":self.sun_data.solar_azimuth, "elevation":self.sun_data.solar_elevation})
        solpos = df_today.set_index(self.sun_data.times)
        frame = (solpos["azimuth"] > self.azi_min_abs) & (solpos["azimuth"] < self.azi_max_abs) & (solpos["elevation"] > 0)
        return solpos[frame].index[0].to_pydatetime(), solpos[frame].index[-1].to_pydatetime()

    def value(self, value: any):
        """Return input value"""
        return value

    @property
    def azi_min_abs(self):
        """Calculate min azimuth"""
        azi_min_abs = (self.win_azi - self.azi_left + 360) % 360
        return azi_min_abs

    @property
    def azi_max_abs(self):
        """Calculate max azimuth"""
        azi_max_abs = (self.win_azi + self.azi_right + 360) % 360
        return azi_max_abs

    @property
    def gamma(self):
        """Calculate Gamma"""
        # surface solar azimuth
        gamma = (self.win_azi - self.sol_azi + 180) % 360 - 180
        return gamma

    @property
    def valid(self):
        """Determine if sun infront of window"""
        # clip azi_min and azi_max to 90
        azi_min = min(self.azi_left, 90)
        azi_max = min(self.azi_right, 90)

        # valid sun positions are those within the blind's azimuth range and above the horizon (FOV)
        valid = (self.gamma < azi_min) & (self.gamma > -azi_max) & (self.sol_elev >= 0)
        return valid

    def fov(self):
        """Return field of view"""
        return [self.azi_min_abs, self.azi_max_abs]

    @property
    def calculate_blind_height(self)-> float:
        """Calculate blind height"""
        # calculate blind height
        blind_height = np.clip(
            (self.distance / cos(rad(self.gamma))) * tan(rad(self.sol_elev)),
            0,
            self.h_win,
        )
        return blind_height

    @property
    def calculate_awning_length(self) -> float:
        """Calculate awn length from blind height"""
        awn_angle = 90 - self.angle
        a_angle = 90 - self.sol_elev
        c_angle = 180 - awn_angle - a_angle

        length = ((self.h_win - self.calculate_blind_height) * sin(rad(a_angle))) / sin(rad(c_angle))
        return length

    @property
    def calculate_tilt_angle(self) -> float:
        """
            Calculate tilt angle of venetian blinds

            https://www.mdpi.com/1996-1073/13/7/1731
        """
        beta = np.arctan(tan(rad(self.sol_elev))/cos(rad(self.gamma)))

        slat = 2*np.arctan(
            (tan(beta)+np.sqrt((tan(beta)**2)-((self.slat_distance/self.depth)**2)+1))/
            (1+self.slat_distance/self.depth)
        )
        result = np.rad2deg(slat)

        return result

    @property
    def default_pos(self):
        """Change default position at sunset"""
        default = self.h_def
        sunset = self.sun_data.sunset().replace(tzinfo=None)
        condition = datetime.utcnow() > sunset + timedelta(minutes=self.sunset_off)
        if condition:
            default = self.sunset_pos
        return default, condition

    def blind_state_perc(self) -> float:
        """Convert blind height to percentage or default value"""
        default_pos, time_con = self.default_pos
        blind_height = np.where(
            (self.valid) & (not time_con),
            self.calculate_blind_height / self.h_win * 100,
            default_pos,
        )
        result = np.clip(blind_height, 0, 100)
        return result

    def awn_state_perc(self) -> float:
        """Convert awn length to percentage or default value"""
        default_pos, time_con = self.default_pos
        awn_length = np.where(
            (self.valid)& (not time_con),
            self.calculate_awning_length / self.l_awn * 100,
            default_pos
        )
        result = np.clip(awn_length, 0, 100)
        return result

    def tilt_state_perc(self):
        """Convert tilt angle to percentages or default value"""
        default_pos, time_con = self.default_pos
        # 0 degrees is closed, 90 degrees is open, 180 degrees is closed
        percentage_single = self.calculate_tilt_angle / 90 * 100 # single directional
        percentage_bi = self.calculate_tilt_angle / 180 * 100   # bi-directional


        if self.mode == 'mode1':
            percentage = percentage_single
        else:
            percentage = percentage_bi

        angle = np.where(
            (self.valid)& (not time_con),
            percentage,
            default_pos
        )
        result = np.clip(angle, 0, 100)
        return result
