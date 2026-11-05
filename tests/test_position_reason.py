"""Tests for the Position Reason sensor (#295)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from custom_components.adaptive_cover.calculation import (
    AdaptiveGeneralCover,
    AdaptiveTiltCover,
    AdaptiveVerticalCover,
    ClimateCoverState,
    NormalCoverState,
)
from custom_components.adaptive_cover.const import (
    REASON_CLIMATE_INTERMEDIATE_SUN,
    REASON_CLIMATE_LOW_LIGHT,
    REASON_CLIMATE_NO_PRESENCE,
    REASON_CLIMATE_SUMMER_CLOSED,
    REASON_CLIMATE_SUMMER_TRANSPARENT,
    REASON_CLIMATE_TILT_PRESET,
    REASON_CLIMATE_WINTER_SUN,
    REASON_CONTROL_OFF,
    REASON_OUTSIDE_TIME_WINDOW,
    REASON_SECURITY,
    REASON_SUN_IN_BLIND_SPOT,
    REASON_SUN_OUTSIDE_ELEVATION,
    REASON_SUN_OUTSIDE_FOV,
    REASON_SUN_TRACKING,
    REASON_SUNSET_POSITION,
    REASONS,
)
from custom_components.adaptive_cover.coordinator import (
    AdaptiveCoverManager,
    AdaptiveDataUpdateCoordinator,
)
from custom_components.adaptive_cover.sensor import AdaptiveCoverReasonSensor

COMPONENT = Path(__file__).parent.parent / "custom_components" / "adaptive_cover"

COMMON = {
    "sol_azi": 180.0,  # sun due south, window faces south: in view
    "sol_elev": 20.0,
    "sunset_pos": 0,
    "sunset_off": 0,
    "sunrise_off": 0,
    "timezone": "UTC",
    "fov_left": 45,
    "fov_right": 45,
    "win_azi": 180,
    "h_def": 60,
    "max_pos": 100,
    "min_pos": 0,
    "max_pos_bool": False,
    "min_pos_bool": False,
    "blind_spot_left": None,
    "blind_spot_right": None,
    "blind_spot_elevation": None,
    "blind_spot_on": False,
    "min_elevation": None,
    "max_elevation": None,
}


@pytest.fixture(autouse=True)
def _no_sun_data():
    with patch("custom_components.adaptive_cover.calculation.SunData"):
        yield
    patch.stopall()


def _sunset(value: bool) -> None:
    patch.object(
        AdaptiveGeneralCover, "sunset_valid", new_callable=PropertyMock
    ).start().return_value = value


def _cover(sunset: bool = False, **kwargs) -> AdaptiveVerticalCover:
    _sunset(sunset)
    return AdaptiveVerticalCover(
        MagicMock(), MagicMock(), distance=0.5, h_win=2.0, **{**COMMON, **kwargs}
    )


def _tilt(**kwargs) -> AdaptiveTiltCover:
    _sunset(False)
    return AdaptiveTiltCover(
        MagicMock(),
        MagicMock(),
        **{**COMMON, **kwargs},
        slat_distance=2.0,
        depth=2.5,
        mode="mode1",
    )


def _climate(
    *,
    presence=True,
    winter=False,
    summer=False,
    sunny=True,
    transparent=False,
    blind_type="cover_blind",
) -> MagicMock:
    data = MagicMock()
    data.is_presence = presence
    data.is_winter = winter
    data.is_summer = summer
    data.is_sunny = sunny
    data.lux = False
    data.irradiance = False
    data.transparent_blind = transparent
    data.blind_type = blind_type
    return data


# ── Basic mode ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("kwargs", "sunset", "reason", "source"),
    [
        ({}, False, REASON_SUN_TRACKING, None),
        ({}, True, REASON_SUNSET_POSITION, "sunset"),
        ({"sol_azi": 0.0}, False, REASON_SUN_OUTSIDE_FOV, "default"),
        ({"sol_elev": -5.0}, False, REASON_SUN_OUTSIDE_ELEVATION, "default"),
        ({"min_elevation": 30}, False, REASON_SUN_OUTSIDE_ELEVATION, "default"),
        (
            {"blind_spot_left": 10, "blind_spot_right": 80, "blind_spot_on": True},
            False,
            REASON_SUN_IN_BLIND_SPOT,
            "default",
        ),
    ],
)
def test_normal_reason(kwargs, sunset, reason, source):
    """Each basic branch records its own reason and default source."""
    state = NormalCoverState(_cover(sunset=sunset, **kwargs))
    state.get_state()
    assert state.reason == reason
    assert state.default_source == source
    assert state.limit is None


@pytest.mark.parametrize(
    ("kwargs", "expected", "limit"),
    [
        ({"max_pos": 40}, 40, "max_position"),  # default 60 capped at 40
        ({"min_pos": 80}, 80, "min_position"),  # default 60 raised to 80
    ],
)
def test_normal_limit(kwargs, expected, limit):
    """A min/max clamp is recorded without hiding why the default applied."""
    state = NormalCoverState(_cover(sol_azi=0.0, **kwargs))
    assert state.get_state() == expected
    assert state.limit == limit
    assert state.reason == REASON_SUN_OUTSIDE_FOV


# ── Climate mode ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("climate", "reason", "expected"),
    [
        ({"presence": False}, REASON_CLIMATE_NO_PRESENCE, 0),
        ({"winter": True}, REASON_CLIMATE_WINTER_SUN, 100),
        ({"summer": True}, REASON_CLIMATE_SUMMER_CLOSED, 0),
        ({"summer": True, "transparent": True}, REASON_CLIMATE_SUMMER_TRANSPARENT, 9),
        ({"sunny": False}, REASON_CLIMATE_LOW_LIGHT, 60),
        ({}, REASON_CLIMATE_INTERMEDIATE_SUN, 9),
    ],
)
def test_climate_reason(climate, reason, expected):
    """Each climate branch records a reason specific to that branch."""
    state = ClimateCoverState(_cover(), _climate(**climate))
    assert state.get_state() == expected
    assert state.reason == reason


def test_climate_sun_out_of_view_keeps_seasonal_source():
    """Sun out of view: the sun reason, plus which seasonal default was used."""
    cover = _cover(sol_azi=0.0, h_def_winter=100)
    state = ClimateCoverState(cover, _climate(winter=True))
    assert state.get_state() == 100
    assert state.reason == REASON_SUN_OUTSIDE_FOV
    assert state.default_source == "winter"


def test_climate_low_light_after_sunset_says_sunset():
    """The sunset position wins over the low-light default, and says so."""
    state = ClimateCoverState(_cover(sunset=True), _climate(sunny=False))
    assert state.get_state() == 0
    assert state.reason == REASON_SUNSET_POSITION


def test_climate_basic_keeps_more_specific_reason():
    """A blind spot inside the 'follow the sun' branch isn't relabelled."""
    cover = _cover(blind_spot_left=10, blind_spot_right=80, blind_spot_on=True)
    state = ClimateCoverState(cover, _climate())
    state.get_state()
    assert state.reason == REASON_SUN_IN_BLIND_SPOT


