"""Scene platform for the Adaptive Cover integration — hub shortcuts.

Four scenes are exposed on the "All Blinds" hub device:

  auto       — adaptive positioning ON; manual overrides cleared.
  off        — adaptive positioning OFF; covers stay in place.
  all_open   — every cover moves to 100 %; manual override activated.
  all_closed — every cover moves to 0 %;  manual override activated.

Alexa, Google Assistant and Assist all support scene entities natively,
making voice control straightforward:
  "Alexa, activate Tous fermés"
  "OK Google, activate Tous ouverts"
"""

from __future__ import annotations

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_IS_HUB, DOMAIN, LOGGER
from .helpers import iter_regular_coordinators


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register the four hub scenes — only for hub entries."""
    if not config_entry.data.get(CONF_IS_HUB):
        return

    device_info = DeviceInfo(
        identifiers={(DOMAIN, config_entry.entry_id)},
        name="All Blinds",
        manufacturer="Adaptive Cover",
    )

    async_add_entities(
        [
            AdaptiveCoverScene(hass, config_entry, "auto", device_info),
            AdaptiveCoverScene(hass, config_entry, "off", device_info),
            AdaptiveCoverScene(hass, config_entry, "all_open", device_info),
            AdaptiveCoverScene(hass, config_entry, "all_closed", device_info),
        ]
    )


class AdaptiveCoverScene(Scene):
    """One of the four All-Blinds hub scenes.

    Each scene delegates to the same action helpers used by the select
    entity, keeping behaviour consistent regardless of how the user
    triggers a mode change (UI dropdown or voice / automation scene).
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        mode: str,
        device_info: DeviceInfo,
    ) -> None:
        """Initialise the scene for *mode* (``auto`` / ``off`` / ``all_open`` / ``all_closed``)."""
        self.hass = hass
        self._mode = mode
        self._attr_translation_key = f"scene_{mode}"
        self._attr_unique_id = f"{config_entry.entry_id}_scene_{mode}"
        self._attr_device_info = device_info

    async def async_activate(self, **kwargs) -> None:
        """Activate the scene — apply the corresponding hub action."""
        LOGGER.debug("AdaptiveCoverScene: activating '%s'", self._mode)
        if self._mode == "auto":
            await self._apply_auto()
        elif self._mode == "off":
            await self._apply_off()
        elif self._mode == "all_open":
            await self._apply_position(100)
        elif self._mode == "all_closed":
            await self._apply_position(0)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    async def _apply_auto(self) -> None:
        """Enable adaptive control and clear all manual overrides."""
        for coord in iter_regular_coordinators(self.hass):
            coord.control_toggle = True
            manager = getattr(coord, "manager", None)
            if manager is not None:
                for entity_id in getattr(coord, "entities", None) or ():
                    manager.reset(entity_id)
            await coord.async_refresh()

    async def _apply_off(self) -> None:
        """Disable adaptive control everywhere — covers stay in place."""
        for coord in iter_regular_coordinators(self.hass):
            coord.control_toggle = False
            await coord.async_refresh()

    async def _apply_position(self, position: int) -> None:
        """Set every cover to *position* % and activate manual override."""
        for coord in iter_regular_coordinators(self.hass):
            for entity_id in getattr(coord, "entities", None) or ():
                await coord.async_set_position(entity_id, position)
            await coord.async_refresh()
