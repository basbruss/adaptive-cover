"""Constants for integration_blueprint."""

import logging

DOMAIN = "adaptive_cover"
LOGGER = logging.getLogger(__package__)
_LOGGER = logging.getLogger(__name__)

ATTR_POSITION = "position"
ATTR_TILT_POSITION = "tilt_position"

CONF_AZIMUTH = "set_azimuth"
CONF_BLUEPRINT = "blueprint"
CONF_HEIGHT_WIN = "window_height"
CONF_DISTANCE = "distance_shaded_area"
CONF_DEFAULT_HEIGHT = "default_percentage"
CONF_FOV_LEFT = "fov_left"
CONF_FOV_RIGHT = "fov_right"
CONF_ENTITIES = "group"
CONF_HEIGHT_AWNING = "height_awning"
CONF_LENGTH_AWNING = "length_awning"
CONF_AWNING_ANGLE = "angle"
CONF_SENSOR_TYPE = "sensor_type"
CONF_INVERSE_STATE = "inverse_state"
CONF_SUNSET_POS = "sunset_position"
CONF_SUNSET_OFFSET = "sunset_offset"
CONF_TILT_DEPTH = "slat_depth"
CONF_TILT_DISTANCE = "slat_distance"
CONF_TILT_MODE = "tilt_mode"
CONF_SUNSET_POS = "sunset_position"
CONF_SUNSET_OFFSET = "sunset_offset"
CONF_SUNRISE_OFFSET = "sunrise_offset"
CONF_TEMP_ENTITY = "temp_entity"
CONF_PRESENCE_ENTITY = "presence_entity"
CONF_WEATHER_ENTITY = "weather_entity"
CONF_TEMP_LOW = "temp_low"
CONF_TEMP_HIGH = "temp_high"
CONF_MODE = "mode"
CONF_CLIMATE_MODE = "climate_mode"
CONF_WEATHER_STATE = "weather_state"
CONF_MAX_POSITION = "max_position"
CONF_OUTSIDETEMP_ENTITY = "outside_temp"


CONF_DELTA_POSITION = "delta_position"
CONF_DELTA_TIME = "delta_time"
CONF_START_TIME = "start_time"
CONF_START_ENTITY = "start_entity"
CONF_END_TIME = "end_time"
CONF_END_ENTITY = "end_entity"
CONF_MANUAL_OVERRIDE_DURATION = "manual_override_duration"
CONF_MANUAL_OVERRIDE_RESET = "manual_override_reset"

STRATEGY_MODE_BASIC = "basic"
STRATEGY_MODE_CLIMATE = "climate"
STRATEGY_MODES = [
    STRATEGY_MODE_BASIC,
    STRATEGY_MODE_CLIMATE,
]


class SensorType:
    """Possible modes for a number selector."""

    BLIND = "cover_blind"
    AWNING = "cover_awning"
    TILT = "cover_tilt"
