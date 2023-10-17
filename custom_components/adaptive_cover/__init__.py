"""The Adaptive Cover integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .blueprint import configure_blueprint
from .const import DOMAIN


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

    await hass.config_entries.async_forward_entry_setups(entry, (Platform.SENSOR,))

    await async_initialize_integration(hass=hass, config_entry=entry)
    return True


async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)
    await async_initialize_integration(hass=hass, config_entry=entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        entry, (Platform.SENSOR,)
    ):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
