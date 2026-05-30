# Adaptive Cover

🇫🇷 [Documentation en français](README.fr.md)

[![Version](https://img.shields.io/badge/version-1.9.0-blue)](CHANGELOG.md)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.5+-green)](https://www.home-assistant.io)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

Automatically position your covers (blinds, awnings, tilts) based on the sun's position relative to each window. A **climate mode** adapts positioning to temperature conditions, and a **security mode** closes covers automatically when nobody is home.

---

## Architecture

```mermaid
graph TB
    subgraph Inputs["Data sources"]
        SUN["☀️ sun.sun\nazimuth + elevation"]
        PRES["👤 Presence sensor"]
        ENV["🌡️ Temp / Weather / Lux / Irradiance"]
    end

    subgraph HUB["🏠 Hub Entry — All Blinds  (singleton)"]
        HC["cover.* Les volets\n↔ Alexa: open / close the blinds"]
        HS["switch.* Les volets\n↔ Alexa: activate / deactivate the blinds"]
        HSEC["switch.* Sécurité volets\n↔ Alexa: activate blind security"]
        HSEL["select.* Control mode\nauto · off · all_open · all_closed"]
        HSCN["scene.* Volets ouverts\nscene.* Volets fermés"]
    end

    subgraph ENTRY["📦 Regular entry  (one per cover group)"]
        COORD["Coordinator\n_async_update_data()"]
        COVER["cover.*\nAdaptiveCoverEntry\ncalculated position"]
        SW["switch.*\nToggle Control · Manual Override\nSecurity Mode · Climate Mode\nLux · Irradiance"]
        SEN["sensor.*\nPosition · Start Sun · End Sun\nControl Method · Climate Debug"]
        BS["binary_sensor.* Manual Control"]
        BTN["button.* Reset Manual Control"]
    end

    SUN  --> COORD
    PRES --> COORD
    ENV  --> COORD

    COORD -->|"calculated position"| COVER
    COORD --> SEN
    HUB   -.->|"iterates all coordinators"| ENTRY
```

---

## Decision flow per entry

```mermaid
flowchart TD
    UPDATE(["🔄 _async_update_data()"])
    CTRL{control_toggle\nON?}
    SEC{security_active?}
    APPLY_SEC["_apply_security_position()"]
    ADAPT["Adaptive positioning\nNormalCoverState / ClimateCoverState"]
    MOVE(["📡 set_cover_position\ncover.*"])

    UPDATE --> CTRL
    CTRL -->|NO| SKIP(["⏸ Nothing"])
    CTRL -->|YES| SEC
    SEC -->|YES| MANUAL{is_cover_manual?}
    MANUAL -->|YES| SKIP2(["⏸ Skip — manual override wins"])
    MANUAL -->|NO| APPLY_SEC --> MOVE
    SEC -->|NO| ADAPT --> MOVE
```

---

## Security mode logic

```mermaid
flowchart TD
    A(["🔒 security_toggle = ON?"])
    B{"presence_entity\nconfigured?"}
    C{"Presence\ndetected?"}
    D(["✅ Normal adaptive mode"])
    E(["🛡️ SECURITY ACTIVE"])
    F{"Climate mode\n+ winter/intermediate?"}
    G(["🔒 0% — fully closed"])
    H(["🔒 CONF_MIN_POSITION\n(or 0%)"])

    A -->|NO| D
    A -->|YES| B
    B -->|NO → no sensor| D
    B -->|YES| C
    C -->|YES → someone home| D
    C -->|NO → absent| E
    E --> F
    F -->|NO| G
    F -->|YES| H

    style E fill:#ff6b6b,color:#fff
    style G fill:#c0392b,color:#fff
    style H fill:#e67e22,color:#fff
    style D fill:#27ae60,color:#fff
```

---

## Cover types

| Type | Description |
|------|-------------|
| **Vertical blind** (`cover_blind`) | Roller blind — position in % (0 = open, 100 = closed) |
| **Horizontal awning** (`cover_awning`) | Outdoor awning |
| **Tilt** (`cover_tilt`) | Venetian blind with adjustable slat angle |

---

## Installation

### HACS (recommended)

1. In HACS → **Integrations → Custom repositories**
2. Add `https://github.com/kamahat/adaptive-cover` (category: Integration)
3. Search for *Adaptive Cover* and install
4. Restart Home Assistant

### Manual

1. Copy the `adaptive_cover` folder into `config/custom_components/`
2. Restart Home Assistant

---

## Configuration

Add via **Settings → Devices & Services → Add integration → Adaptive Cover**.

### Basic (required)

| Option | Description |
|--------|-------------|
| **Name** | Label for this cover group |
| **Cover type** | Vertical / Horizontal / Tilt |
| **Azimuth** | Window direction in degrees (0 = N, 90 = E, 180 = S, 270 = W) |
| **Field of view left / right** | Degrees from window normal where sun hits the glass |
| **Window height** | Height in metres |
| **Distance shaded area** | Depth to keep in shade (metres) |
| **Default position** | Fallback position (%) when sun is outside FOV |

### Cover group

| Option | Description |
|--------|-------------|
| **Covers** | `cover.*` entities controlled by this entry |

### Time window

| Option | Description |
|--------|-------------|
| **Start / end time or entity** | Adaptive control window |
| **Sunrise / sunset offset** | Shift in minutes |
| **Sunset position** | Position to apply at sunset |
| **Return at sunset** | Restore default instead of sunset position |

### Position limits

| Option | Description |
|--------|-------------|
| **Min position** | Minimum allowed (%) — also used by security mode in winter/intermediate |
| **Max position** | Maximum allowed (%) |

### Climate mode

Enable via **Settings → Integrations → [entry] → Configure → Climate settings**.

```mermaid
flowchart TD
    SV{"Sun in\nfield of view?"}
    DEF["Default position"]
    WIN{"WINTER?\ninside_temp < temp_low"}
    SUM{"SUMMER?\nref_temp > temp_high\nAND outside_high"}
    OPEN["100% open\n(solar gain)"]
    TRANS{"Transparent\nblind?"}
    CLOSED["0% closed\n(block heat)"]
    CALC_SUM["Calculated position\n(shading only)"]
    CLOUDS{"Overcast / low lux\nlow irradiance?"}
    CALC_INT["Calculated position\n(sun tracking)"]

    SV -->|NO| DEF
    SV -->|YES| WIN
    WIN -->|YES| OPEN
    WIN -->|NO| SUM
    SUM -->|YES| TRANS
    TRANS -->|YES| CALC_SUM
    TRANS -->|NO| CLOSED
    SUM -->|NO — intermediate| CLOUDS
    CLOUDS -->|YES| DEF
    CLOUDS -->|NO| CALC_INT

    style OPEN fill:#27ae60,color:#fff
    style CLOSED fill:#c0392b,color:#fff
    style DEF fill:#7f8c8d,color:#fff
```

> **When nobody is home** → min_position (or 0 %).

| Option | Description |
|--------|-------------|
| **Temperature entity** | Indoor sensor |
| **Outside temperature entity** | Outdoor sensor (optional) |
| **Weather entity** | Temperature source when no sensor |
| **Temp low / high** | Winter / summer thresholds (°C) |
| **Use outside temperature** | Compare outside temp to `temp_high` |
| **Weather condition** | States considered "sunny" |
| **Presence entity** | Used for both climate mode **and** security mode |

### Security mode

> Requires a **presence entity** to be configured. Without one, the switch is inactive even when ON.

**Position rules:**

| Situation | Target position |
|---|---|
| No climate mode | 0 % (fully closed) |
| Climate mode + `summer` branch | 0 % (fully closed) |
| Climate mode + `winter` or `intermediate` | `CONF_MIN_POSITION` (or 0 if unset) |

**Key behaviours:**
- Manual override wins — covers already under manual control are skipped
- Automatic return — when presence is restored, adaptive positioning resumes without any manual step
- Fail-safe — unavailable presence sensor → security inactive (no close-on-sensor-error)

### Light threshold

| Option | Description |
|--------|-------------|
| **Lux entity / threshold** | Below threshold → treated as "not sunny" |
| **Irradiance entity / threshold** | Same for irradiance |

### Manual override

| Option | Description |
|--------|-------------|
| **Manual override duration** | Minutes to pause adaptive control after a manual move |
| **Manual override reset** | Time of day to auto-reset |
| **Manual threshold** | Position delta (%) that counts as "manual" |
| **Ignore intermediate positions** | Only fully open/closed moves count |

---

## Entities

### "All Blinds" hub device

| Entity | Name | Alexa | Description |
|--------|------|-------|-------------|
| `cover.*` | Les volets | "open / close the blinds" | Aggregate cover — all entries |
| `switch.*` | Les volets | "activate / deactivate the blinds" | Adaptive control ON/OFF |
| `switch.*` | Sécurité volets | "activate blind security" | Security mode — entries with presence entity |
| `select.*` | Control mode | — | `auto` · `off` · `all_open` · `all_closed` |
| `scene.*_all_open` | Volets ouverts | "turn on Volets ouverts" | All to 100 % |
| `scene.*_all_closed` | Volets fermés | "turn on Volets fermés" | All to 0 % |

### Regular entry device

#### Switches

| Entity | Default | Description |
|--------|---------|-------------|
| `switch.toggle_control_<name>` | ON | Enable / disable adaptive positioning |
| `switch.manual_override_<name>` | ON | Pause adaptive control (auto-set on manual move) |
| `switch.security_mode_<name>` | **OFF** | **Security mode** — closes covers when no presence *(visible when presence entity configured)* |
| `switch.climate_mode_<name>` | ON | Toggle climate mode *(visible when configured)* |
| `switch.outside_temperature_<name>` | OFF | Use outside temp for summer detection |
| `switch.lux_<name>` | ON | Enable lux threshold |
| `switch.irradiance_<name>` | ON | Enable irradiance threshold |

#### Other entities

| Entity | Description |
|--------|-------------|
| `cover.<name>` | **Main entity** — adaptive position; open/close/set_position on this group |
| `sensor.cover_position_<name>` | Calculated target position (%) |
| `sensor.start_sun_<name>` / `sensor.end_sun_<name>` | Timestamps when sun enters/leaves FOV |
| `sensor.control_method_<name>` | Active branch (`summer` / `winter` / `intermediate`) |
| `sensor.climate_debug_<name>` *(diagnostic)* | Full climate decision snapshot |
| `binary_sensor.manual_control_<name>` | ON when any cover in the group is in manual override |
| `button.reset_manual_control_<name>` | Immediately clear manual override |

---

## Alexa integration

| Alexa command | Entity | Action |
|---------------|--------|--------|
| "open the blinds" | `cover.*` hub | → 100 % |
| "close the blinds" | `cover.*` hub | → 0 % |
| "activate the blinds" | `switch.*` adaptive hub | Adaptive ON |
| "deactivate the blinds" | `switch.*` adaptive hub | Adaptive OFF |
| "activate blind security" | `switch.*` security hub | Security ON |
| "deactivate blind security" | `switch.*` security hub | Security OFF |
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

### Evening close via select

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
| Cover stuck in manual | Manual override active | Press reset button or wait |
| Cover stays closed after returning home | Security switch ON + presence entity absent or unavailable | Check presence sensor |
| Security switch not visible | No presence entity configured | Add `presence_entity` in entry options |
| Climate branch always "intermediate" | No temperature entity | Add a temperature sensor |
| Duplicate cover entity on device | Legacy v1.7.x residue | Auto-fixed on startup (v1.8.11+) |

---

## Links

- [Changelog](CHANGELOG.md)
- [Operational Runbook (FR)](RUNBOOK.fr.md)
- [Releases](https://github.com/kamahat/adaptive-cover/releases)
- [Issues](https://github.com/kamahat/adaptive-cover/issues)
- [Home Assistant Community](https://community.home-assistant.io)
