# Changelog

All notable changes to **Adaptive Cover** are documented here.

---

## [1.8.11] — 2026-05-30

### New features

- **Per-entry cover entity** (`cover.py`) — Each regular config entry now exposes its own `AdaptiveCoverEntry` cover entity (unique_id suffix `_entry_cover`). This entity reports the coordinator's calculated adaptive position and allows direct open/close/set_position scoped to that group. It is the "main" entity of the regular-entry device.
- **Hub cover extra attributes** — `AdaptiveCoverAll` now exposes `adaptive_control`, `manual_override`, `covers` (list of physical entity_ids), and `config_entries` count as state attributes.
- **Hub cover turn_on / turn_off** — `AdaptiveCoverAll` supports `cover.turn_on` (enable adaptive, clear manual overrides) and `cover.turn_off` (disable adaptive) service calls.
- **Scene unique_id `_v2` suffix** — Forces a fresh entity registry entry to fix legacy entries where the entity name included the device prefix.

### Bug fixes

- **Orphan cover entities cleanup** (`cover.py`) — `_cleanup_orphan_cover_entities()` removes any `cover.*` entities registered on a regular entry's device whose unique_id doesn't end with `_entry_cover`. This automatically eliminates entities left behind by v1.7.x.

---

## [1.8.7] — 2026-05-18

### Bug fixes

- **Alexa name prefix** — Hub entities (cover, switch) had `_attr_has_entity_name = True`, which caused Alexa to prefix their names with the device name ("All Blinds Les volets" instead of "Les volets"). Fixed by setting `_attr_has_entity_name = False` and hard-coding the full name on all hub entities (cover, switch, scenes).

---

## [1.8.6] — 2026-05-18

### Changes

- **Hub switch re-added** — `AdaptiveControlAllSwitch` ("Les volets") re-added to the hub entry after being replaced by the select in v1.8.4. Both coexist: the switch handles Alexa voice control ("active / désactive les volets") while the select handles HA dashboard control.
- **Scenes simplified to 2** — Reduced from 4 scenes (open/closed + adaptive on/off) to 2 position scenes only (`all_open`, `all_closed`). Adaptive on/off is handled by the switch.

---

## [1.8.5] — 2026-05-18

### New features

- **Hub scenes** (`scene.py`) — 4 scenes on the hub device for Alexa shortcuts and automations.
- **`iter_regular_coordinators`** moved to `helpers.py` — Shared helper to iterate regular-entry coordinators, imported by `select.py` and `scene.py`.

---

## [1.8.4] — 2026-05-18

### Changes

- **Hub select replaces hub switch** — `AdaptiveControlModeSelect` (4 states: `auto`, `off`, `all_open`, `all_closed`) replaces the binary `AdaptiveControlAllSwitch` on the hub. Restores last selected state on HA restart via `RestoreEntity`.

---

## [1.8.3] — 2026-05-15

### New features

- **Hub switch** (`switch.py`) — `AdaptiveControlAllSwitch` added to the hub entry. Enables/disables adaptive control across all regular entries and clears manual overrides on turn-on.

---

## [1.8.2] — 2026-05-15

### New features

- **Auto-cleanup v1.8.0 leftover device** — `_cleanup_v18_leftover_device()` removes the orphan device with identifier `(DOMAIN, "all_covers")` left by v1.8.0. Runs once per HA boot (guarded by `_V18_CLEANUP_DONE`), idempotent.
- **Auto-bootstrap hub entry** — If no hub entry exists when the first regular entry sets up, `_async_bootstrap_hub_entry()` creates it automatically via `SOURCE_IMPORT`. Guarded by `_HUB_BOOTSTRAPPED`.

---

## [1.8.1] — 2026-05-15

### Changes

- **Dedicated hub config entry** — The "All Blinds" aggregate cover is now bound to its own singleton config entry (`is_hub=True`) instead of being attached to the first regular entry's device. The config flow menu now offers "All Blinds" as an explicit creation option.
- **Cover platform only on hub** — Regular entries no longer create a cover entity on the `cover` platform (only the hub entry does). This avoids the v1.7.x pattern of one aggregate cover per regular entry.

---

## [1.8.0] — 2026-05-15

### New features

- **Singleton aggregate cover** — A single `AdaptiveCoverAll` entity controls all covers across all regular entries (open/close/set_position broadcasts to every entry).
- **Single-lookup optimisation** — `pos_sun` and `_get_current_position` now read `hass.states` once per call instead of using the deprecated `state_attr` helper.

---

## [1.7.2] — 2026-05-15

### Bug fixes

- **`None` lux / irradiance on first refresh** — `_lux_toggle` and `_irradiance_toggle` were initialised to `None` when the entity was configured, causing `lux()` to short-circuit to `False` and preventing Winter mode on the first coordinator refresh. Fixed by initialising to `True` when the entity is configured (matching `initial_state=True` of the corresponding switch).
- **`OptionsFlow.config_entry` read-only** — Since HA 2025.12, `OptionsFlowWithConfigEntry.config_entry` is a read-only property. Any assignment now raises `AttributeError`. All direct assignments to `self.config_entry` in the options flow were removed.

