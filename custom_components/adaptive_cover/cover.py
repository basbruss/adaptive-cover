"""Global cover entity aggregating all Adaptive Cover config entries."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    STATE_CLOSED,
    STATE_OPEN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ENTITIES, CONF_SENSOR_TYPE, DOMAIN, LOGGER

COVER_DOMAIN = "cover"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the global cover entity for this config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [AdaptiveCoverGlobal(hass, config_entry, coordinator)],
        update_before_add=True,
    )


class AdaptiveCoverGlobal(CoverEntity):
    """A single cover entity that controls all covers of this config entry.

    Actions:
    - open_cover  → marks all covers as manual + opens them fully
    - close_cover → marks all covers as manual + closes them fully
    - stop_cover  → (no-op, required by HA)
    - turn_on     → enables adaptive control (control_toggle = True)
    - turn_off    → disables adaptive control (control_toggle = False)
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

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, coordinator) -> None:
        """Initialize the global cover entity."""
        self.hass = hass
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._name = config_entry.data.get("name", "Adaptive Cover")

        cover_type = config_entry.data.get(CONF_SENSOR_TYPE, "cover_blind")
        type_label = {
            "cover_blind": "Vertical",
            "cover_awning": "Horizontal",
            "cover_tilt": "Tilt",
        }.get(cover_type, "Cover")

        self._attr_unique_id = f"{config_entry.entry_id}_global_cover"
        self._attr_name = f"Tous les volets – {self._name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=type_label,
        )

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def is_closed(self) -> bool | None:
        """Return True if all covers are closed."""
        covers = self._coordinator.entities
        if not covers:
            return None
        positions = []
        for entity_id in covers:
            state = self.hass.states.get(entity_id)
            if state is None:
                continue
            pos = state.attributes.get("current_position")
            if pos is not None:
                positions.append(int(pos))
        if not positions:
            return None
        return all(p == 0 for p in positions)

    @property
    def current_cover_position(self) -> int | None:
        """Return the average position of all covers (0-100)."""
        covers = self._coordinator.entities
        if not covers:
            return None
        positions = []
        for entity_id in covers:
            state = self.hass.states.get(entity_id)
            if state is None:
                continue
            pos = state.attributes.get("current_position")
            if pos is not None:
                positions.append(int(pos))
        if not positions:
            return None
        return round(sum(positions) / len(positions))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose whether adaptive control is active."""
        return {
            "adaptive_control": self._coordinator.control_toggle,
            "manual_override": self._coordinator.manager.binary_cover_manual,
            "covers": self._coordinator.entities,
        }

    # ------------------------------------------------------------------
    # Actions – open / close  (set manual override then move)
    # ------------------------------------------------------------------

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Mark all covers as manual and open them fully."""
        LOGGER.debug("Global cover: open requested")
        await self._move_all(100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Mark all covers as manual and close them fully."""
        LOGGER.debug("Global cover: close requested")
        await self._move_all(0)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Set all covers to a specific position (manual)."""
        position = kwargs.get(ATTR_POSITION, 100)
        LOGGER.debug("Global cover: set position %s", position)
        await self._move_all(position)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop is a no-op – individual covers handle their own stop."""

    async def _move_all(self, position: int) -> None:
        """Move all covers to *position* and flag them as manual."""
        covers = self._coordinator.entities
        for entity_id in covers:
            # Mark as manual so adaptive cover won't override immediately
            self._coordinator.manager.mark_manual_control(entity_id)
            await self._coordinator.async_set_manual_position(entity_id, position)
        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Actions – enable / disable adaptive control
    # ------------------------------------------------------------------

    async def async_enable_adaptive(self) -> None:
        """Enable adaptive control for this entry (control_toggle = True)."""
        LOGGER.debug("Global cover: enabling adaptive control")
        self._coordinator.control_toggle = True
        # reset manual flags so adaptive takes over immediately
        for entity_id in self._coordinator.entities:
            self._coordinator.manager.reset(entity_id)
        await self._coordinator.async_refresh()
        self.async_write_ha_state()

    async def async_disable_adaptive(self) -> None:
        """Disable adaptive control for this entry (control_toggle = False)."""
        LOGGER.debug("Global cover: disabling adaptive control")
        self._coordinator.control_toggle = False
        await self._coordinator.async_refresh()
        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # HA service: cover.turn_on / cover.turn_off → adaptive on/off
    # ------------------------------------------------------------------

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable adaptive control."""
        await self.async_enable_adaptive()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable adaptive control."""
        await self.async_disable_adaptive()