def test_climate_limit():
    """The climate clamp is recorded too."""
    state = ClimateCoverState(_cover(max_pos=70), _climate(winter=True))
    assert state.get_state() == 70
    assert state.limit == "max_position"


def test_tilt_overrides_stale_normal_reason():
    """Tilt replaces normal_type_cover()'s result, so its reason must win."""
    state = ClimateCoverState(_tilt(), _climate(winter=True, blind_type="cover_tilt"))
    state.get_state()
    assert state.reason == REASON_CLIMATE_TILT_PRESET


def test_states_on_one_cover_do_not_share_reasons():
    """Climate and normal states evaluated on one cover keep their own reason."""
    cover = _cover()
    climate = ClimateCoverState(cover, _climate(summer=True))
    climate.get_state()
    normal = NormalCoverState(cover)
    normal.get_state()
    assert climate.reason == REASON_CLIMATE_SUMMER_CLOSED
    assert normal.reason == REASON_SUN_TRACKING


# ── Coordinator ──────────────────────────────────────────────────────────────

COVER = "cover.office"


def _coordinator(
    *, position=60, manual=False, options=None, last_updated=None
) -> AdaptiveDataUpdateCoordinator:
    states = {COVER: MagicMock(attributes={"current_position": position})}
    # Moved long ago unless a test says otherwise, so delta time never blocks.
    states[COVER].last_updated = last_updated or dt.datetime(2000, 1, 1, tzinfo=dt.UTC)
    hass = MagicMock()
    hass.states.get = states.get
    coordinator = object.__new__(AdaptiveDataUpdateCoordinator)
    coordinator.hass = hass
    coordinator.logger = MagicMock()
    coordinator.config_entry = MagicMock(options=options or {})
    coordinator._cover_type = "cover_blind"
    coordinator._inverse_state = False
    coordinator._switch_mode = False
    coordinator._control_toggle = True
    coordinator._security_toggle = False
    coordinator._pending_close = {}
    coordinator._default_height = 60
    coordinator.entities = [COVER]
    coordinator.min_change = 5
    coordinator.time_threshold = 2
    coordinator.start_time = None
    coordinator.start_time_entity = None
    coordinator.end_time = None
    coordinator.end_time_entity = None
    coordinator._start_time = None
    coordinator.control_method = "intermediate"
    coordinator.climate_cover_state = None
    coordinator.manager = AdaptiveCoverManager({"minutes": 15}, MagicMock())
    coordinator.manager.add_covers([COVER])
    if manual:
        coordinator.manager.mark_manual_control(COVER)
    normal = NormalCoverState(_cover())
    coordinator.default_state = round(normal.get_state())
    coordinator.normal_cover_state = normal
    return coordinator


