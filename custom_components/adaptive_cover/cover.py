"""Singleton global cover aggregating every Adaptive Cover config entry.

A single ``cover.adaptive_cover_all`` entity is registered for the integration
as a whole (not per config entry). It controls every cover declared across
all Adaptive Cover entries in one place.

The previous behaviour created one ``Tous les volets – <name>`` entity per
config entry, which produced redundant aggregates (one per single-cover
entry). This module replaces that with a true integration-level singleton.
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

from .const import DOMAIN, LOGGER

# Internal flag stored in ``hass.data[DOMAIN]`` to ensure the singleton entity
# is registered exactly once across all config entries.
_GLOBAL_FLAG = "_global_cover_added"
_GLOBAL_UNIQUE_ID = f"{DOMAIN}_all_covers"
_GLOBAL_DEVICE_ID = "all_covers"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register the singleton global cover on the first entry setup.

    Subsequent ``async_setup_entry`` calls (for other config entries) skip
    registration. The singleton iterates ``hass.data[DOMAIN]`` at runtime to
    discover all coordinators currently loaded.
    """
    data = hass.data.setdefault(DOMAIN, {})
    if data.get(_GLOBAL_FLAG):
        return  # already registered by an earlier entry
    data[_GLOBAL_FLAG] = True
    async_add_entities([AdaptiveCoverAll(hass)], update_before_add=True)


def _iter_coordinators(hass: HomeAssistant):
    """Yield every Adaptive Cover coordinator currently loaded.

    Skips internal bookkeeping keys (anything starting with ``_``).
    """
    for key, value in hass.data.get(DOMAIN, {}).items():
        if isinstance(key, str) and key.startswith("_"):
            continue
        yield value


class AdaptiveCoverAll(CoverEntity):
    """Aggregate cover entity controlling every Adaptive Cover config entry.

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
    _attr_unique_id = _GLOBAL_UNIQUE_ID
    _attr_name = "Tous les volets"
    _attr_device_info = DeviceInfo(
        identifiers={(DOMAIN, _GLOBAL_DEVICE_ID)},
        name="Adaptive Cover",
        manufacturer="Adaptive Cover",
    )

    def __init__(self, hass: HomeAssistant) -> None:
        """Store hass reference; no per-entry state."""
        self.hass = hass

    # ------------------------------------------------------------------
    # Internal helpers (single pass over hass.states)
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
        states = self.hass.states  # local alias removes attr lookups in loop
        positions: list[int] = []
        for entity_id in self._all_cover_ids():
            state = states.get(entity_id)
            if state is None:
                continue
            pos = state.attributes.get("current_position")
            if pos is not None:
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
        """Expose adaptive-control state aggregated from every entry."""
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
