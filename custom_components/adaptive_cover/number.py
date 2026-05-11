"""Number platform for Adaptive Cover."""
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, CONF_CLOSE_SUNSET_OFFSET

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the number platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([AdaptiveCoverOffsetNumber(coordinator, config_entry)])

class AdaptiveCoverOffsetNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Number entity for sunset offset."""

    _attr_has_entity_name = True
    _attr_translation_key = "close_sunset_offset"

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._key = CONF_CLOSE_SUNSET_OFFSET
        self._attr_unique_id = f"{config_entry.entry_id}_{self._key}"
        self._attr_icon = "mdi:weather-sunset-down"
        
        self._attr_native_min_value = -120.0
        self._attr_native_max_value = 120.0
        self._attr_native_step = 5.0
        self._attr_native_unit_of_measurement = "min"
        self._attr_mode = "box"

        self._attr_native_value = float(config_entry.options.get(self._key, 0))

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.config_entry.entry_id)},
            name=self.config_entry.data.get("name", "Adaptive Cover"),
        )

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        new_options = dict(self.config_entry.options)
        new_options[self._key] = int(value)
        self.hass.config_entries.async_update_entry(self.config_entry, options=new_options)
        self.async_write_ha_state()
        await self.coordinator.async_refresh()