"""Add blueprint to HomeAssistant."""

from __future__ import annotations

import os
import shutil

from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_BLUEPRINT


def configure_blueprint(hass: HomeAssistant, config_entry):
    """Configure initial blueprint."""
    if config_entry.data[CONF_BLUEPRINT]:
        os.makedirs(hass.config.path(f"blueprints/automation/{DOMAIN}"), exist_ok=True)
        if not os.path.exists(
            hass.config.path(f"blueprints/automation/{DOMAIN}/{DOMAIN}.yaml")
        ):
            shutil.copy(
                hass.config.path(
                    f"custom_components/{DOMAIN}/blueprints/{DOMAIN}.yaml"
                ),
                hass.config.path(f"blueprints/automation/{DOMAIN}/{DOMAIN}.yaml"),
            )
