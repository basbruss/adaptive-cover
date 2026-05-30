# Adaptive Cover

🇫🇷 [Documentation en français](README.fr.md)

[![Version](https://img.shields.io/badge/version-1.9.0-blue)](CHANGELOG.md)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.5+-green)](https://www.home-assistant.io)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

Automatically position your covers (blinds, awnings, tilts) based on the sun's position relative to each window. The integration calculates the optimal cover position to block direct sunlight while keeping the room bright, supports a full climate mode to react to temperature conditions, and includes a **security mode** that closes covers automatically when nobody is home.

---

## Architecture

```
Home Assistant
└── Adaptive Cover (DOMAIN: adaptive_cover)
    │
    ├── Hub entry "All Blinds" (is_hub=True) ← singleton, auto-created
    │   ├── cover.*             — "Les volets"        → Alexa "open / close the blinds"
    │   ├── switch.* (adaptive) — "Les volets"        → Alexa "activate / deactivate the blinds"
    │   ├── switch.* (security) — "Sécurité volets"   → Alexa "activate blind security"
    │   ├── select.*            — Control mode (auto / off / all_open / all_closed)
    │   └── scene.*             — "Volets ouverts" / "Volets fermés"
    │
    └── Regular entries (one per cover group)
        ├── cover.*         — AdaptiveCoverEntry (adaptive position of this group)
        ├── sensor.*        — Position / Start Sun / End Sun / Control Method / Climate Debug
        ├── switch.*        — Toggle Control / Manual Override / Security Mode /
        │                     Climate Mode / Lux / Irradiance
        ├── binary_sensor.* — Manual Control
        └── button.*        — Reset Manual Control
```

**Data flow per regular entry:**

```
sun.sun ──► Coordinator ──► security_active ?
                │                 │ YES → _apply_security_position()
   sensors ────►│                 │ NO  → NormalCoverState / ClimateCoverState
   presence     │                        │
   weather      │                        ▼ calculated position (0-100 %)
   lux/irr.     │            apply_max / apply_min / interpolation
                └──► AdaptiveCoverEntry.current_cover_position → cover.*
```

---

## Cover types

| Type | Description |
|------|-------------|
| **Vertical blind** (`cover_blind`) | Standard roller blind — position in % (0 = open, 100 = closed) |
| **Horizontal awning** (`cover_awning`) | Outdoor awning projected horizontally |
| **Tilt** (`cover_tilt`) | Venetian blind with adjustable slat angle |

---

## Installation

### HACS (recommended)

1. In HACS, go to **Integrations → Custom repositories**
2. Add `https://github.com/kamahat/adaptive-cover` (category: Integration)
3. Search for *Adaptive Cover* and install
4. Restart Home Assistant

### Manual

1. Copy the `adaptive_cover` folder into `config/custom_components/`
2. Restart Home Assistant

---

## Configuration

Add the integration via **Settings → Devices & Services → Add integration → Adaptive Cover**.

On first start, the menu offers three choices:
- **Add cover group** — configure a cover group (vertical / horizontal / tilt)
- **All Blinds** — create the hub entry manually (normally auto-created)
- **Import** — internal use (automatic bootstrap)

### Basic (required)

| Option | Description |
|--------|-------------|
| **Name** | Label for this cover group |
| **Cover type** | Vertical / Horizontal / Tilt |
| **Azimuth** | Window direction in degrees (0 = N, 90 = E, 180 = S, 270 = W) |
| **Field of view left / right** | Degrees from the window normal where sun starts/stops hitting the glass |
| **Window height** | Height in metres |
| **Distance shaded area** | Depth to keep in shade (metres) |
| **Default position** | Fallback position (%) when sun is outside FOV |

### Cover group

| Option | Description |
|--------|-------------|
| **Covers** | One or more `cover.*` entities controlled by this entry |

### Time window

| Option | Description |
|--------|-------------|
| **Start / end time or entity** | Adaptive control window (static time or `input_datetime`) |
| **Sunrise / sunset offset** | Shift in minutes relative to sunrise / sunset |
| **Sunset position** | Position to apply at sunset |
| **Return at sunset** | Restore default instead of applying sunset position |

### Position limits

| Option | Description |
|--------|-------------|
| **Enable min position** | Prevent cover from going below a threshold |
| **Min position** | Minimum allowed position (%) — also used by security mode in winter/intermediate |
| **Enable max position** | Prevent cover from going above a threshold |
| **Max position** | Maximum allowed position (%) |

### Blind spot

| Option | Description |
|--------|-------------|
| **Enable blind spot** | Activate |
| **Blind spot left / right** | Azimuth range (°) |
| **Blind spot elevation** | Minimum sun elevation (°) to apply |

### Tilt-specific

| Option | Description |
|--------|-------------|
| **Slat depth** | Physical depth of one slat (mm) |
| **Slat distance** | Gap between slats (mm) |
| **Tilt mode** | `mode1` — single direction (0°–90°); `mode2` — bi-directional (0°–180°) |

### Transparent blind

Accounts for light passing through a semi-transparent blind.

### Interpolation

Map the sun-based position to a custom curve instead of linear 0–100.

### Climate mode

Enable via **Settings → Devices & Services → Configure** after initial setup.

#### Decision tree (presence = true)

```
Sun in field of view?
├─ NO  → default position
└─ YES
    ├─ WINTER (inside_temp < temp_low) → 100% open (solar gain)
    ├─ SUMMER (ref_temp > temp_high AND outside_high)
    │   ├─ transparent blind → calculated (shading only)
    │   └─ opaque blind      → 0% closed
    └─ INTERMEDIATE
        ├─ overcast / low lux / low irradiance → default position
        └─ sunny → calculated (shading only)
```

When **nobody is home** → min_position (or 0 %).

| Option | Description |
|--------|-------------|
| **Temperature entity** | Indoor temperature sensor |
| **Outside temperature entity** | Outdoor sensor (optional) |
| **Weather entity** | HA weather entity as temperature source |
| **Temp low** | Winter threshold (°C) |
| **Temp high** | Summer threshold (°C) |
| **Use outside temperature** | Compare outside temp to `temp_high` |
| **Weather condition** | States considered "sunny" |
| **Presence entity** | Used for both climate mode **and** security mode |

### Security mode

Security mode closes covers automatically when nobody is home.

**Activation:** security switch = ON **AND** presence entity reports absence.

> Requires a **presence entity** to be configured. Without one, the switch
> has no effect even when ON.

#### Security decision tree

```
security_switch = ON?
└─ YES → presence_entity configured?
    ├─ NO  → inactive (no sensor = no security)
    └─ YES → presence detected?
        ├─ YES → normal adaptive mode (security inactive)
        └─ NO  → security ACTIVE
            ├─ Climate mode ON + winter or intermediate branch
            │   → close to CONF_MIN_POSITION (or 0 if not set)
            └─ All other cases (no climate, or summer branch)
                → close to 0% (fully closed)
```

**Key behaviours:**
- Security overrides adaptive positioning (higher priority)
- Covers in **manual override are skipped** — the user's explicit action takes precedence
- **Automatic return:** when presence is restored, the coordinator re-evaluates `security_active → False` and resumes adaptive positioning without any manual step
- Security does NOT set `manual_control` flag — the automatic return is never blocked

### Light threshold

| Option | Description |
|--------|-------------|
| **Lux entity / threshold** | Below threshold → treated as "not sunny" |
| **Irradiance entity / threshold** | Same for irradiance |

### Manual override

| Option | Description |
|--------|-------------|
| **Manual override duration** | Minutes to pause adaptive control after a manual move |
| **Manual override reset** | Time of day to auto-reset manual override |
| **Manual threshold** | Position delta (%) that counts as "manual" |
| **Ignore intermediate positions** | Only fully open/closed moves count as manual |

---

## Entities

### "All Blinds" hub device

| Entity | Name | Alexa | Description |
|--------|------|-------|-------------|
| `cover.*` | Les volets | "open / close the blinds" | Aggregate cover — all entries |
| `switch.*` (adaptive) | Les volets | "activate / deactivate the blinds" | Adaptive control ON/OFF |
| `switch.*` (security) | Sécurité volets | "activate blind security" | Security mode ON/OFF — entries with presence entity |
| `select.*` | Control mode | — | 4-state dropdown |
| `scene.*_all_open` | Volets ouverts | "turn on Volets ouverts" | All to 100 % |
| `scene.*_all_closed` | Volets fermés | "turn on Volets fermés" | All to 0 % |

#### Control mode select states

| State | Behaviour |
|-------|-----------|
| `auto` | Adaptive ON, manual overrides cleared |
| `off` | Adaptive OFF, covers stay in place |
| `all_open` | All covers to 100 % |
| `all_closed` | All covers to 0 % |

### Regular entry device

#### Cover

| Entity | Description |
|--------|-------------|
| `cover.<name>` | **Main entity** — adaptive position; open/close/set_position on this group |

#### Sensors

| Entity | Description |
|--------|-------------|
| `sensor.cover_position_<name>` | Calculated target position (%) |
| `sensor.start_sun_<name>` | Timestamp when sun enters FOV today |
| `sensor.end_sun_<name>` | Timestamp when sun leaves FOV today |
| `sensor.control_method_<name>` | Active branch (`summer` / `winter` / `intermediate`) |
| `sensor.climate_debug_<name>` *(diagnostic)* | Full climate decision snapshot |

#### Switches

| Entity | Default | Description |
|--------|---------|-------------|
| `switch.toggle_control_<name>` | ON | Enable / disable adaptive positioning |
| `switch.manual_override_<name>` | ON | Pause adaptive control (auto-set on manual move) |
| `switch.security_mode_<name>` | **OFF** | **Security mode** — closes covers when no presence (visible when presence entity configured) |
| `switch.climate_mode_<name>` | ON | Toggle climate mode (visible when configured) |
| `switch.outside_temperature_<name>` | OFF | Use outside temp for summer detection |
| `switch.lux_<name>` | ON | Enable lux threshold |
| `switch.irradiance_<name>` | ON | Enable irradiance threshold |

#### Binary sensor

| Entity | Description |
|--------|-------------|
| `binary_sensor.manual_control_<name>` | ON when any cover in the group is in manual override |

#### Button

| Entity | Description |
|--------|-------------|
| `button.reset_manual_control_<name>` | Immediately clear manual override for all covers |

---

## Climate Debug sensor

`sensor.climate_debug_<name>` — visible in the device's *Diagnostic* section.

| Attribute | Type | Description |
|-----------|------|-------------|
| `is_winter` | bool | Inside temp < `temp_low` |
| `is_summer` | bool | Ref temp > `temp_high` AND `outside_high` |
| `is_presence` | bool | Presence entity active |
| `sun_in_window` | bool | Sun in FOV |
| `temp_inside` | float | Raw indoor sensor value |
| `temp_outside` | float | Raw outdoor sensor value |
| `temp_used_winter` | float | Value compared to `temp_low` |
| `temp_used_summer` | float | Value compared to `temp_high` |
| `temp_low` | float | Configured winter threshold |
| `temp_high` | float | Configured summer threshold |
| `temp_switch` | bool | Outside temp used for summer check |
| `is_sunny` | bool | Weather matches sunny states |
| `lux_below_threshold` | bool | Lux below threshold |
| `irradiance_below_threshold` | bool | Irradiance below threshold |
| `active_branch` | str | `summer` / `winter` / `intermediate` |

---

## Alexa integration

| Alexa command | Target entity | Action |
|---------------|---------------|--------|
| "open the blinds" | `cover.*` (hub) | `open_cover` → 100 % |
| "close the blinds" | `cover.*` (hub) | `close_cover` → 0 % |
| "activate the blinds" | `switch.*` adaptive (hub) | Adaptive ON |
| "deactivate the blinds" | `switch.*` adaptive (hub) | Adaptive OFF |
| "activate blind security" | `switch.*` security (hub) | Security ON |
| "deactivate blind security" | `switch.*` security (hub) | Security OFF |
| "turn on Volets ouverts" | `scene.*_all_open` | All to 100 % |
| "turn on Volets fermés" | `scene.*_all_closed` | All to 0 % |

---

## Automation examples

### Activate security on departure

```yaml
automation:
  - alias: "Security mode on departure"
    trigger:
      - platform: state
        entity_id: binary_sensor.presence_home
        to: "off"
        for: "00:05:00"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.security_mode_salon
```

### Re-enable adaptive control at sunrise

```yaml
automation:
  - alias: "Reset adaptive cover at sunrise"
    trigger:
      - platform: sun
        event: sunrise
    action:
      - service: cover.turn_on
        target:
          entity_id: cover.les_volets
```

### Evening mode via select

```yaml
automation:
  - alias: "Close all blinds in the evening"
    trigger:
      - platform: time
        at: "21:00:00"
    action:
      - service: select.select_option
        target:
          entity_id: select.control_mode
        data:
          option: all_closed
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Cover doesn't move | `switch.toggle_control` is OFF | Turn the switch ON |
| Cover stuck in manual | Manual override active | Press reset button or wait for duration |
| Switches OFF after restart | Fixed in v1.7.0 | Update to latest |
| Temperature attributes unavailable | `state_attr` removed from HA core | Fixed in v1.7.1 |
| Climate branch always "intermediate" | No temperature entity configured | Add a temperature sensor |
| Cover stays closed after returning home | Security switch still ON and presence entity missing | Check `switch.security_mode` or add `presence_entity` |
| Security switch not visible | No presence entity configured | Add `presence_entity` in entry options |
| Duplicate cover entity on device | Legacy v1.7.x residue | Auto-fixed on startup in v1.8.11 |

---

## Links

- [Changelog](CHANGELOG.md)
- [Operational Runbook (FR)](RUNBOOK.fr.md)
- [Issues](https://github.com/kamahat/adaptive-cover/issues)
- [Home Assistant Community](https://community.home-assistant.io)
