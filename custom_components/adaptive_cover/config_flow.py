"""Config flow for Adaptive Cover integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import DOMAIN
from homeassistant.helpers import selector
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import callback
from homeassistant.config_entries import (
    ConfigFlow,
    OptionsFlowWithConfigEntry,
    ConfigEntry,
)

from .const import (
    DOMAIN,
    CONF_AZIMUTH,
    CONF_BLUEPRINT,
    CONF_HEIGHT_WIN,
    CONF_DISTANCE,
    CONF_DEFAULT_HEIGHT,
    CONF_FOV_LEFT,
    CONF_FOV_RIGHT,
    CONF_ENTITIES,
    CONF_HEIGHT_AWNING,
    CONF_LENGTH_AWNING,
    CONF_AWNING_ANGLE,
    CONF_SENSOR_TYPE,
    CONF_INVERSE_STATE,
    CONF_SUNSET_POS,
    CONF_SUNSET_OFFSET,
    CONF_TILT_DEPTH,
    CONF_TILT_DISTANCE,
    CONF_TILT_MODE,
    CONF_TEMP_ENTITY,
    CONF_PRESENCE_ENTITY,
    CONF_TEMP_LOW,
    CONF_TEMP_HIGH,
    CONF_MODE,
    STRATEGY_MODES,
    SensorType,
)

DEFAULT_NAME = "Adaptive Cover"

SENSOR_TYPE_MENU = [SensorType.BLIND, SensorType.AWNING, SensorType.TILT]


CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional("name", default=DEFAULT_NAME): selector.TextSelector(),
        vol.Optional(CONF_BLUEPRINT, default=False): bool,
        vol.Optional(CONF_MODE, default="basic"): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=STRATEGY_MODES, translation_key="mode"
            )
        ),
    }
)

OPTIONS = vol.Schema(
    {
        vol.Required(CONF_AZIMUTH, default=180): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=359, mode="slider")
        ),
        vol.Required(CONF_DEFAULT_HEIGHT, default=60): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, max=100, step=1, mode="slider")
        ),
        vol.Required(CONF_FOV_LEFT, default=90): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=90, step=1, mode="slider")
        ),
        vol.Required(CONF_FOV_RIGHT, default=90): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=90, step=1, mode="slider")
        ),
        vol.Required(CONF_SUNSET_POS, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode="slider")
        ),
        vol.Required(CONF_SUNSET_OFFSET, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(mode="box")
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
            selector.NumberSelectorConfig(min=0, max=6, step=0.01, mode="slider")
        ),
        vol.Required(CONF_DISTANCE, default=0.5): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0.1, max=2, step=0.1, mode="slider")
        ),
    }
).extend(OPTIONS.schema)

HORIZONTAL_OPTIONS = vol.Schema(
    {
        vol.Required(CONF_HEIGHT_AWNING, default=2.1): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=6, step=0.01, mode="slider")
        ),
        vol.Required(CONF_LENGTH_AWNING, default=2.1): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=6, step=0.01, mode="slider")
        ),
        vol.Required(CONF_AWNING_ANGLE, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=45, mode="slider")
        ),
        vol.Required(CONF_DISTANCE, default=0.5): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0.1, max=2, step=0.1, mode="slider")
        ),
    }
).extend(VERTICAL_OPTIONS.schema)

TILT_OPTIONS = vol.Schema(
    {
        vol.Required(CONF_TILT_DEPTH, default=3): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=15, step=0.1, mode="slider")
        ),
        vol.Required(CONF_TILT_DISTANCE, default=2): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=15, step=0.1, mode="slider")
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
        vol.Required(CONF_TEMP_ENTITY, default=[]): selector.EntitySelector(
            selector.EntityFilterSelectorConfig(domain=["climate", "sensor"])
        ),
        vol.Required(CONF_TEMP_LOW, default=21): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=86, step=1, mode="slider")
        ),
        vol.Required(CONF_TEMP_HIGH, default=25): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=90, step=1, mode="slider")
        ),
        vol.Optional(CONF_PRESENCE_ENTITY, default=[]): selector.EntitySelector(
            selector.EntityFilterSelectorConfig(
                domain=["device_tracker", "zone", "binary_sensor","input_boolean"]
            )
        ),
    }
)


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle ConfigFlow."""

    def __init__(self) -> None:  # noqa: D107
        super().__init__()
        self._type_blind: str | None = None
        self._config: dict[str, Any] = {}
        self._mode: str = "basic"

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        # errors = {}
        user_input = user_input or {}
        if user_input:
            self._config = user_input
            return self.async_show_menu(step_id="user", menu_options=SENSOR_TYPE_MENU)
        return self.async_show_form(step_id="user", data_schema=CONFIG_SCHEMA)

    async def async_step_cover_blind(self, user_input):
        """Show config for vertical blinds."""
        self._type_blind = SensorType.BLIND
        self._mode = self._config[CONF_MODE]
        schema = VERTICAL_OPTIONS
        if self._mode == "climate":
            schema = VERTICAL_OPTIONS.extend(CLIMATE_OPTIONS.schema)
        return self.async_show_form(step_id="vertical", data_schema=schema)

    async def async_step_vertical(self, user_input):
        """Create entry."""
        return self.async_create_entry(
            title=f"Adaptive Cover {self._config['name'] if self._config['name'] != 'Adaptive Cover' else ''} Vertical",
            data={
                "name": self._config["name"],
                CONF_BLUEPRINT: self._config[CONF_BLUEPRINT],
                CONF_SENSOR_TYPE: self._type_blind,
                CONF_MODE: self._mode,
            },
            options={
                CONF_AZIMUTH: user_input[CONF_AZIMUTH],
                CONF_HEIGHT_WIN: user_input[CONF_HEIGHT_WIN],
                CONF_DISTANCE: user_input[CONF_DISTANCE],
                CONF_DEFAULT_HEIGHT: user_input[CONF_DEFAULT_HEIGHT],
                CONF_FOV_LEFT: user_input[CONF_FOV_LEFT],
                CONF_FOV_RIGHT: user_input[CONF_FOV_RIGHT],
                CONF_ENTITIES: user_input[CONF_ENTITIES],
                CONF_INVERSE_STATE: user_input[CONF_INVERSE_STATE],
                CONF_SUNSET_POS: user_input[CONF_SUNSET_POS],
                CONF_SUNSET_OFFSET: user_input[CONF_SUNSET_OFFSET],
                CONF_TEMP_ENTITY: user_input.get(CONF_TEMP_ENTITY, None),
                CONF_PRESENCE_ENTITY: user_input.get(CONF_PRESENCE_ENTITY, None),
                CONF_TEMP_LOW: user_input.get(CONF_TEMP_LOW, None),
                CONF_TEMP_HIGH: user_input.get(CONF_TEMP_HIGH, None),
            },
        )

    async def async_step_cover_awning(self, user_input):
        """Show config for horizontal blinds."""
        self._type_blind = SensorType.AWNING
        self._mode = self._config[CONF_MODE]
        schema = HORIZONTAL_OPTIONS
        if self._mode == "climate":
            schema = HORIZONTAL_OPTIONS.extend(CLIMATE_OPTIONS.schema)
        return self.async_show_form(step_id="horizontal", data_schema=schema)

    async def async_step_horizontal(self, user_input):
        """Create entry."""
        return self.async_create_entry(
            title=f"Adaptive Cover {self._config['name'] if self._config['name'] != 'Adaptive Cover' else ''} Horizontal",
            data={
                "name": self._config["name"],
                CONF_BLUEPRINT: self._config[CONF_BLUEPRINT],
                CONF_SENSOR_TYPE: self._type_blind,
                CONF_MODE: self._mode,
            },
            options={
                CONF_AZIMUTH: user_input[CONF_AZIMUTH],
                CONF_HEIGHT_WIN: user_input[CONF_HEIGHT_AWNING],
                CONF_LENGTH_AWNING: user_input[CONF_LENGTH_AWNING],
                CONF_DISTANCE: user_input[CONF_DISTANCE],
                CONF_DEFAULT_HEIGHT: user_input[CONF_DEFAULT_HEIGHT],
                CONF_FOV_LEFT: user_input[CONF_FOV_LEFT],
                CONF_FOV_RIGHT: user_input[CONF_FOV_RIGHT],
                CONF_ENTITIES: user_input[CONF_ENTITIES],
                CONF_AWNING_ANGLE: user_input[CONF_AWNING_ANGLE],
                CONF_INVERSE_STATE: user_input[CONF_INVERSE_STATE],
                CONF_SUNSET_POS: user_input[CONF_SUNSET_POS],
                CONF_SUNSET_OFFSET: user_input[CONF_SUNSET_OFFSET],
                CONF_TEMP_ENTITY: user_input.get(CONF_TEMP_ENTITY, None),
                CONF_PRESENCE_ENTITY: user_input.get(CONF_PRESENCE_ENTITY, None),
                CONF_TEMP_LOW: user_input.get(CONF_TEMP_LOW, None),
                CONF_TEMP_HIGH: user_input.get(CONF_TEMP_HIGH, None),
            },
        )

    async def async_step_cover_tilt(self, user_input):
        """Show config for tilted blinds."""
        self._type_blind = SensorType.TILT
        self._mode = self._config[CONF_MODE]
        schema = TILT_OPTIONS
        if self._mode == "climate":
            schema = TILT_OPTIONS.extend(CLIMATE_OPTIONS.schema)
        return self.async_show_form(step_id="tilt", data_schema=schema)

    async def async_step_tilt(self, user_input):
        """Create entry."""
        return self.async_create_entry(
            title=f"Adaptive Cover {self._config['name'] if self._config['name'] != 'Adaptive Cover' else ''} Tilt",
            data={
                "name": self._config["name"],
                CONF_BLUEPRINT: self._config[CONF_BLUEPRINT],
                CONF_SENSOR_TYPE: self._type_blind,
                CONF_MODE: self._mode,
            },
            options={
                CONF_AZIMUTH: user_input[CONF_AZIMUTH],
                CONF_TILT_DEPTH: user_input[CONF_TILT_DEPTH],
                CONF_TILT_DISTANCE: user_input[CONF_TILT_DISTANCE],
                CONF_TILT_MODE: user_input[CONF_TILT_MODE],
                CONF_DEFAULT_HEIGHT: user_input[CONF_DEFAULT_HEIGHT],
                CONF_FOV_LEFT: user_input[CONF_FOV_LEFT],
                CONF_FOV_RIGHT: user_input[CONF_FOV_RIGHT],
                CONF_ENTITIES: user_input[CONF_ENTITIES],
                CONF_INVERSE_STATE: user_input[CONF_INVERSE_STATE],
                CONF_SUNSET_POS: user_input[CONF_SUNSET_POS],
                CONF_SUNSET_OFFSET: user_input[CONF_SUNSET_OFFSET],
                CONF_TEMP_ENTITY: user_input.get(CONF_TEMP_ENTITY, None),
                CONF_PRESENCE_ENTITY: user_input.get(CONF_PRESENCE_ENTITY, None),
                CONF_TEMP_LOW: user_input.get(CONF_TEMP_LOW, None),
                CONF_TEMP_HIGH: user_input.get(CONF_TEMP_HIGH, None),
            },
        )


