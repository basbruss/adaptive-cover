from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_SENSOR_TYPE

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the demo switch platform."""
    async_add_entities(
        [
            AdaptiveCoverSwitch(config_entry,config_entry.entry_id, "Climate Mode", True, "mdi:home-thermometer-outline", True),
        ]
    )


class AdaptiveCoverSwitch(SwitchEntity):
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
        device_class: SwitchDeviceClass | None = None,
    ) -> None:
        """Initialize the Demo switch."""
        self.type = {
            "cover_blind": "Vertical",
            "cover_awning": "Horizontal",
            "cover_tilt": "Tilt",
        }
        self._name = config_entry.data["name"]
        self._device_name= self.type[config_entry.data[CONF_SENSOR_TYPE]]
        self._switch_name = switch_name
        self._attr_assumed_state = assumed
        self._attr_device_class = device_class
        self._attr_icon = icon
        self._attr_is_on = state
        self._attr_unique_id = unique_id
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, unique_id)},
            name=self._device_name,
        )

    @property
    def name(self):
        """Name of the entity."""
        return f"{self._switch_name}_{self._name}"

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self._attr_is_on = True
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        self._attr_is_on = False
        self.schedule_update_ha_state()
