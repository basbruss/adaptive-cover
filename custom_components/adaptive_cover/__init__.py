"""The Adaptive Cover integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_state_change_event,
)

from .const import (
    CONF_END_ENTITY,
    CONF_END_TIME,
    CONF_ENTITIES,
    CONF_PRESENCE_ENTITY,
    CONF_RETURN_SUNSET,
    CONF_TEMP_ENTITY,
    CONF_WEATHER_ENTITY,
    DOMAIN,
)
from .coordinator import AdaptiveDataUpdateCoordinator
from .helpers import get_datetime_from_str

PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.BINARY_SENSOR, Platform.BUTTON]
CONF_SUN = ["sun.sun"]


async def async_initialize_integration(
    hass: HomeAssistant,
    config_entry: ConfigEntry | None = None,
) -> bool:
    """Initialize the integration."""

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Adaptive Cover from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    coordinator = AdaptiveDataUpdateCoordinator(hass)
    end_time=None
    _temp_entity = entry.options.get(CONF_TEMP_ENTITY)
    _presence_entity = entry.options.get(CONF_PRESENCE_ENTITY)
    _weather_entity = entry.options.get(CONF_WEATHER_ENTITY)
    _cover_entities = entry.options.get(CONF_ENTITIES, [])
    _entities = ["sun.sun"]
    for entity in [_temp_entity, _presence_entity, _weather_entity]:
        if entity is not None:
            _entities.append(entity)
    _track_end_time = entry.options.get(CONF_RETURN_SUNSET)
    _end_time = entry.options.get(CONF_END_TIME)
    _end_time_entity = entry.options.get(CONF_END_ENTITY)
    if _end_time is not None:
        end_time = get_datetime_from_str(_end_time)
    if _end_time_entity is not None:
        end_time = get_datetime_from_str(_end_time_entity)

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

    if _track_end_time and end_time is not None:
        entry.async_on_unload(
            async_track_point_in_time(hass, coordinator.async_timed_refresh, end_time)
        )

    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