def test_reason_data_reports_calculation():
    """No gate active: the state is the calculation reason, with its inputs."""
    coordinator = _coordinator(position=9)
    data = coordinator.reason_data(9, {})
    assert data["reason"] == REASON_SUN_TRACKING
    assert data["position_reason"] == REASON_SUN_TRACKING
    assert data["target_position"] == 9
    assert data["calculated_position"] == 9
    assert data["sun_azimuth"] == 180.0
    assert data["sun_in_field_of_view"] is True
    assert data["covers"] == {COVER: "at_target"}
    json.dumps(data)  # attributes must be plain, serializable values


def test_reason_data_uses_climate_state_when_climate_mode_is_on():
    """With climate mode on, the reason comes from the climate calculation."""
    coordinator = _coordinator()
    climate = ClimateCoverState(_cover(), _climate(summer=True))
    coordinator.climate_state = round(climate.get_state())
    coordinator.climate_cover_state = climate
    coordinator._switch_mode = True
    coordinator.control_method = "summer"
    data = coordinator.reason_data(0, {})
    assert data["reason"] == REASON_CLIMATE_SUMMER_CLOSED
    assert data["calculated_position"] == 0
    assert data["climate_branch"] == "summer"


def test_reason_data_inverse_shows_both_positions():
    """Inverse state: the calculated and the final position differ."""
    data = _coordinator().reason_data(91, {})
    assert data["calculated_position"] == 9
    assert data["target_position"] == 91


@pytest.mark.parametrize(
    ("setup", "reason"),
    [
        ({"_control_toggle": False}, REASON_CONTROL_OFF),
        ({"_control_toggle": None}, REASON_CONTROL_OFF),  # not yet restored
        ({"end_time": "00:00:01"}, REASON_OUTSIDE_TIME_WINDOW),
    ],
)
def test_reason_data_gates(setup, reason):
    """A gate overrides the state but never hides the calculation reason."""
    coordinator = _coordinator()
    for key, value in setup.items():
        setattr(coordinator, key, value)
    data = coordinator.reason_data(9, {})
    assert data["reason"] == reason
    assert data["position_reason"] == REASON_SUN_TRACKING


