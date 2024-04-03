"""Config flow for Adaptive Cover integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_AWNING_ANGLE,
    CONF_AZIMUTH,
    CONF_BLUEPRINT,
    CONF_CLIMATE_MODE,
    CONF_DEFAULT_HEIGHT,
    CONF_DELTA_POSITION,
    CONF_DELTA_TIME,
    CONF_DISTANCE,
    CONF_ENTITIES,
    CONF_FOV_LEFT,
    CONF_FOV_RIGHT,
    CONF_HEIGHT_AWNING,
    CONF_HEIGHT_WIN,
    CONF_INVERSE_STATE,
    CONF_LENGTH_AWNING,
    CONF_MAX_POSITION,
    CONF_MODE,
    CONF_OUTSIDETEMP_ENTITY,
    CONF_PRESENCE_ENTITY,
    CONF_SENSOR_TYPE,
    CONF_START_ENTITY,
    CONF_START_TIME,
    CONF_SUNSET_OFFSET,
    CONF_SUNSET_POS,
    CONF_TEMP_ENTITY,
    CONF_TEMP_HIGH,
    CONF_TEMP_LOW,
    CONF_TILT_DEPTH,
    CONF_TILT_DISTANCE,
    CONF_TILT_MODE,
    CONF_WEATHER_ENTITY,
    CONF_WEATHER_STATE,
    DOMAIN,
    SensorType,
)

# DEFAULT_NAME = "Adaptive Cover"

SENSOR_TYPE_MENU = [SensorType.BLIND, SensorType.AWNING, SensorType.TILT]


CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required("name"): selector.TextSelector(),
        vol.Optional(CONF_BLUEPRINT, default=False): bool,
        vol.Optional(CONF_MODE, default="basic"): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=SENSOR_TYPE_MENU, translation_key="mode"
            )
        ),
    }
)

CLIMATE_MODE = vol.Schema(
    {
        vol.Optional(CONF_CLIMATE_MODE, default=False): selector.BooleanSelector(),
    }
)

OPTIONS = vol.Schema(
    {
        vol.Required(CONF_AZIMUTH, default=180): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=359, mode="slider", unit_of_measurement="°"
            )
        ),
        vol.Required(CONF_DEFAULT_HEIGHT, default=60): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1, max=100, step=1, mode="slider", unit_of_measurement="%"
            )
        ),
        vol.Optional(CONF_MAX_POSITION, default=100): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1, max=100, step=1, mode="slider", unit_of_measurement="%"
            )
        ),
        vol.Required(CONF_FOV_LEFT, default=90): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1, max=90, step=1, mode="slider", unit_of_measurement="°"
            )
        ),
        vol.Required(CONF_FOV_RIGHT, default=90): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1, max=90, step=1, mode="slider", unit_of_measurement="°"
            )
        ),
        vol.Required(CONF_SUNSET_POS, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=100, step=1, mode="slider", unit_of_measurement="%"
            )
        ),
        vol.Required(CONF_SUNSET_OFFSET, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(mode="box", unit_of_measurement="minutes")
        ),
        vol.Optional(CONF_ENTITIES, default=[]): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="cover", multiple=True)
        ),
        vol.Required(CONF_INVERSE_STATE, default=False): bool,
    }
)

VERTICAL_OPTIONS = vol.Schema(
    {
        vol.Required(CONF_HEIGHT_WIN, default=2.1): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.1, max=6, step=0.01, mode="slider", unit_of_measurement="m"
            )
        ),
        vol.Required(CONF_DISTANCE, default=0.5): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.1, max=2, step=0.1, mode="slider", unit_of_measurement="m"
            )
        ),
    }
).extend(OPTIONS.schema)

TEST_OPTIONS = vol.Schema(
    {
        vol.Optional(CONF_BLUEPRINT, default=True): bool,
    }
)

HORIZONTAL_OPTIONS = vol.Schema(
    {
        vol.Required(CONF_HEIGHT_AWNING, default=2.1): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.1, max=6, step=0.01, mode="slider", unit_of_measurement="m"
            )
        ),
        vol.Required(CONF_LENGTH_AWNING, default=2.1): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.3, max=6, step=0.01, mode="slider", unit_of_measurement="m"
            )
        ),
        vol.Required(CONF_AWNING_ANGLE, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=45, mode="slider", unit_of_measurement="°"
            )
        ),
    }
).extend(VERTICAL_OPTIONS.schema)

TILT_OPTIONS = vol.Schema(
    {
        vol.Required(CONF_TILT_DEPTH, default=3): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.1, max=15, step=0.1, mode="slider", unit_of_measurement="cm"
            )
        ),
        vol.Required(CONF_TILT_DISTANCE, default=2): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.1, max=15, step=0.1, mode="slider", unit_of_measurement="cm"
            )
        ),
        vol.Required(CONF_TILT_MODE, default="mode2"): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=["mode1", "mode2"], translation_key="tilt_mode"
            )
        ),
    }
).extend(OPTIONS.schema)

CLIMATE_OPTIONS = vol.Schema(
    {
        vol.Required(CONF_TEMP_ENTITY): selector.EntitySelector(
            selector.EntityFilterSelectorConfig(domain=["climate", "sensor"])
        ),
        vol.Required(CONF_TEMP_LOW, default=21): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=86, step=1, mode="slider", unit_of_measurement="°"
            )
        ),
        vol.Required(CONF_TEMP_HIGH, default=25): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=90, step=1, mode="slider", unit_of_measurement="°"
            )
        ),
        vol.Optional(
            CONF_OUTSIDETEMP_ENTITY, default=vol.UNDEFINED
        ): selector.EntitySelector(
            selector.EntityFilterSelectorConfig(domain=["sensor"])
        ),
        vol.Optional(
            CONF_PRESENCE_ENTITY, default=vol.UNDEFINED
        ): selector.EntitySelector(
            selector.EntityFilterSelectorConfig(
                domain=["device_tracker", "zone", "binary_sensor", "input_boolean"]
            )
        ),
        vol.Optional(
            CONF_WEATHER_ENTITY, default=vol.UNDEFINED
        ): selector.EntitySelector(
            selector.EntityFilterSelectorConfig(domain="weather")
        ),
    }
)

WEATHER_OPTIONS = vol.Schema(
    {
        vol.Optional(
            CONF_WEATHER_STATE, default=["sunny", "partlycloudy", "cloudy", "clear"]
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                multiple=True,
                sort=False,
                options=[
                    "clear-night",
                    "clear",
                    "cloudy",
                    "fog",
                    "hail",
                    "lightning",
                    "lightning-rainy",
                    "partlycloudy",
                    "pouring",
                    "rainy",
                    "snowy",
                    "snowy-rainy",
                    "sunny",
                    "windy",
                    "windy-variant",
                    "exceptional",
                ],
            )
        )
    }
)


AUTOMATION_CONFIG = vol.Schema(
    {
        vol.Required(CONF_DELTA_POSITION, default=1): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1, max=90, step=1, mode="slider", unit_of_measurement="%"
            )
        ),
        vol.Optional(CONF_DELTA_TIME, default=2): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=2, mode="box", unit_of_measurement="minutes"
            )
        ),
        vol.Optional(CONF_START_TIME, default="00:00:00"): selector.TimeSelector(),
        vol.Optional(CONF_START_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor","input_datetime"])
        ),
    }
)


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle ConfigFlow."""

    def __init__(self) -> None:  # noqa: D107
        super().__init__()
        self.type_blind: str | None = None
        self.config: dict[str, Any] = {}
        self.mode: str = "basic"

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        # errors = {}
        if user_input:
            self.config = user_input
            if self.config[CONF_MODE] == SensorType.BLIND:
                return await self.async_step_vertical()
            if self.config[CONF_MODE] == SensorType.AWNING:
                return await self.async_step_horizontal()
            if self.config[CONF_MODE] == SensorType.TILT:
                return await self.async_step_tilt()
        return self.async_show_form(step_id="user", data_schema=CONFIG_SCHEMA)

    async def async_step_vertical(self, user_input: dict[str, Any] | None = None):
        """Show basic config for vertical blinds."""
        self.type_blind = SensorType.BLIND
        if user_input is not None:
            self.config.update(user_input)
            return await self.async_step_automation()
        return self.async_show_form(
            step_id="vertical",
            data_schema=CLIMATE_MODE.extend(VERTICAL_OPTIONS.schema),
        )

    async def async_step_horizontal(self, user_input: dict[str, Any] | None = None):
        """Show basic config for horizontal blinds."""
        self.type_blind = SensorType.AWNING
        if user_input is not None:
            self.config.update(user_input)
            return await self.async_step_automation()
        return self.async_show_form(
            step_id="horizontal",
            data_schema=CLIMATE_MODE.extend(HORIZONTAL_OPTIONS.schema),
        )

    async def async_step_tilt(self, user_input: dict[str, Any] | None = None):
        """Show basic config for tilted blinds."""
        self.type_blind = SensorType.TILT
        if user_input is not None:
            self.config.update(user_input)
            return await self.async_step_automation()
        return self.async_show_form(
            step_id="tilt", data_schema=CLIMATE_MODE.extend(TILT_OPTIONS.schema)
        )

    async def async_step_automation(self, user_input: dict[str, Any] | None = None):
        """Manage automation options."""
        if user_input is not None:
            self.config.update(user_input)
            if self.config[CONF_CLIMATE_MODE] is True:
                return await self.async_step_climate()
            return await self.async_step_update()
        return self.async_show_form(step_id="automation", data_schema=AUTOMATION_CONFIG)

    async def async_step_climate(self, user_input: dict[str, Any] | None = None):
        """Manage climate options."""
        if user_input is not None:
            self.config.update(user_input)
            if self.config.get(CONF_WEATHER_ENTITY):
                return await self.async_step_weather()
            return await self.async_step_update()
        return self.async_show_form(step_id="climate", data_schema=CLIMATE_OPTIONS)

    async def async_step_weather(self, user_input: dict[str, Any] | None = None):
        """Manage weather conditions."""
        if user_input is not None:
            self.config.update(user_input)
            return await self.async_step_update()
        return self.async_show_form(step_id="weather", data_schema=WEATHER_OPTIONS)

    async def async_step_update(self, user_input: dict[str, Any] | None = None):
        """Create entry."""
        type = {
            "cover_blind": "Vertical",
            "cover_awning": "Horizontal",
            "cover_tilt": "Tilt",
        }
        return self.async_create_entry(
            title=f"{type[self.type_blind]} {self.config['name']}",
            data={
                "name": self.config["name"],
                CONF_BLUEPRINT: self.config[CONF_BLUEPRINT],
                CONF_SENSOR_TYPE: self.type_blind,
            },
            options={
                CONF_MODE: self.mode,
                CONF_AZIMUTH: self.config.get(CONF_AZIMUTH),
                CONF_HEIGHT_WIN: self.config.get(CONF_HEIGHT_WIN),
                CONF_DISTANCE: self.config.get(CONF_DISTANCE),
                CONF_DEFAULT_HEIGHT: self.config.get(CONF_DEFAULT_HEIGHT),
                CONF_MAX_POSITION: self.config.get(CONF_MAX_POSITION),
                CONF_FOV_LEFT: self.config.get(CONF_FOV_LEFT),
                CONF_FOV_RIGHT: self.config.get(CONF_FOV_RIGHT),
                CONF_ENTITIES: self.config.get(CONF_ENTITIES),
                CONF_INVERSE_STATE: self.config.get(CONF_INVERSE_STATE),
                CONF_SUNSET_POS: self.config.get(CONF_SUNSET_POS),
                CONF_SUNSET_OFFSET: self.config.get(CONF_SUNSET_OFFSET),
                CONF_LENGTH_AWNING: self.config.get(CONF_LENGTH_AWNING),
                CONF_AWNING_ANGLE: self.config.get(CONF_AWNING_ANGLE),
                CONF_TILT_DISTANCE: self.config.get(CONF_TILT_DISTANCE),
                CONF_TILT_DEPTH: self.config.get(CONF_TILT_DEPTH),
                CONF_TILT_MODE: self.config.get(CONF_TILT_MODE),
                CONF_TEMP_ENTITY: self.config.get(CONF_TEMP_ENTITY),
                CONF_PRESENCE_ENTITY: self.config.get(CONF_PRESENCE_ENTITY),
                CONF_WEATHER_ENTITY: self.config.get(CONF_WEATHER_ENTITY),
                CONF_TEMP_LOW: self.config.get(CONF_TEMP_LOW),
                CONF_TEMP_HIGH: self.config.get(CONF_TEMP_HIGH),
                CONF_OUTSIDETEMP_ENTITY: self.config.get(CONF_OUTSIDETEMP_ENTITY),
                CONF_CLIMATE_MODE: self.config.get(CONF_CLIMATE_MODE),
                CONF_WEATHER_STATE: self.config.get(CONF_WEATHER_STATE),
                CONF_DELTA_POSITION: self.config.get(CONF_DELTA_POSITION),
                CONF_DELTA_TIME: self.config.get(CONF_DELTA_TIME),
                CONF_START_TIME: self.config.get(CONF_START_TIME),
                CONF_START_ENTITY: self.config.get(CONF_START_ENTITY),
            },
        )


