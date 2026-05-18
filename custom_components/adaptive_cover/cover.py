"""Aggregate cover entity for the singleton 'All Blinds' hub config entry.

The Adaptive Cover integration uses TWO kinds of config entries:

  * **Regular entries** — one per cover group (Vertical / Horizontal / Tilt).
    These expose all the usual sensors, switches, buttons and per-entry
    diagnostics. The ``cover`` platform is a no-op for these entries.

  * **Hub entry** — a single singleton entry (marked ``entry.data['is_hub']``)
    that exposes ONE aggregate ``cover.*`` entity. This entity controls every
    cover declared in every regular entry: open / close / set position, plus
    ``turn_on`` / ``turn_off`` to globally enable or disable adaptive control.

The hub entry is created from the integration's config flow via the
"All Blinds" menu option and behaves like any other config entry — it can be
removed, renamed, or recreated independently.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_IS_HUB, DOMAIN, LOGGER


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register the aggregate cover entity, but only for the hub entry.

    Regular per-cover entries don't register anything on the ``cover``
    platform — they only expose sensors / switches / etc.
    """
    if not config_entry.data.get(CONF_IS_HUB):
        return
    async_add_entities([AdaptiveCoverAll(hass, config_entry)], update_before_add=True)


def _iter_coordinators(hass: HomeAssistant):
    """Yield every Adaptive Cover coordinator currently loaded.

    Skips:
      - internal bookkeeping keys (anything starting with ``_``)
      - hub entries (no coordinator stored, but defensive in case the layout
        ever changes)
    """
    for key, value in hass.data.get(DOMAIN, {}).items():
        if isinstance(key, str) and key.startswith("_"):
            continue
        # value is the coordinator for regular entries; hub entries never
        # store anything under their entry_id (see __init__.async_setup_entry).
        if value is None:
            continue
        yield value


class AdaptiveCoverAll(CoverEntity):
    """Aggregate cover entity controlling every Adaptive Cover regular entry.

    Behaviour:
      - ``open_cover`` / ``close_cover`` / ``set_cover_position``
            → moves every cover (across all entries) and flags each as manual.
      - ``stop_cover`` → no-op (individual covers handle their own stop).
      - ``turn_on`` → enables adaptive control on every entry, clears manual flags.
      - ``turn_off`` → disables adaptive control on every entry.
      - ``is_closed`` → True when every known cover is at 0 %.
      - ``current_cover_position`` → average position across all covers.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_device_class = CoverDeviceClass.BLIND
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )
    _attr_name = "Tous les volets"

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Tie this entity to the hub config entry's own device."""
        self.hass = hass
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_all_blinds"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name="All Blinds",
            manufacturer="Adaptive Cover",
        )

    # ------------------------------------------------------------------
    # Internal helpers — single pass over hass.states, no recomputation.
    # ------------------------------------------------------------------

    def _all_cover_ids(self) -> list[str]:
        """Return the deduplicated list of cover entity_ids across all entries."""
        seen: set[str] = set()
        ordered: list[str] = []
        for coord in _iter_coordinators(self.hass):
            for entity_id in getattr(coord, "entities", None) or ():
                if entity_id in seen:
                    continue
                seen.add(entity_id)
                ordered.append(entity_id)
        return ordered

    def _collect_positions(self) -> list[int]:
        """One ``hass.states.get`` per cover; skip missing / non-int values."""
        states = self.hass.states  # local alias avoids repeated attr lookups
        positions: list[int] = []
        for entity_id in self._all_cover_ids():
            state = states.get(entity_id)
            if state is None:
                continue
            pos = state.attributes.get("current_position")
            if pos is None:
                continue
            try:
                positions.append(int(pos))
            except (TypeError, ValueError):
                continue
        return positions

    # ------------------------------------------------------------------
    # State properties
    # ------------------------------------------------------------------

    @property
    def is_closed(self) -> bool | None:
        """True when every known cover is fully closed (position == 0)."""
        positions = self._collect_positions()
        if not positions:
            return None
        return all(p == 0 for p in positions)

    @property
    def current_cover_position(self) -> int | None:
        """Average position across every cover (0-100)."""
        positions = self._collect_positions()
        if not positions:
            return None
        return round(sum(positions) / len(positions))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose aggregated adaptive-control state."""
        coords = list(_iter_coordinators(self.hass))
        if not coords:
            return {
                "adaptive_control": False,
                "manual_override": False,
                "covers": [],
                "config_entries": 0,
            }
        adaptive = all(getattr(c, "control_toggle", False) for c in coords)
        any_manual = any(
            getattr(getattr(c, "manager", None), "binary_cover_manual", False)
            for c in coords
        )
        return {
            "adaptive_control": adaptive,
            "manual_override": any_manual,
            "covers": self._all_cover_ids(),
            "config_entries": len(coords),
        }

    # ------------------------------------------------------------------
    # Movement actions
    # ------------------------------------------------------------------

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Mark every cover as manual and open fully."""
        LOGGER.debug("AdaptiveCoverAll: open requested")
        await self._move_all(100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Mark every cover as manual and close fully."""
        LOGGER.debug("AdaptiveCoverAll: close requested")
        await self._move_all(0)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move every cover to a specific position (manual)."""
        position = int(kwargs.get(ATTR_POSITION, 100))
        LOGGER.debug("AdaptiveCoverAll: set position %s", position)
        await self._move_all(position)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """No-op — individual covers handle their own stop."""

    async def _move_all(self, position: int) -> None:
        """Mark every cover as manual then move it to ``position``."""
        for coord in _iter_coordinators(self.hass):
            manager = getattr(coord, "manager", None)
            entities = getattr(coord, "entities", None) or ()
            for entity_id in entities:
                if manager is not None:
                    manager.mark_manual_control(entity_id)
                await coord.async_set_manual_position(entity_id, position)
        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Adaptive control toggle (cover.turn_on / cover.turn_off)
    # ------------------------------------------------------------------

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable adaptive control on every entry; clear manual flags."""
        LOGGER.debug("AdaptiveCoverAll: enabling adaptive control")
        for coord in _iter_coordinators(self.hass):
            coord.control_toggle = True
            manager = getattr(coord, "manager", None)
            if manager is not None:
                for entity_id in getattr(coord, "entities", None) or ():
                    manager.reset(entity_id)
            await coord.async_refresh()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable adaptive control on every entry."""
        LOGGER.debug("AdaptiveCoverAll: disabling adaptive control")
        for coord in _iter_coordinators(self.hass):
            coord.control_toggle = False
            await coord.async_refresh()
        self.async_write_ha_state()
