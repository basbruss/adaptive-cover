"""Scene platform for the Adaptive Cover integration — hub position shortcuts.

Two scenes are exposed on the "All Blinds" hub device:

  all_open   — every cover moves to 100 % (manual override activated).
  all_closed — every cover moves to 0 %   (manual override activated).

These scenes are primarily useful for HA automations and shortcuts.
For Alexa voice control of open / close, the aggregate cover entity
``cover.tous_les_volets`` already handles "Alexa, ouvre / ferme les volets"
natively without needing these scenes.

Adaptive control ON/OFF is handled by the hub switch entity (see switch.py)
which Alexa understands as "active / désactive les volets".
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
    """Register position scenes — only for hub entries."""
    if not config_entry.data.get(CONF_IS_HUB):
        return

    device_info = DeviceInfo(
        identifiers={(DOMAIN, config_entry.entry_id)},
        name="All Blinds",
        manufacturer="Adaptive Cover",
    )

    async_add_entities(
        [
            AdaptiveCoverScene(hass, config_entry, "all_open", device_info),
            AdaptiveCoverScene(hass, config_entry, "all_closed", device_info),
        ]
    )


class AdaptiveCoverScene(Scene):
    """Position shortcut scene on the All Blinds hub device.

    ``all_open``   → every cover to 100 %, manual override activated.
    ``all_closed`` → every cover to 0 %,   manual override activated.
    """

    _attr_has_entity_name = False  # full name set directly — no device prefix in Alexa

    _NAMES = {
        "all_open":   "Volets ouverts",   # Alexa: "allume Volets ouverts"
        "all_closed": "Volets fermés",    # Alexa: "allume Volets fermés"
    }

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        mode: str,
        device_info: DeviceInfo,
    ) -> None:
        """Initialise the scene for *mode* (``all_open`` / ``all_closed``)."""
        self.hass = hass
        self._mode = mode
        self._attr_name = self._NAMES[mode]
        self._attr_unique_id = f"{config_entry.entry_id}_scene_{mode}"
        self._attr_device_info = device_info

    async def async_activate(self, **kwargs) -> None:
        """Move all covers to the target position."""
        position = 100 if self._mode == "all_open" else 0
        LOGGER.debug("AdaptiveCoverScene: activating '%s' → %d%%", self._mode, position)
        for coord in iter_regular_coordinators(self.hass):
            for entity_id in getattr(coord, "entities", None) or ():
                await coord.async_set_position(entity_id, position)
            await coord.async_refresh()
