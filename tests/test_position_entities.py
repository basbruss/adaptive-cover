"""Tests for min/max/default position read from entities (#496)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.adaptive_cover.const import (
    CONF_DEFAULT_HEIGHT,
    CONF_DEFAULT_HEIGHT_ENTITY,
    CONF_MAX_POSITION,
    CONF_MAX_POSITION_ENTITY,
    CONF_MIN_POSITION,
    CONF_MIN_POSITION_ENTITY,
)
from custom_components.adaptive_cover.coordinator import (
    AdaptiveDataUpdateCoordinator,
)
from custom_components.adaptive_cover.helpers import get_numeric_state

MIN_E = "input_number.min_pos"
MAX_E = "input_number.max_pos"
DEF_E = "input_number.default_pos"


def _hass(states: dict[str, str]) -> MagicMock:
    hass = MagicMock()

    def _get(entity_id):
        if entity_id not in states:
            return None
        state = MagicMock()
        state.state = states[entity_id]
        return state

    hass.states.get = _get
    return hass


def _coordinator(states: dict[str, str]) -> AdaptiveDataUpdateCoordinator:
    coordinator = object.__new__(AdaptiveDataUpdateCoordinator)
    coordinator.hass = _hass(states)
    coordinator.logger = MagicMock()
    coordinator._numeric_entity_warned = set()
    return coordinator


def _resolve(coordinator, options):
    """Run the same resolution _update_options performs."""
    default = coordinator._resolve_numeric_option(
        options, CONF_DEFAULT_HEIGHT, CONF_DEFAULT_HEIGHT_ENTITY, minimum=0, maximum=100
    )
    min_pos = coordinator._resolve_numeric_option(
        options, CONF_MIN_POSITION, CONF_MIN_POSITION_ENTITY, minimum=0, maximum=100
    )
    max_pos = coordinator._resolve_numeric_option(
        options, CONF_MAX_POSITION, CONF_MAX_POSITION_ENTITY, minimum=0, maximum=100
    )
    min_pos, max_pos = coordinator._validate_position_bounds(options, min_pos, max_pos)
    return default, min_pos, max_pos


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("42", 42.0),
        ("12.5", 12.5),
        ("unknown", None),
        ("unavailable", None),
        ("abc", None),
        ("", None),
        ("nan", None),
        ("inf", None),
    ],
)
def test_get_numeric_state(state, expected):
    """Only finite numbers are usable."""
    assert get_numeric_state(_hass({MIN_E: state}), MIN_E) == expected


def test_get_numeric_state_missing_entity():
    assert get_numeric_state(_hass({}), MIN_E) is None
    assert get_numeric_state(_hass({}), None) is None


def test_static_config_unchanged():
    """Without entities the configured constants pass through untouched."""
    options = {CONF_DEFAULT_HEIGHT: 60, CONF_MIN_POSITION: 10, CONF_MAX_POSITION: 90}
    assert _resolve(_coordinator({}), options) == (60, 10, 90)


def test_entity_values_are_used_clamped_and_rounded():
    coordinator = _coordinator({DEF_E: "55.6", MIN_E: "-5", MAX_E: "120"})
    options = {
        CONF_DEFAULT_HEIGHT: 60,
        CONF_DEFAULT_HEIGHT_ENTITY: DEF_E,
        CONF_MIN_POSITION: 10,
        CONF_MIN_POSITION_ENTITY: MIN_E,
        CONF_MAX_POSITION: 90,
        CONF_MAX_POSITION_ENTITY: MAX_E,
    }
    assert _resolve(coordinator, options) == (56, 0, 100)


@pytest.mark.parametrize("bad", ["unavailable", "unknown", "open", "nan"])
def test_unusable_entity_falls_back_and_warns_once(bad):
    coordinator = _coordinator({MIN_E: bad})
    options = {CONF_MIN_POSITION: 15, CONF_MIN_POSITION_ENTITY: MIN_E}

    for _ in range(3):
        _, min_pos, _ = _resolve(coordinator, options)
        assert min_pos == 15

    assert coordinator.logger.warning.call_count == 1


def test_missing_entity_without_constant_falls_back_to_none():
    """No constant configured and entity gone -> guard inactive, no crash."""
    coordinator = _coordinator({})
    options = {CONF_MIN_POSITION_ENTITY: MIN_E}
    assert _resolve(coordinator, options)[1] is None


def test_min_not_below_max_falls_back_to_configured_values():
    coordinator = _coordinator({MIN_E: "70", MAX_E: "40"})
    options = {
        CONF_MIN_POSITION: 10,
        CONF_MIN_POSITION_ENTITY: MIN_E,
        CONF_MAX_POSITION: 90,
        CONF_MAX_POSITION_ENTITY: MAX_E,
    }

    _, min_pos, max_pos = _resolve(coordinator, options)

    assert (min_pos, max_pos) == (10, 90)
    coordinator.logger.warning.assert_called_once()


def test_conflict_with_only_min_from_entity():
    """Only the entity-sourced bound is replaced."""
    coordinator = _coordinator({MIN_E: "95"})
    options = {
        CONF_MIN_POSITION: 20,
        CONF_MIN_POSITION_ENTITY: MIN_E,
        CONF_MAX_POSITION: 80,
    }
    assert _resolve(coordinator, options)[1:] == (20, 80)


def test_conflict_without_usable_static_values_keeps_the_floor():
    """If configured values can't fix it, keep min_position and drop max."""
    coordinator = _coordinator({MIN_E: "60", MAX_E: "30"})
    options = {CONF_MIN_POSITION_ENTITY: MIN_E, CONF_MAX_POSITION_ENTITY: MAX_E}
    assert _resolve(coordinator, options)[1:] == (60, None)


def test_equal_bounds_are_a_conflict():
    coordinator = _coordinator({MIN_E: "50", MAX_E: "50"})
    options = {
        CONF_MIN_POSITION: 10,
        CONF_MIN_POSITION_ENTITY: MIN_E,
        CONF_MAX_POSITION: 90,
        CONF_MAX_POSITION_ENTITY: MAX_E,
    }
    assert _resolve(coordinator, options)[1:] == (10, 90)


def test_conflict_warning_rearms_after_recovery():
    states = {MIN_E: "70", MAX_E: "40"}
    coordinator = _coordinator(states)
    options = {
        CONF_MIN_POSITION: 10,
        CONF_MIN_POSITION_ENTITY: MIN_E,
        CONF_MAX_POSITION: 90,
        CONF_MAX_POSITION_ENTITY: MAX_E,
    }
    _resolve(coordinator, options)
    _resolve(coordinator, options)
    assert coordinator.logger.warning.call_count == 1

    states[MAX_E] = "80"
    assert _resolve(coordinator, options)[1:] == (70, 80)

    states[MAX_E] = "40"
    _resolve(coordinator, options)
    assert coordinator.logger.warning.call_count == 2


def test_static_only_conflict_is_left_alone():
    """A purely static config is the config flow's concern, not changed here."""
    coordinator = _coordinator({})
    options = {CONF_MIN_POSITION: 50, CONF_MAX_POSITION: 50}
    assert _resolve(coordinator, options)[1:] == (50, 50)
    coordinator.logger.warning.assert_not_called()