class OptionsFlowHandler(OptionsFlowWithConfigEntry):
    """Options to adjust parameters."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__(config_entry)
        self.current_config: dict = dict(config_entry.data)
        self.sensor_type: SensorType = (
            self.current_config.get(CONF_SENSOR_TYPE) or SensorType.BLIND
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        vertical_schema = VERTICAL_OPTIONS
        if self.current_config.get(CONF_MODE) == "climate":
            vertical_schema = VERTICAL_OPTIONS.extend(CLIMATE_OPTIONS.schema)

        horizontal_schema = HORIZONTAL_OPTIONS
        if self.current_config.get(CONF_MODE) == "climate":
            horizontal_schema = HORIZONTAL_OPTIONS.extend(CLIMATE_OPTIONS.schema)

        tilt_schema = TILT_OPTIONS
        if self.current_config.get(CONF_MODE) == "climate":
            tilt_schema = TILT_OPTIONS.extend(CLIMATE_OPTIONS.schema)

        if self.sensor_type == SensorType.BLIND:
            return self.async_show_form(
                step_id="init",
                data_schema=self.add_suggested_values_to_schema(
                    vertical_schema, user_input or self.options
                ),
            )

        if self.sensor_type == SensorType.AWNING:
            return self.async_show_form(
                step_id="init",
                data_schema=self.add_suggested_values_to_schema(
                    horizontal_schema, user_input or self.options
                ),
            )

        if self.sensor_type == SensorType.TILT:
            return self.async_show_form(
                step_id="init",
                data_schema=self.add_suggested_values_to_schema(
                    tilt_schema, user_input or self.options
                ),
            )
