"""Select platform for Adaptive Cover."""
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

OPTIONS = [
    "none", 
    "15_min", 
    "30_min", 
    "60_min", 
    "120_min", 
    "240_min", 
    "sunset"
]

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([AdaptiveCoverOverrideSelect(coordinator, config_entry)])

class AdaptiveCoverOverrideSelect(CoordinatorEntity, SelectEntity):
    """Representation of a Select entity for Manual Override Duration."""

    _attr_has_entity_name = True
    _attr_translation_key = "manual_override"

    def __init__(self, coordinator, config_entry):
        """Initialize the select entity."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_override_duration"
        self._attr_icon = "mdi:timer-cog"
        self._attr_options = OPTIONS
        
        # Pobieramy to, co jest aktualnie zapisane w opcjach integracji
        duration_dict = config_entry.options.get("manual_override_duration", {"minutes": 15})
        minutes = duration_dict.get("minutes", 15)
        
        mapping_rev = {
            0: "none",
            15: "15_min",
            30: "30_min",
            60: "60_min",
            120: "120_min",
            240: "240_min",
            9999: "sunset"
        }
        self._attr_current_option = mapping_rev.get(minutes, "60_min")

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.config_entry.entry_id)},
            name=self.config_entry.data.get("name", "Adaptive Cover"),
        )

    async def async_select_option(self, option: str) -> None:
        """Change the selected option and SAVE permanently."""
        self._attr_current_option = option
        
        mapping = {
            "none": 0,
            "15_min": 15,
            "30_min": 30,
            "60_min": 60,
            "120_min": 120,
            "240_min": 240,
            "sunset": 9999
        }
        minutes = mapping.get(option, 60)
        
        new_options = dict(self.config_entry.options)
        new_options["manual_override_duration"] = {"minutes": minutes}
        
        self.hass.config_entries.async_update_entry(self.config_entry, options=new_options)
        self.async_write_ha_state()