class OptionsFlowHandler(OptionsFlow):
    """Options to adjust parameters."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        # super().__init__(config_entry)
        self.config_entry = config_entry
        self.current_config: dict = dict(config_entry.data)
        self.options = dict(config_entry.options)
        self.sensor_type: SensorType = (
            self.current_config.get(CONF_SENSOR_TYPE) or SensorType.BLIND
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        return self.async_show_menu(
            step_id="init",
            menu_options={
                "automation": "Change Automation Config",
                "blind": "Adjust blind parameters",
            },
        )

    async def async_step_automation(self, user_input: dict[str, Any] | None = None):
        """Manage automation options."""
        if user_input is not None:
            self.options.update(user_input)
            return await self._update_options()
        return self.async_show_form(step_id="automation", data_schema=AUTOMATION_CONFIG)

    async def async_step_blind(self, user_input: dict[str, Any] | None = None):
        """Adjust blind parameters."""
        if self.sensor_type == SensorType.BLIND:
            return await self.async_step_vertical()
        if self.sensor_type == SensorType.AWNING:
            return await self.async_step_horizontal()
        if self.sensor_type == SensorType.TILT:
            return await self.async_step_tilt()

    async def async_step_vertical(self, user_input: dict[str, Any] | None = None):
        """Show basic config for vertical blinds."""
        self.type_blind = SensorType.BLIND
        schema = CLIMATE_MODE.extend(VERTICAL_OPTIONS.schema)
        if self.options[CONF_CLIMATE_MODE]:
            schema = VERTICAL_OPTIONS
        if user_input is not None:
            self.options.update(user_input)
            if self.options[CONF_CLIMATE_MODE]:
                return await self.async_step_climate()
            return await self._update_options()
        return self.async_show_form(
            step_id="vertical",
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input or self.options
            ),
        )

    async def async_step_horizontal(self, user_input: dict[str, Any] | None = None):
        """Show basic config for horizontal blinds."""
        self.type_blind = SensorType.AWNING
        schema = CLIMATE_MODE.extend(HORIZONTAL_OPTIONS.schema)
        if self.options[CONF_CLIMATE_MODE]:
            schema = HORIZONTAL_OPTIONS
        if user_input is not None:
            self.options.update(user_input)
            if self.options[CONF_CLIMATE_MODE]:
                return await self.async_step_climate()
            return await self._update_options()
        return self.async_show_form(
            step_id="horizontal",
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input or self.options
            ),
        )

    async def async_step_tilt(self, user_input: dict[str, Any] | None = None):
        """Show basic config for tilted blinds."""
        self.type_blind = SensorType.TILT
        schema = CLIMATE_MODE.extend(TILT_OPTIONS.schema)
        if self.options[CONF_CLIMATE_MODE]:
            schema = TILT_OPTIONS
        if user_input is not None:
            self.options.update(user_input)
            if self.options[CONF_CLIMATE_MODE]:
                return await self.async_step_climate()
            return await self._update_options()
        return self.async_show_form(
            step_id="tilt",
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input or self.options
            ),
        )

    async def async_step_climate(self, user_input: dict[str, Any] | None = None):
        """Manage climate options."""
        if user_input is not None:
            entities = [
                CONF_OUTSIDETEMP_ENTITY,
                CONF_WEATHER_ENTITY,
                CONF_PRESENCE_ENTITY,
            ]
            self.optional_entities(entities, user_input)
            self.options.update(user_input)
            if self.options.get(CONF_WEATHER_ENTITY):
                return await self.async_step_weather()
            return await self._update_options()
        return self.async_show_form(
            step_id="climate",
            data_schema=self.add_suggested_values_to_schema(
                CLIMATE_OPTIONS, user_input or self.options
            ),
        )

    async def async_step_weather(self, user_input: dict[str, Any] | None = None):
        """Manage weather conditions."""
        if user_input is not None:
            self.options.update(user_input)
            return await self._update_options()
        return self.async_show_form(
            step_id="weather",
            data_schema=self.add_suggested_values_to_schema(
                WEATHER_OPTIONS, user_input or self.options
            ),
        )

    async def _update_options(self) -> FlowResult:
        """Update config entry options."""
        return self.async_create_entry(title="", data=self.options)

    def optional_entities(self, keys: list, user_input: dict[str, Any] | None = None):
        """Set value to None if key does not exist."""
        for key in keys:
            if key not in user_input:
                user_input[key] = None
