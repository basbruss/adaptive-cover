"""Helper functions."""

from __future__ import annotations

import datetime as dt
import math

from dateutil import parser
from homeassistant.core import HomeAssistant, split_entity_id


def get_safe_state(hass: HomeAssistant, entity_id: str) -> str | None:
    """Return entity state, or None if unknown/unavailable."""
    state = hass.states.get(entity_id)
    if not state or state.state in ("unknown", "unavailable"):
        return None
    return state.state


def get_numeric_state(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Return an entity's state as a float, or None when it isn't usable.

    None covers every "can't use this" case alike — no entity configured,
    unknown/unavailable (via get_safe_state), a state that doesn't parse as
    a number, or one that parses but isn't finite (NaN, +-inf) — so callers
    get one thing to check rather than several. NaN in particular matters:
    float("nan") parses without error, but a caller that then rounds or
    clamps it (as _resolve_numeric_option does) would raise, turning one
    entity's weird state into a coordinator-wide crash. Screening it out
    here keeps every caller's "falls back to the configured value" contract
    genuinely exception-free.
    """
    if entity_id is None:
        return None
    state = get_safe_state(hass, entity_id)
    if state is None:
        return None
    try:
        value = float(state)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


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


def is_presence_detected(hass: HomeAssistant, entity_id: str | None) -> bool:
    """Return True when someone is detected as home.

    Supports the same domains as ``ClimateCoverData.is_presence``:
      - ``device_tracker`` : state == "home"
      - ``zone``           : state > 0  (number of people)
      - ``binary_sensor``  : state == "on"
      - ``input_boolean``  : state == "on"

    Safe defaults:
      - ``entity_id`` is None  → True  (no sensor configured → assume present)
      - state is unavailable   → True  (fail-safe: don't close on sensor error)
    """
    if entity_id is None:
        return True
    state = get_safe_state(hass, entity_id)
    if state is None:
        return True  # unavailable → fail-safe
    domain = get_domain(entity_id)
    if domain == "device_tracker":
        return state == "home"
    if domain == "zone":
        try:
            return int(state) > 0
        except ValueError:
            return True
    if domain in ("binary_sensor", "input_boolean"):
        return state == "on"
    return True


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
