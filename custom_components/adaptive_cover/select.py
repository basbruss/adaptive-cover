"""Select platform for the Adaptive Cover integration — hub controls."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CONF_IS_HUB, DOMAIN, LOGGER

# The four modes exposed on the All-Blinds hub device.
MODE_AUTO = "auto"
MODE_OFF = "off"
MODE_ALL_OPEN = "all_open"
MODE_ALL_CLOSED = "all_closed"

HUB_SELECT_OPTIONS = [MODE_AUTO, MODE_OFF, MODE_ALL_OPEN, MODE_ALL_CLOSED]


def _iter_regular_coordinators(hass: HomeAssistant):
    """Yield every Adaptive Cover coordinator (regular entries only).

    Skips internal bookkeeping keys (``_*``) and any ``None`` placeholders.
    """
    for key, value in hass.data.get(DOMAIN, {}).items():
        if isinstance(key, str) and key.startswith("_"):
            continue
        if value is None:
            continue
        yield value


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register the hub mode select — only for hub entries."""
    if not config_entry.data.get(CONF_IS_HUB):
        return
    async_add_entities([AdaptiveControlModeSelect(hass, config_entry)])


class AdaptiveControlModeSelect(RestoreEntity, SelectEntity):
    """4-state select on the All Blinds hub device.

    +--------------+------------------------------------------------+
    | auto         | Adaptive positioning ON; manual overrides      |
    |              | cleared on every regular entry.                |
    +--------------+------------------------------------------------+
    | off          | Adaptive positioning OFF everywhere; covers    |
    |              | stay at their current position.                |
    +--------------+------------------------------------------------+
    | all_open     | Every cover set to 100 %; manual override      |
    |              | activated (reverts after override duration).   |
    +--------------+------------------------------------------------+
    | all_closed   | Every cover set to 0 %;  manual override       |
    |              | activated (reverts after override duration).   |
    +--------------+------------------------------------------------+
    """

    _attr_has_entity_name = True
    _attr_translation_key = "adaptive_control_mode"
    _attr_options = HUB_SELECT_OPTIONS
    _attr_icon = "mdi:auto-mode"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Bind to the hub config entry's device."""
        self.hass = hass
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_adaptive_control_mode"
        self._attr_current_option = MODE_AUTO
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name="All Blinds",
            manufacturer="Adaptive Cover",
        )

    async def async_added_to_hass(self) -> None:
        """Restore last selected option on HA restart."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in HUB_SELECT_OPTIONS:
            self._attr_current_option = last_state.state
            LOGGER.debug(
                "AdaptiveControlModeSelect: restored state '%s'", last_state.state
            )

    async def async_select_option(self, option: str) -> None:
        """Apply the chosen mode across every regular entry."""
        LOGGER.debug("AdaptiveControlModeSelect: selecting '%s'", option)
        self._attr_current_option = option

        if option == MODE_AUTO:
            await self._apply_auto()
        elif option == MODE_OFF:
            await self._apply_off()
        elif option == MODE_ALL_OPEN:
            await self._apply_position(100)
        elif option == MODE_ALL_CLOSED:
            await self._apply_position(0)

        self.async_write_ha_state()

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    async def _apply_auto(self) -> None:
        """Enable adaptive control and clear all manual overrides."""
        for coord in _iter_regular_coordinators(self.hass):
            coord.control_toggle = True
            manager = getattr(coord, "manager", None)
            if manager is not None:
                for entity_id in getattr(coord, "entities", None) or ():
                    manager.reset(entity_id)
            await coord.async_refresh()

    async def _apply_off(self) -> None:
        """Disable adaptive control everywhere — covers stay in place."""
        for coord in _iter_regular_coordinators(self.hass):
            coord.control_toggle = False
            await coord.async_refresh()

    async def _apply_position(self, position: int) -> None:
        """Set every cover to *position* % and activate manual override."""
        for coord in _iter_regular_coordinators(self.hass):
            for entity_id in getattr(coord, "entities", None) or ():
                await coord.async_set_position(entity_id, position)
            await coord.async_refresh()
