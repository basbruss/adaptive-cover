"""Time platform for Adaptive Cover."""
import datetime as dt
from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, CONF_START_TIME_WORKDAY, CONF_START_TIME_WEEKEND, CONF_WORKDAY_ENTITY

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the time platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Sprawdzamy czy użytkownik skonfigurował encję Workday
    workday_entity = config_entry.options.get(CONF_WORKDAY_ENTITY)
    entities = []
    
    if workday_entity:
        # Jeśli tak: dodajemy dwa osobne czasy
        entities.append(AdaptiveCoverTimeEntity(coordinator, config_entry, CONF_START_TIME_WORKDAY, "Otwarcie (Dni robocze)", "07:00:00", "mdi:briefcase-clock"))
        entities.append(AdaptiveCoverTimeEntity(coordinator, config_entry, CONF_START_TIME_WEEKEND, "Otwarcie (Dni wolne)", "09:00:00", "mdi:calendar-clock"))
    else:
        # Jeśli nie: dodajemy tylko jeden, uniwersalny czas otwarcia
        entities.append(AdaptiveCoverTimeEntity(coordinator, config_entry, CONF_START_TIME_WORKDAY, "Czas otwarcia (Codziennie)", "07:00:00", "mdi:clock-outline"))
        
    async_add_entities(entities)

class AdaptiveCoverTimeEntity(CoordinatorEntity, TimeEntity):
    """Representation of a Time entity for starting times."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, config_entry, key, name, default_time, icon):
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._key = key
        self._attr_unique_id = f"{config_entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_icon = icon

        time_str = config_entry.options.get(key, default_time)
        self._attr_native_value = dt.time.fromisoformat(time_str)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.config_entry.entry_id)},
            name=self.config_entry.data.get("name", "Adaptive Cover"),
        )

    async def async_set_value(self, value: dt.time) -> None:
        self._attr_native_value = value
        new_options = dict(self.config_entry.options)
        new_options[self._key] = value.isoformat()
        self.hass.config_entries.async_update_entry(self.config_entry, options=new_options)
        self.async_write_ha_state()
        await self.coordinator.async_refresh()