def test_reason_data_security():
    """Security mode (switch on, nobody home) is reported over the calculation."""
    coordinator = _coordinator()
    coordinator._security_toggle = True
    coordinator.config_entry = MagicMock(options={"presence_entity": "person.me"})
    with patch(
        "custom_components.adaptive_cover.coordinator.is_presence_detected",
        return_value=False,
    ):
        assert coordinator.reason_data(9, {})["reason"] == REASON_SECURITY


def test_unavailable_time_entity_does_not_break_the_update():
    """An unreadable start-time helper means 'unknown', not an exception."""
    coordinator = _coordinator()
    coordinator.start_time_entity = "input_datetime.start"
    with patch(
        "custom_components.adaptive_cover.coordinator.get_safe_state",
        return_value=None,
    ):
        assert coordinator._in_time_window() is None
        assert coordinator.reason_data(9, {})["reason"] == REASON_SUN_TRACKING


def _recent() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


@pytest.mark.parametrize(
    ("kwargs", "state", "status"),
    [
        ({"manual": True}, 9, "manual_override"),
        ({"position": None}, 9, "position_unknown"),
        ({"position": 9}, 9, "at_target"),
        ({"position": 12}, 9, "below_delta_position"),  # 3 < min_change 5
        ({"position": 30, "last_updated": _recent()}, 9, "waiting_delta_time"),
        ({"position": 30}, 9, "moving_to_target"),
    ],
)
def test_cover_status(kwargs, state, status):
    """Each per-cover check that can keep a cover off target is named."""
    coordinator = _coordinator(**kwargs)
    assert coordinator.cover_status(COVER, state, {}) == status


def test_cover_status_close_pending():
    """A pre-close notice counting down is reported as such."""
    coordinator = _coordinator(position=30)
    coordinator._pending_close[COVER] = MagicMock()
    assert coordinator.cover_status(COVER, 0, {}) == "close_pending"


def test_cover_status_opening_open():
    """A close withheld by an open door/window sensor is reported."""
    coordinator = _coordinator(position=30)
    with patch(
        "custom_components.adaptive_cover.coordinator.is_opening_open",
        return_value=True,
    ):
        assert (
            coordinator.cover_status(COVER, 9, {"opening_entity": "binary_sensor.d"})
            == "opening_open"
        )


# ── Sensor contract ──────────────────────────────────────────────────────────


def test_reason_codes_are_unique_lowercase_slugs():
    """Enum options must be unique and valid translation keys."""
    assert len(REASONS) == len(set(REASONS))
    for code in REASONS:
        assert code == code.lower()
        assert code.replace("_", "").isalnum()


@pytest.mark.parametrize(
    "path",
    [
        COMPONENT / "strings.json",
        *sorted((COMPONENT / "translations").glob("*.json")),
    ],
    ids=lambda p: p.name,
)
def test_every_reason_is_translated(path):
    """Every reason code has a state string in every language."""
    states = json.loads(path.read_text())["entity"]["sensor"]["reason"]["state"]
    assert set(states) == set(REASONS)


def test_sensor_state_and_attributes():
    """The sensor shows the code as state and everything else as attributes."""
    sensor = object.__new__(AdaptiveCoverReasonSensor)
    sensor.data = MagicMock(reason=None)
    assert sensor.native_value is None
    assert sensor.extra_state_attributes is None

    sensor.data = MagicMock(reason={"reason": REASON_CONTROL_OFF, "target_position": 9})
    assert sensor.native_value == REASON_CONTROL_OFF
    assert sensor.native_value in sensor.options
    assert sensor.extra_state_attributes == {"target_position": 9}
