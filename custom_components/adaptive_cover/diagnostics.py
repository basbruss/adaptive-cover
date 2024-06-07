"""Adaptive Cover integration diagnostics."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
):
    """Return config entry diagnostics."""
    return {
        "title": "Adaptive Cover Configuration",
        "type": "config_entry",
        "identifier": config_entry.entry_id,
        "config_data": config_entry.data,
        "config_options": config_entry.options,
    }
