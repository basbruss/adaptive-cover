"""The Adaptive Cover integration."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import (
    async_track_state_change_event,
)

from .const import (
    ALL_BLINDS_TITLE,
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
    LOGGER,
)
from .coordinator import AdaptiveDataUpdateCoordinator

# Internal data keys (prefixed with ``_`` so ``_iter_coordinators`` skips them).
_HUB_BOOTSTRAPPED = "_hub_bootstrapped"
_V18_CLEANUP_DONE = "_v18_cleanup_done"

# Identifier used by the v1.8.0 leftover singleton device. We remove any device
# carrying this identifier on first setup of v1.8.2+ — it's a one-shot
# migration that becomes a no-op once cleaned.
_V18_LEFTOVER_IDENTIFIER = (DOMAIN, "all_covers")

# Full platform list — used by regular per-cover config entries.
PLATFORMS = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.COVER,
]

# Platforms used by the singleton "All Blinds" hub entry:
#   - cover  : aggregate "Tous les volets" — Alexa "ouvre / ferme les volets"
#   - switch : "Les volets" ON/OFF        — Alexa "active / désactive les volets"
#   - select : 4-state UI dropdown        — HA dashboard
#   - scene  : "Volets ouverts/fermés"    — automations / shortcuts
HUB_PLATFORMS = [Platform.COVER, Platform.SWITCH, Platform.SELECT, Platform.SCENE]

CONF_SUN = ["sun.sun"]


async def async_initialize_integration(
    hass: HomeAssistant,
    config_entry: ConfigEntry | None = None,
) -> bool:
    """Initialize the integration."""

    return True


def _cleanup_v18_leftover_device(hass: HomeAssistant) -> None:
    """One-shot migration: remove the orphan device left behind by v1.8.0.

    v1.8.0 created an implicit aggregate device with identifier
    ``(DOMAIN, "all_covers")`` attached to whichever config entry first
    finished its platform setup. v1.8.1+ doesn't reference that identifier
    anymore, but HA's device registry keeps the record until something
    explicitly removes it — which is what we do here.

    Safe and idempotent: if the device doesn't exist, this is a no-op.
    """
    dev_reg = dr.async_get(hass)
    leftover = dev_reg.async_get_device(identifiers={_V18_LEFTOVER_IDENTIFIER})
    if leftover is not None:
        LOGGER.info(
            "Removing v1.8.0 leftover 'All Blinds' device (%s)", leftover.id
        )
        dev_reg.async_remove_device(leftover.id)


def _hub_entry_exists(hass: HomeAssistant) -> bool:
    """Return True if any config entry is marked as the All-Blinds hub."""
    return any(
        e.data.get(CONF_IS_HUB) for e in hass.config_entries.async_entries(DOMAIN)
    )


async def _async_bootstrap_hub_entry(hass: HomeAssistant) -> None:
    """Auto-create the singleton hub entry if it doesn't exist yet.

    Triggered once per HA boot (guarded by ``_HUB_BOOTSTRAPPED``). Uses the
    import flow source so the user doesn't see a popup.
    """
    if _hub_entry_exists(hass):
        return
    LOGGER.info("Bootstrapping the 'All Blinds' hub config entry")
    await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data={CONF_IS_HUB: True},
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Adaptive Cover from a config entry.

    Hub entries (the singleton "All Blinds" aggregator, identified by
    ``entry.data["is_hub"] is True``) skip coordinator creation and only
    forward to the ``cover`` platform. Regular entries follow the full
    setup path.

    On the first ``async_setup_entry`` call after upgrade we also:
      - remove the v1.8.0 leftover device (one-shot migration);
      - auto-create the hub entry if none exists yet.
    """

    data = hass.data.setdefault(DOMAIN, {})

    # One-shot migration of v1.8.0 leftovers (runs once per HA boot).
    if not data.get(_V18_CLEANUP_DONE):
        data[_V18_CLEANUP_DONE] = True
        _cleanup_v18_leftover_device(hass)

    # Auto-create the hub entry on first non-hub setup (one-shot per HA boot).
    if not entry.data.get(CONF_IS_HUB) and not data.get(_HUB_BOOTSTRAPPED):
        data[_HUB_BOOTSTRAPPED] = True
        hass.async_create_task(_async_bootstrap_hub_entry(hass))

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
