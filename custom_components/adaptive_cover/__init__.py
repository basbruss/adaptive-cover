"""The Adaptive Cover integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .blueprint import configure_blueprint


async def async_initialize_integration(
    hass: HomeAssistant,
    # *,
    config_entry: ConfigEntry | None = None,
    # config: dict[str, Any] | None = None,
) -> bool:
    """Initialize the integration."""

    configure_blueprint(hass=hass, config_entry=config_entry)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Adaptive Cover from a config entry."""

    await hass.config_entries.async_forward_entry_setups(entry, (Platform.SENSOR,Platform.SWITCH))

    await async_initialize_integration(hass=hass, config_entry=entry)

    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))

    return True


async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        entry, (Platform.SENSOR,Platform.SWITCH)
    ):
        return unload_ok
