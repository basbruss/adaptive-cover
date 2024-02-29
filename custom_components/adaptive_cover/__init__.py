"""The Adaptive Cover integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import (
    async_track_entity_registry_updated_event,
    async_track_state_change,
)

from .const import DOMAIN
from .blueprint import configure_blueprint
from .coordinator import AdaptiveDataUpdateCoordinator

PLATFORMS = [Platform.SENSOR,Platform.SWITCH]
CONF_ENTITIES = ["sun.sun"]

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

    hass.data.setdefault(DOMAIN, {})

    coordinator = AdaptiveDataUpdateCoordinator(hass)

    entry.async_on_unload(
        async_track_state_change(
            hass,
            CONF_ENTITIES,
            coordinator.async_check_entity_state_change,
        )
    )

    # # entry.async_on_unload(
    # #     async_track_entity_registry_updated_event(
    # #         hass,
    # #         CONF_ENTITIES,
    # #         coordinator.async_check_entity_state_change,
    # #     )
    # )

    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


# async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#     """Set up Adaptive Cover from a config entry."""

#     coordinator = AdaptiveDataUpdateCoordinator(hass)
#     await coordinator.async_config_entry_first_refresh()

#     hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

#     await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # await async_initialize_integration(hass=hass, config_entry=entry)

    # entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))

#     return True


# async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
#     """Update listener, called when the config entry options are changed."""
#     await hass.config_entries.async_reload(entry.entry_id)


# async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#     """Unload a config entry."""
#     if unload_ok := await hass.config_entries.async_unload_platforms(
#         entry, (Platform.SENSOR,Platform.SWITCH)
#     ):
#         return unload_ok