---

## [1.7.1] — 2026-05-14

### Bug fixes

- **`state_attr` removed from HA core** — `homeassistant.helpers.template.state_attr` was removed in recent Home Assistant versions, causing the integration to crash silently when reading entity attributes. Both `calculation.py` and `coordinator.py` now use a local `state_attr()` helper in `helpers.py` that reads directly from `hass.states`. Affected paths:
  - Weather entity temperature (`calculation.py`)
  - Climate temperature entity (`calculation.py`)
  - Cover current position and tilt position (`coordinator.py`)
  - Sun azimuth and elevation (`coordinator.py`)

---

## [1.7.0] — 2026-05-08

### New features

- **Global cover entity** (`cover.py`) — Each config entry now exposes a single aggregate `cover.*` entity that controls all physical covers in the group simultaneously.
  - `open_cover` / `close_cover` / `set_cover_position` → moves all covers and flags them as *manual*.
  - `turn_on` → re-enables adaptive control and clears all manual flags.
  - `turn_off` → disables adaptive control.
  - State reports the average position across all covers.

- **Climate Debug diagnostic sensor** (`sensor.py`) — New `sensor.climate_debug_<name>` entity (category: Diagnostic) that exposes every intermediate value in the climate decision tree as attributes. Key attributes: `is_winter`, `is_summer`, `is_presence`, `sun_in_window`, `temp_inside`, `temp_outside`, `temp_used_winter`, `temp_used_summer`, `active_branch`, and all threshold values.

### Bug fixes

- **Switches turning OFF after HA restart** (`switch.py`) — `async_added_to_hass()` was not calling `super()`, which prevented `CoordinatorEntity` from registering its state-update listener. Fixed by calling `await super().async_added_to_hass()` before restoring the last state.

- **`control_method` stuck in `summer` or `winter`** (`coordinator.py`) — Two independent `if` statements in `climate_mode_data()` prevented returning to `intermediate` once a seasonal mode was set. Fixed with `if / elif / else`.

- **`temperature_for_winter` / `temperature_for_summer`** (`calculation.py`) — Introduced dedicated properties that apply the correct sensor source for each seasonal check: inside sensor preferred for winter, outside sensor (when `temp_switch=True`) for summer.

- **`start_time` not assigned** (`coordinator.py`) — `self._start_time` was not assigned when using a static start time (only the entity path wrote it). The missing assignment prevented the `start_time > end_time` cross-check from ever working.

---

## [1.5.0] — 2026-05-07 (baseline)

Initial tracked version. Features present at this baseline:

### Core

- Sun-position tracking using `sun.sun` azimuth and elevation.
- Three cover types: **vertical blind**, **horizontal awning**, **tilt (venetian)**.
- Field-of-view (FOV) configuration per window (left/right angle offsets from window normal).
- Default fallback position when sun is outside FOV.

### Cover control

- Grouping of multiple `cover.*` entities under a single config entry.
- `Toggle Control` switch to enable/disable adaptive positioning.
- `Manual Override` switch — automatically activated when the cover is moved manually.
- Manual override duration with configurable reset time.
- Manual threshold: minimum position delta considered a manual move.
- Option to ignore intermediate positions (only fully open/closed moves count as manual).

### Time window

- Static start/end times or `input_datetime` entity references.
- Sunrise/sunset offsets.
- Configurable sunset position with optional return-to-default behaviour.

### Position limits

- Optional minimum and maximum position clamps.

### Climate mode (optional)

- Three-branch logic: **summer** (block heat), **winter** (solar gain), **intermediate** (sun tracking).
- Indoor temperature entity.
- Outdoor temperature entity or weather entity as temperature source.
- Configurable `temp_low` (winter) and `temp_high` (summer) thresholds.
- Presence entity to bypass climate logic when nobody is home.
- Weather condition filter for "sunny" states.

### Light threshold (optional)

- Lux sensor with configurable threshold.
- Irradiance sensor with configurable threshold.
- Individual enable/disable switches for lux and irradiance checks.

### Blind spot

- Azimuth range where adaptive positioning is suspended.
- Configurable minimum elevation for blind spot activation.

### Tilt options

- Slat depth and spacing for accurate tilt angle calculation.
- Mode 1 (0°–90°) and Mode 2 (0°–180°, bi-directional).

### Transparent blind

- Position adjustment for semi-transparent materials.

### Interpolation

- Custom position curve mapping sun angle to cover position.

### Sensors

- Cover Position sensor (%).
- Start Sun / End Sun timestamp sensors.
- Control Method sensor.

### Platforms

- `sensor`, `switch`, `binary_sensor`, `button`, `cover`.
