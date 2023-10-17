"""Config flow for Adaptive Cover integration."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import voluptuous as vol

from homeassistant.components.sensor import DOMAIN
from homeassistant.helpers import selector
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import callback
from homeassistant.core import HomeAssistant
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
    SensorType,
)

DEFAULT_NAME = "Adaptive Cover"

SENSOR_TYPE_MENU = [
    SensorType.BLIND,
    SensorType.AWNING,
    SensorType.TILT
    ]


CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required("name", default=DEFAULT_NAME): selector.TextSelector(),
        vol.Required(CONF_BLUEPRINT, default=False): bool,
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
        vol.Required(CONF_TILT_MODE, default='mode2'): selector.SelectSelector(
            selector.SelectSelectorConfig(options=['mode1','mode2'], translation_key='tilt_mode')
        )
    }
).extend(OPTIONS.schema)

CONFIG_VERTICAL = CONFIG_SCHEMA.extend(VERTICAL_OPTIONS.schema)
CONFIG_HORIZONTAL = CONFIG_SCHEMA.extend(HORIZONTAL_OPTIONS.schema)
CONFIG_TILT = CONFIG_SCHEMA.extend(TILT_OPTIONS.schema)


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle ConfigFlow."""

    def __init__(self) -> None:
        super().__init__()
        self.type_blind: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Show menu to decide type."""
        return self.async_show_menu(step_id="user", menu_options=SENSOR_TYPE_MENU)

    async def async_step_cover_blind(self, user_input):
        """Show config for vertical blinds."""
        self.type_blind = SensorType.BLIND
        return self.async_show_form(step_id="vertical", data_schema=CONFIG_VERTICAL)

    async def async_step_vertical(self, user_input):
        """Create entry."""
        return self.async_create_entry(
            title=f"Adaptive Cover {user_input['name']} Vertical",
            data={
                "name": user_input["name"],
                CONF_BLUEPRINT: user_input[CONF_BLUEPRINT],
                CONF_SENSOR_TYPE: self.type_blind,
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
            },
        )

    async def async_step_cover_awning(self, user_input):
        """Show config for horizontal blinds."""
        self.type_blind = SensorType.AWNING
        return self.async_show_form(step_id="horizontal", data_schema=CONFIG_HORIZONTAL)

    async def async_step_horizontal(self, user_input):
        """Create entry."""
        return self.async_create_entry(
            title=f"Adaptive Cover {user_input['name']} Horizontal",
            data={
                "name": user_input["name"],
                CONF_BLUEPRINT: user_input[CONF_BLUEPRINT],
                CONF_SENSOR_TYPE: self.type_blind,
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
            },
        )

    async def async_step_cover_tilt(self,user_input):
        """Show config for tilted blinds"""
        self.type_blind = SensorType.TILT
        return self.async_show_form(step_id="tilt", data_schema=CONFIG_TILT)

    async def async_step_tilt(self, user_input):
        """Create entry."""
        return self.async_create_entry(
            title=f"Adaptive Cover {user_input['name']} Tilt",
            data={
                "name": user_input["name"],
                CONF_BLUEPRINT: user_input[CONF_BLUEPRINT],
                CONF_SENSOR_TYPE: self.type_blind,
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

        if self.sensor_type == SensorType.BLIND:
            return self.async_show_form(
                step_id="init",
                data_schema=self.add_suggested_values_to_schema(
                    VERTICAL_OPTIONS, user_input or self.options
                ),
            )

        if self.sensor_type == SensorType.AWNING:
            return self.async_show_form(
                step_id="init",
                data_schema=self.add_suggested_values_to_schema(
                    HORIZONTAL_OPTIONS, user_input or self.options
                ),
            )

        if self.sensor_type == SensorType.TILT:
            return self.async_show_form(
                step_id="init",
                data_schema=self.add_suggested_values_to_schema(
                    TILT_OPTIONS, user_input or self.options
                ),
            )