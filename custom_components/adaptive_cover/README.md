# Adaptive Cover

🇫🇷 [Documentation en français](README.fr.md)

[![Version](https://img.shields.io/badge/version-1.7.1-blue)](CHANGELOG.md)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1+-green)](https://www.home-assistant.io)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

Automatically position your covers (blinds, awnings, tilts) based on the sun's position relative to each window. The integration calculates the optimal cover position to block direct sunlight while keeping the room bright, and supports a full climate mode to react to temperature conditions.

---

## Cover types

| Type | Description |
|------|-------------|
| **Vertical blind** | Standard roller blind or curtain — position in % (0 = open, 100 = closed) |
| **Horizontal awning** | Outdoor awning projected horizontally |
| **Tilt** | Venetian blind with adjustable slat angle |

---

## Installation

### HACS (recommended)

1. In HACS, go to **Integrations → Custom repositories**
2. Add `https://github.com/basbruss/adaptive-cover` (category: Integration)
3. Search for *Adaptive Cover* and install
4. Restart Home Assistant

### Manual

1. Copy the `adaptive_cover` folder into `config/custom_components/`
2. Restart Home Assistant

---

## Configuration

Add the integration via **Settings → Devices & Services → Add integration → Adaptive Cover**.

### Basic (required)

| Option | Description |
|--------|-------------|
| **Name** | Label for this cover group |
| **Cover type** | Vertical / Horizontal / Tilt |
| **Azimuth** | Compass direction the window faces (0 = N, 90 = E, 180 = S, 270 = W) |
| **Field of view left / right** | Degrees from the window normal where sun starts/stops hitting the glass |
| **Window height** | Height of the window in metres |
| **Distance shaded area** | Depth of the area you want to keep in shade (metres) |
| **Default position** | Fallback position (%) when the sun is outside the FOV |

### Cover group

| Option | Description |
|--------|-------------|
| **Covers** | One or more `cover.*` entities controlled by this entry |

### Time window

| Option | Description |
|--------|-------------|
| **Start time / entity** | Earliest time adaptive control is active (static time or `input_datetime`) |
| **End time / entity** | Latest time adaptive control is active |
| **Sunrise offset** | Shift the start relative to sunrise (minutes, positive = later) |
| **Sunset position** | Cover position to apply at sunset |
| **Sunset offset** | Minutes before/after sunset to apply the sunset position |
| **Return at sunset** | Restore the default position instead of using sunset position |

### Position limits

| Option | Description |
|--------|-------------|
| **Enable min position** | Prevent the cover from going below a minimum % |
| **Min position** | Minimum allowed position (%) |
| **Enable max position** | Prevent the cover from going above a maximum % |
| **Max position** | Maximum allowed position (%) |

### Blind spot

Prevent the cover from stopping in a range where the sun shines directly through the gap between slats or at an extreme angle.

| Option | Description |
|--------|-------------|
| **Enable blind spot** | Activate the feature |
| **Blind spot left / right** | Azimuth range (°) that defines the blind spot |
| **Blind spot elevation** | Minimum sun elevation (°) for the blind spot to apply |

### Tilt-specific

| Option | Description |
|--------|-------------|
| **Slat depth** | Physical depth of one slat (mm) |
| **Slat distance** | Gap between slats (mm) |
| **Tilt mode** | `basic` — angle only; `enhanced` — also adjusts vertical position |

### Transparent blind

When enabled, the integration accounts for direct light passing through a semi-transparent blind and adjusts the position to compensate.

### Interpolation

Map the calculated sun-based position to a custom curve instead of a linear 0–100 scale.

| Option | Description |
|--------|-------------|
| **Enable interpolation** | Activate |
| **Interpolation start / end** | Sun angle range over which interpolation applies |
| **Interpolation list** | Comma-separated position values for the custom curve |

### Climate mode

Enable via **Settings → Devices & Services → Configure** after initial setup.

When climate mode is active, the integration picks one of three strategies:

| Branch | Condition | Cover behaviour |
|--------|-----------|-----------------|
| **Summer** | Outside (or ref) temp > `temp_high` AND sun is in FOV | Close cover to block heat |
| **Winter** | Inside temp < `temp_low` | Open cover to let passive solar heat in |
| **Intermediate** | Neither above | Fall back to standard sun-tracking |

| Option | Description |
|--------|-------------|
| **Temperature entity** | Indoor temperature sensor |
| **Outside temperature entity** | Outdoor temperature sensor (optional) |
| **Weather entity** | HA weather entity used as temperature source if no sensor |
| **Temp low** | Winter threshold (°C) — below this, open for solar gain |
| **Temp high** | Summer threshold (°C) — above this, close to block heat |
| **Use outside temperature** | Compare outside temp to `temp_high` instead of inside temp |
| **Weather condition** | Weather states considered "sunny" for climate decisions |
| **Presence entity** | Override climate logic when nobody is home |

### Light threshold

| Option | Description |
|--------|-------------|
| **Lux entity** | Illuminance sensor (`sensor.*`) |
| **Lux threshold** | Below this value (lx) the cover opens regardless of sun position |
| **Irradiance entity** | Solar irradiance sensor (`sensor.*`) |
| **Irradiance threshold** | Below this value (W/m²) the cover opens |

### Manual override

| Option | Description |
|--------|-------------|
| **Manual override duration** | Minutes to pause adaptive control after a manual move |
| **Manual override reset** | Reset manual override at a specific time of day |
| **Manual threshold** | Position delta (%) that counts as "manual" vs adaptive move |
| **Ignore intermediate positions** | Only consider fully open/closed moves as manual |

---

## Entities

Each config entry creates a device containing these entities:

### Sensors

| Entity | Description |
|--------|-------------|
| `sensor.cover_position_<name>` | Calculated target position (%) |
| `sensor.start_sun_<name>` | Timestamp when the sun enters the FOV today |
| `sensor.end_sun_<name>` | Timestamp when the sun leaves the FOV today |
| `sensor.control_method_<name>` | Active control branch (`sun` / `climate` / `manual`) |
| `sensor.climate_debug_<name>` *(diagnostic)* | Full snapshot of all climate decision inputs — see below |

### Switches

| Entity | Default | Description |
|--------|---------|-------------|
| `switch.toggle_control_<name>` | ON | Enable / disable adaptive positioning |
| `switch.manual_override_<name>` | ON | Pause adaptive control (set automatically on manual move) |
| `switch.climate_mode_<name>` | ON | Toggle climate mode (visible only when configured) |
| `switch.outside_temperature_<name>` | OFF | Use outside temp for summer detection |
| `switch.lux_<name>` | ON | Enable lux threshold check |
| `switch.irradiance_<name>` | ON | Enable irradiance threshold check |

### Binary sensor

| Entity | Description |
|--------|-------------|
| `binary_sensor.manual_control_<name>` | `ON` when any cover in the group is in manual override |

### Button

| Entity | Description |
|--------|-------------|
| `button.reset_manual_control_<name>` | Immediately clear manual override for all covers |

### Cover (global)

| Entity | Description |
|--------|-------------|
| `cover.<name>` | Aggregate cover — open/close/set position acts on **all** covers in the group; `turn_on` / `turn_off` enables or disables adaptive control |

---

## Climate Debug sensor

The `sensor.climate_debug_<name>` diagnostic sensor (visible under the device's *Diagnostic* section) exposes every intermediate value used in the climate decision tree.

| Attribute | Type | Description |
|-----------|------|-------------|
| `is_winter` | bool | Inside temp < `temp_low` |
| `is_summer` | bool | Ref temp > `temp_high` AND sun in FOV |
| `is_presence` | bool | Presence sensor active |
| `sun_in_window` | bool | Sun azimuth inside cover FOV |
| `temp_inside` | float | Raw indoor sensor value |
| `temp_outside` | float | Raw outdoor sensor value |
| `temp_used_winter` | float | Value compared against `temp_low` |
| `temp_used_summer` | float | Value compared against `temp_high` |
| `temp_low` | float | Configured winter threshold |
| `temp_high` | float | Configured summer threshold |
| `temp_switch` | bool | Outside temp is used for summer check |
| `is_sunny` | bool | Weather matches configured sunny states |
| `lux_below_threshold` | bool | Lux sensor below threshold |
| `irradiance_below_threshold` | bool | Irradiance sensor below threshold |
| `active_branch` | str | `summer` / `winter` / `intermediate` |

---

## Global cover entity

The global cover entity aggregates all physical covers in a config entry into a single controllable entity:

- **Open / Close / Set position** — moves all covers and flags them as *manual* so adaptive control does not immediately override the move.
- **`cover.turn_on`** — re-enables adaptive control and clears all manual flags.
- **`cover.turn_off`** — disables adaptive control.
- **State** — reports the average position; `closed` if all covers are at 0 %.

---

## Automation examples

### Re-enable adaptive control every morning

```yaml
automation:
  - alias: "Reset adaptive cover at sunrise"
    trigger:
      - platform: sun
        event: sunrise
    action:
      - service: cover.turn_on
        target:
          entity_id: cover.salon
```

### Manual dashboard button

```yaml
# Lovelace button card
type: button
name: Volets — mode adaptatif
tap_action:
  action: toggle
entity: switch.toggle_control_salon
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Cover doesn't move | `switch.toggle_control` is OFF | Turn the switch ON |
| Cover stuck in manual | Manual override is active | Press the reset button or wait for the override duration |
| Switches turn OFF after HA restart | Fixed in v1.7.1 | Update to latest version |
| Temperature attributes unavailable | `state_attr` helper removed in recent HA | Fixed in v1.7.1 |
| Climate branch always "intermediate" | No temperature entity configured | Add a temperature entity in options |

---

## Links

- [Changelog](CHANGELOG.md)
- [Issues](https://github.com/basbruss/adaptive-cover/issues)
- [Home Assistant Community](https://community.home-assistant.io)
