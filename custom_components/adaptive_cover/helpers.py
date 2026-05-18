"""Helper functions."""

from __future__ import annotations

import datetime as dt

from dateutil import parser
from homeassistant.core import HomeAssistant, split_entity_id


def get_safe_state(hass: HomeAssistant, entity_id: str) -> str | None:
    """Return entity state, or None if unknown/unavailable."""
    state = hass.states.get(entity_id)
    if not state or state.state in ("unknown", "unavailable"):
        return None
    return state.state


def state_attr(hass: HomeAssistant, entity_id: str, attribute: str):
    """Return an attribute of a state, or None if state/attribute is missing.

    Replacement for the deprecated ``homeassistant.helpers.template.state_attr``
    (removed in HA core). Reads directly from ``hass.states`` — single lookup,
    no template engine.
    """
    state = hass.states.get(entity_id)
    if state is None:
        return None
    return state.attributes.get(attribute)


def get_domain(entity: str) -> str | None:
    """Return the domain part of an entity_id."""
    if entity is not None:
        # CLEAN: _ replaces object_id (W0612 — never used)
        domain, _ = split_entity_id(entity)
        return domain
    return None


def get_datetime_from_str(string: str) -> dt.datetime | None:
    """Convert a datetime string to a naive datetime object."""
    if string is not None:
        return parser.parse(string, ignoretz=True)
    return None


def get_last_updated(entity_id: str, hass: HomeAssistant) -> dt.datetime | None:
    """Return last_updated timestamp of an entity, or None."""
    if entity_id is not None:
        state = hass.states.get(entity_id)
        if state:
            return state.last_updated
    return None


# CLEAN: get_timedelta_str, check_time_passed, dt_check_time_passed removed
# No usages found in the project (dead code confirmed by static analysis)


def iter_regular_coordinators(hass: HomeAssistant):
    """Yield every Adaptive Cover coordinator (regular entries only).

    Skips internal bookkeeping keys (``_*``) and any ``None`` placeholders
    so callers never receive the hub entry or migration flags.
    Imported by ``select.py`` and ``scene.py`` to avoid duplication.
    """
    from .const import DOMAIN  # local import to avoid circular dependency

    for key, value in hass.data.get(DOMAIN, {}).items():
        if isinstance(key, str) and key.startswith("_"):
            continue
        if value is None:
            continue
        yield value
