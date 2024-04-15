"""Button platform for the Adaptive Cover integration."""

from __future__ import annotations

import asyncio

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import _LOGGER, CONF_ENTITIES, CONF_SENSOR_TYPE, DOMAIN
from .coordinator import AdaptiveDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    coordinator: AdaptiveDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    reset_manual = AdaptiveCoverButton(
        config_entry, config_entry.entry_id, "Reset Manual Override", coordinator
    )

    buttons = []

    entities = config_entry.options.get(CONF_ENTITIES, [])
    if len(entities) >= 1:
        buttons = [reset_manual]

    async_add_entities(buttons)


class AdaptiveCoverButton(
    CoordinatorEntity[AdaptiveDataUpdateCoordinator], ButtonEntity
):
    """Representation of a adaptive cover button."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_icon = "mdi:cog-refresh-outline"

    def __init__(
        self,
        config_entry,
        unique_id: str,
        button_name: str,
        coordinator: AdaptiveDataUpdateCoordinator,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator=coordinator)
        self.type = {
            "cover_blind": "Vertical",
            "cover_awning": "Horizontal",
            "cover_tilt": "Tilt",
        }
        self._name = config_entry.data["name"]
        self._device_name = self.type[config_entry.data[CONF_SENSOR_TYPE]]
        self._attr_unique_id = f"{unique_id}_{button_name}"
        self._device_id = unique_id
        self._button_name = button_name
        self._entities = config_entry.options.get(CONF_ENTITIES, [])
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
        )

    @property
    def name(self):
        """Name of the entity."""
        return f"{self._button_name} {self._name}"

    async def async_press(self) -> None:
        """Handle the button press."""
        for entity in self._entities:
            if self.coordinator.manager.is_cover_manual(entity):
                _LOGGER.debug("Resetting manual override for: %s", entity)
                await self.coordinator.async_set_position(entity)
                self.coordinator.manager.reset(entity)
            else:
                _LOGGER.debug(
                    "Resetting manual override for %s is not needed since it is already auto-cotrolled",
                    entity,
                )
        await self.coordinator.async_refresh()
