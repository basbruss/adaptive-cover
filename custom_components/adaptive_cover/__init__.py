"""The Adaptive Cover integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import (
    async_track_state_change_event,
)

from .const import (
    CONF_END_ENTITY,
    CONF_ENTITIES,
    CONF_IRRADIANCE_ENTITY,
    CONF_IS_HUB,
    CONF_LUX_ENTITY,
    CONF_OUTSIDETEMP_ENTITY,
    CONF_PRESENCE_ENTITY,
    CONF_START_ENTITY,
    CONF_TEMP_ENTITY,
    CONF_WEATHER_ENTITY,
    DOMAIN,
)
from .coordinator import AdaptiveDataUpdateCoordinator

# Full platform list — used by regular per-cover config entries.
PLATFORMS = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.COVER,
]

# Platforms used by the singleton "All Blinds" hub entry: only the aggregate
# cover entity. No sensors / switches / button etc. for the hub.
HUB_PLATFORMS = [Platform.COVER]

CONF_SUN = ["sun.sun"]


async def async_initialize_integration(
    hass: HomeAssistant,
    config_entry: ConfigEntry | None = None,
) -> bool:
    """Initialize the integration."""

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Adaptive Cover from a config entry.

    Hub entries (the singleton "All Blinds" aggregator, identified by
    ``entry.data["is_hub"] is True``) skip coordinator creation and only
    forward to the ``cover`` platform. Regular entries follow the full
    setup path.
    """

    hass.data.setdefault(DOMAIN, {})

    # Hub entry — no coordinator, no listeners, only the singleton cover entity.
    if entry.data.get(CONF_IS_HUB):
        await hass.config_entries.async_forward_entry_setups(entry, HUB_PLATFORMS)
        entry.async_on_unload(entry.add_update_listener(_async_update_listener))
        return True

    coordinator = AdaptiveDataUpdateCoordinator(hass)
    _temp_entity = entry.options.get(CONF_TEMP_ENTITY)
    _presence_entity = entry.options.get(CONF_PRESENCE_ENTITY)
    _weather_entity = entry.options.get(CONF_WEATHER_ENTITY)
    _cover_entities = entry.options.get(CONF_ENTITIES, [])
    _end_time_entity = entry.options.get(CONF_END_ENTITY)
    _lux_entity = entry.options.get(CONF_LUX_ENTITY)
    _irradiance_entity = entry.options.get(CONF_IRRADIANCE_ENTITY)
    _outside_temp_entity = entry.options.get(CONF_OUTSIDETEMP_ENTITY)
    _start_time_entity = entry.options.get(CONF_START_ENTITY)
    _entities = ["sun.sun"]
    for entity in [
        _temp_entity,
        _presence_entity,
        _weather_entity,
        _end_time_entity,
        _lux_entity,
        _irradiance_entity,
        _outside_temp_entity,
        _start_time_entity,
    ]:
        if entity is not None:
            _entities.append(entity)

    entry.async_on_unload(
        async_track_state_change_event(
            hass,
            _entities,
            coordinator.async_check_entity_state_change,
        )
    )

    entry.async_on_unload(
        async_track_state_change_event(
            hass,
            _cover_entities,
            coordinator.async_check_cover_state_change,
        )
    )

    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry — handles both regular and hub entries."""
    platforms = HUB_PLATFORMS if entry.data.get(CONF_IS_HUB) else PLATFORMS
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        # Regular entries store their coordinator under ``entry.entry_id``;
        # hub entries don't (no coordinator). ``pop(..., None)`` covers both.
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
