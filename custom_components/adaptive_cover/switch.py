"""Switch platform for the Adaptive Cover integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.input_boolean import DOMAIN as INPUT_DOMAIN
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TOGGLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_CLIMATE_MODE, CONF_SENSOR_TYPE, DOMAIN
from .coordinator import AdaptiveDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the demo switch platform."""
    coordinator: AdaptiveDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    climate_switch = AdaptiveCoverSwitch(
        config_entry,
        config_entry.entry_id,
        "Climate Mode",
        True,
        "mdi:home-thermometer-outline",
        True,
        coordinator,
    )
    climate_mode = config_entry.options.get(CONF_CLIMATE_MODE)
    switches = []
    if climate_mode:
        switches.append(climate_switch)
    async_add_entities(switches)


class AdaptiveCoverSwitch(
    CoordinatorEntity[AdaptiveDataUpdateCoordinator], SwitchEntity
):
    """Representation of a adaptive cover switch."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        config_entry,
        unique_id: str,
        switch_name: str,
        state: bool,
        icon: str | None,
        assumed: bool,
        coordinator: AdaptiveDataUpdateCoordinator,
        device_class: SwitchDeviceClass | None = None,
    ) -> None:
        """Initialize the Demo switch."""
        super().__init__(coordinator=coordinator)
        self.type = {
            "cover_blind": "Vertical",
            "cover_awning": "Horizontal",
            "cover_tilt": "Tilt",
        }
        self._name = config_entry.data["name"]
        self._device_name = self.type[config_entry.data[CONF_SENSOR_TYPE]]
        self._switch_name = switch_name
        self._attr_assumed_state = assumed
        self._attr_device_class = device_class
        self._attr_icon = icon
        self._attr_is_on = state
        self._attr_unique_id = f"{unique_id}_{switch_name}"
        self._device_id = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
        )

    @property
    def name(self):
        """Name of the entity."""
        return f"{self._switch_name} {self._name}"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self._attr_is_on = True
        self.coordinator.switch_mode = True
        await self.coordinator.async_refresh()
        self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        self._attr_is_on = False
        self.coordinator.switch_mode = False
        await self.hass.services.async_call(
            INPUT_DOMAIN, SERVICE_TOGGLE, {ATTR_ENTITY_ID: "input_boolean.test_service"}
        )
        await self.coordinator.async_refresh()
        self.schedule_update_ha_state()
