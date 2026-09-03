"""Helper functions."""

from __future__ import annotations

import datetime as dt

from dateutil import parser
from homeassistant.const import STATE_OFF
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


def is_opening_open(hass: HomeAssistant, entity_id: str | None) -> bool:
    """Return True when the window/door is open — or when we cannot tell.

    Fail-safe contract (issue #498): a dead battery, a dropped Zigbee
    device, or a deleted entity must degrade to "as if there were no
    sensor at all", never to "closed". A sensor that lies is worse than no
    sensor — this mirrors is_presence_detected above, but note the
    direction is INVERTED: there, the safe default is "present" and the
    test is `== "on"`; here, the safe default is "open" and the test is
    `!= "off"`. Only the exact string "off" may conclude "closed" — an
    unexpected value (a typo, a non-boolean template state, "On" with a
    stray capital) must fail toward "open", the same way "unknown" does.

    Supported domains (HA convention for binary_sensor device_class door /
    window / opening / garage_door: "on" means open):
      - ``binary_sensor`` : "off" → closed, anything else → open
      - ``input_boolean`` : same

    Open (fail-safe) for:
      - ``entity_id`` is None            → actually returns False: no
        sensor configured means nothing to guard against, not "assume the
        worst". This is the one case that is NOT fail-safe on purpose.
      - entity missing from ``hass.states``, state "unknown"/"unavailable"
      - a non-string or empty state
      - any domain other than the two above
    """
    if entity_id is None:
        return False  # no sensor configured → never blocks

    state = get_safe_state(hass, entity_id)
    if state is None:
        return True  # missing/unknown/unavailable → fail-safe

    if not isinstance(state, str) or not state.strip():
        return True  # fail-safe

    if get_domain(entity_id) in ("binary_sensor", "input_boolean"):
        return state != STATE_OFF  # NOT "== STATE_ON" — see docstring above
    return True  # unrecognized domain → fail-safe


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
