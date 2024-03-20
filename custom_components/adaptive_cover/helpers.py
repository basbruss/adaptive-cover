"""Helper functions."""

from homeassistant.core import split_entity_id


def get_safe_state(hass, entity_id: str):
    """Get a safe state value if not available."""
    state = hass.states.get(entity_id)
    if not state or state.state in ["unknown", "unavailable"]:
        return None
    return state.state


def get_safe_attribute(hass, entity_id: str, attribute: str):
    """Get a safe value from attribute."""
    if not get_safe_state(hass, entity_id):
        return None
    attr_obj = hass.states.get(entity_id).attributes
    if attribute not in attr_obj:
        return None
    return attr_obj[attribute]


def get_domain(entity: str):
    """Get domain of entity."""
    if entity is not None:
        domain, object_id = split_entity_id(entity)
        return domain
