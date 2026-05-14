# Changelog

All notable changes to **Adaptive Cover** are documented here.

---

## [1.7.1] — 2026-05-14

### Bug fixes

- **`state_attr` removed from HA core** — `homeassistant.helpers.template.state_attr` was removed in recent Home Assistant versions, causing the integration to crash silently when reading entity attributes. Both `calculation.py` and `coordinator.py` now use a local `_state_attr()` helper that reads directly from `hass.states`. Affected paths:
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

- **Climate Debug diagnostic sensor** (`sensor.py`) — New `sensor.climate_debug_<name>` entity (category: Diagnostic) that exposes every intermediate value in the climate decision tree as attributes. Useful for understanding why the integration picked summer / winter / intermediate mode. Key attributes: `is_winter`, `is_summer`, `is_presence`, `sun_in_window`, `temp_inside`, `temp_outside`, `temp_used_winter`, `temp_used_summer`, `active_branch`, and all threshold values.

### Bug fixes

- **Switches turning OFF after HA restart** (`switch.py`) — `async_added_to_hass()` was not calling `super()`, which prevented `CoordinatorEntity` from registering its state-update listener. As a result:
  - `_handle_coordinator_update()` was never called from the coordinator after startup.
  - Lux, irradiance, and climate mode switches could appear OFF after a restart even when they should be ON.
  - Fixed by calling `await super().async_added_to_hass()` before restoring the last state.

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

- Lux sensor with configurable threshold — opens cover when light is insufficient.
- Irradiance sensor with configurable threshold.
- Individual enable/disable switches for lux and irradiance checks.

### Blind spot

- Azimuth range where adaptive positioning is suspended to avoid unfavourable sun angles.
- Configurable minimum elevation for blind spot activation.

### Tilt options

- Slat depth and spacing for accurate tilt angle calculation.
- Basic mode (angle only) and enhanced mode (angle + vertical position).

### Transparent blind

- Position adjustment to account for light transmitted through semi-transparent materials.

### Interpolation

- Custom position curve mapping sun angle to cover position.

### Sensors

- Cover Position sensor (%).
- Start Sun / End Sun timestamp sensors.
- Control Method sensor.

### Platforms

- `sensor`, `switch`, `binary_sensor`, `button`, `cover`.
