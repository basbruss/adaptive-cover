# Changelog

All notable changes to **Adaptive Cover** are documented here.

---

## [1.8.10] — 2026-05-25

### Improvement — absent mode closes to minimum position

When nobody is home (`presence_entity = off`), covers now close to the **configured minimum position** (`min_pos`) instead of 0 %.

The "apply min position only when sun is in front of the window" flag (`min_pos_bool`) is intentionally ignored in absent mode — privacy and energy savings take priority over the sun-tracking condition.

| Scenario | Before (v1.8.9) | After (v1.8.10) |
|---|---|---|
| Away, min_pos = 20 % | 0 % (fully closed) | **20 %** (min position) |
| Away, no min_pos configured | 0 % | 0 % (unchanged) |

Applies to vertical/horizontal covers (`normal_without_presence`) and tilt blinds (`tilt_without_presence`).

---

## [1.8.9] — 2026-05-25

### Bug fix — covers do not close when presence sensor is OFF

When `binary_sensor.presence_at_home` (or any binary/boolean presence entity) turned **off**, covers were expected to close but stayed at their default position in two situations:

1. **Intermediate season** (temperature between `temp_low` and `temp_high`) — `normal_without_presence` only closed covers in summer mode; in intermediate mode it fell through to `self.cover.default`.
2. **Sun outside the window FOV** — regardless of season, when the sun was not directly in front of the window the function also fell through to `self.cover.default`.

Fix (`calculation.py` — `ClimateCoverState`):

| Function | Before | After |
|---|---|---|
| `normal_without_presence` | Close (0 %) only when summer **and** sun in FOV; otherwise `default` | **Always 0 %** — no one home → always closed |
| `tilt_without_presence` | Fall back to `NormalCoverState.get_state()` when sun outside FOV | **Always 0 %** — no one home → always closed |

> **Note**: the presence entity is only evaluated when **Climate Mode** is enabled for the entry. Entries without climate mode are unaffected.

---

## [1.8.8] — 2026-05-18

### Bug fix — Alexa shows "All Blinds Volets ouverts" for scenes

Alexa cached the scene names created before v1.8.7 ("All Blinds Volets ouverts") and did not refresh them even after re-discovery, because it matched the entities by their existing unique IDs.

Fix: `unique_id` of both hub scenes now carries a `_v2` suffix, forcing HA to create fresh entity registry entries with the correct names ("Volets ouverts" / "Volets fermés"). Alexa will see them as new scenes on the next discovery.

> **Note**: the old orphan scene entries (`scene.all_blinds_volets_ouverts` / `scene.all_blinds_volets_fermes`) can be deleted from HA's entity registry after upgrading (Settings → Entities → filter "all_blinds").

---

## [1.8.7] — 2026-05-18

### Bug fix — Alexa shows "All Blinds …" prefix

Alexa was displaying entity names prefixed with the device name ("All Blinds Tous les volets", "All Blinds Les volets") because all hub entities had `_attr_has_entity_name = True`, which instructs HA to prepend the device name to the friendly name.

Fix: all hub-device entities now use `_attr_has_entity_name = False` with explicit French names. Alexa reads the name directly, without the device prefix.

| Entity | Before | After |
|---|---|---|
| Cover | "All Blinds Tous les volets" | **"Les volets"** |
| Switch | "All Blinds Les volets" | **"Les volets"** |
| Scene all_open | "All Blinds Volets ouverts" | **"Volets ouverts"** |
| Scene all_closed | "All Blinds Volets fermés" | **"Volets fermés"** |

Cover and switch share the name "Les volets" — Alexa routes correctly by verb type (open/close → cover; active/désactive → switch). Translation keys for switch and scene names removed (hardcoded French names).

---

## [1.8.6] — 2026-05-18

### Alexa voice control

Complete Alexa voice control for the "All Blinds" hub device via native entity types:

| Phrase | Entité | Type |
|---|---|---|
| *"Alexa, active les volets"* | switch **Les volets** ON | Switch |
| *"Alexa, désactive les volets"* | switch **Les volets** OFF | Switch |
| *"Alexa, ouvre les volets"* | cover **Tous les volets** open | Cover (existant) |
| *"Alexa, ferme les volets"* | cover **Tous les volets** close | Cover (existant) |

- **`switch.py`** — `AdaptiveControlAllSwitch` re-added for hub entries with translation key `hub_control` (FR: "Les volets", EN: "Blinds"). ON enables adaptive control + clears manual overrides; OFF disables it.
- **`scene.py`** — simplified to two scenes only: **Volets ouverts** and **Volets fermés** (position shortcuts for automations). Scenes `auto` and `off` removed — covered by the switch.
- **`__init__.py`** — `HUB_PLATFORMS` now includes `Platform.SWITCH` alongside cover, select and scene.
- **Translations** — added `entity.switch.hub_control` (FR: "Les volets") ; scene keys reduced to `scene_all_open` / `scene_all_closed`.

---

## [1.8.5] — 2026-05-18

### New feature

- **4 scene entities on the hub** (`scene.py`) — the "All Blinds" device now exposes four `SceneEntity` objects alongside the existing control-mode select. Scenes are natively supported by Alexa, Google Assistant and Assist:
  - **Auto** (`scene.all_blinds_auto`) — enables adaptive positioning; clears all manual overrides.
  - **Arrêt / Off** (`scene.all_blinds_off`) — disables adaptive positioning; covers stay in place.
  - **Tous ouverts / All open** (`scene.all_blinds_all_open`) — moves every cover to 100 %; manual override activated.
  - **Tous fermés / All closed** (`scene.all_blinds_all_closed`) — moves every cover to 0 %; manual override activated.
  Voice example: *"Alexa, activate Tous fermés"*
- **`helpers.py`** — `iter_regular_coordinators()` extracted as a shared helper (was duplicated in `select.py`); imported by both `select.py` and `scene.py`.
- **`__init__.py`** — `HUB_PLATFORMS` now includes `Platform.SCENE`.
- **Translations** (`en.json` / `fr.json`) — added `entity.scene.*` section with localized names for all four scenes.

---

## [1.8.4] — 2026-05-18

### New feature

- **4-state control select on the hub** (`select.py`) — the "All Blinds" device now exposes a **Control mode** select entity replacing the former ON/OFF switch. Four options:
  - **Auto** — enables adaptive positioning on every regular entry and clears any active manual overrides.
  - **Off** — disables adaptive positioning everywhere; covers stay in their current position.
  - **All open** — moves every cover to 100 % and activates manual override (reverts automatically after the configured override duration).
  - **All closed** — moves every cover to 0 % and activates manual override (same revert behaviour).
  State is restored across HA restarts.
- **`__init__.py`** — `HUB_PLATFORMS` now includes `Platform.SELECT` instead of `Platform.SWITCH`.
- **`switch.py`** — hub early-return and `AdaptiveControlAllSwitch` class removed; the switch platform now only registers entities for regular (per-cover) entries.
- **Translations** (`en.json` / `fr.json`) — added `entity.select.adaptive_control_mode` with localized state labels for all four options.

---

## [1.8.3] — 2026-05-15

### New feature

- **Adaptive Control switch on the hub** (`switch.py`) — the "All Blinds" device now exposes an `Adaptive Control` switch in addition to the aggregate cover. Flipping it ON enables adaptive positioning on every regular entry and clears any active manual overrides; flipping it OFF disables adaptive positioning everywhere. State is an *AND* across every entry — the switch reads ON only when adaptive control is active on all of them. Visible directly in the device card UI.
- **`__init__.py`** — `HUB_PLATFORMS` now includes `Platform.SWITCH` so the hub entry sets up its switch alongside the cover.

---

## [1.8.2] — 2026-05-15

### Bug fixes / migration

- **Auto-cleanup of v1.8.0 leftover device** (`__init__.py`) — v1.8.0 created an implicit aggregate device with identifier `(DOMAIN, "all_covers")` attached to whichever config entry happened to load first. v1.8.1 stopped creating it but left the orphan record in HA's device registry, so users still saw a phantom "Adaptive Cover" device under their first one or two regular entries. v1.8.2 explicitly removes that device on first setup after upgrade (one-shot, idempotent).
- **Auto-bootstrap of the hub entry** (`__init__.py` + `config_flow.py`) — when no `is_hub` config entry exists, the integration now creates one automatically on first setup of any regular entry, via an `import`-source flow. No more "where's the All-Blinds entry?" — it just appears.
- **`async_step_import`** added to `ConfigFlowHandler` so the bootstrap can run without showing a UI popup; reuses the `single_instance_allowed` guard.

---

## [1.8.1] — 2026-05-15

### Breaking change — "All Blinds" is now a dedicated config entry

Following user feedback after v1.8.0: the singleton aggregate cover was implicitly attached to whichever config entry happened to be loaded first, which made the integration layout asymmetric (the "Adaptive Cover" device appeared under one or two random per-cover entries).

The aggregate is now exposed via its own **dedicated config entry** "All Blinds", visible at the same level as the per-cover entries.

- **`config_flow.py`** — the initial step is now a menu offering:
  - *Add a cover group* (Vertical / Horizontal / Tilt) — original behaviour
  - *Add 'All Blinds' aggregator* — creates the hub entry (one per integration)
- **`__init__.py`** — hub entries skip coordinator creation and only set up the `cover` platform. Regular entries unchanged.
- **`cover.py`** — the aggregate `cover.tous_les_volets` is registered only when the hub entry is set up. Regular entries no longer create any cover entity.
- **Options flow** — opening the hub entry's options shows an abort dialog ("no per-cover options").
- **Re-entry guard** — only one hub entry is allowed per integration; a second attempt aborts cleanly with `single_instance_allowed`.

*Migration:* old per-entry aggregates (`cover.<name>_tous_les_volets_...`) are removed when v1.8.0 was used. After upgrading to v1.8.1, click "Add entry → Add 'All Blinds' aggregator" to recreate the singleton with a clean device layout.

### Translations

- **EN / FR** — added `user.menu_options`, `cover_entry`, and `abort.*` strings for both new flows.

---

## [1.8.0] — 2026-05-15

### Breaking change

- **Singleton « Tous les volets » entity** (`cover.py`) — previously each config entry exposed its own `cover.tous_les_volets_<name>` aggregate, producing as many redundant entities as there were entries (even when an entry only had one cover). The integration now exposes a **single** integration-level entity `cover.adaptive_cover_tous_les_volets` that aggregates every cover across every Adaptive Cover entry.

  *Migration:* old per-entry aggregates (e.g. `cover.avr_chambre_adultes_tous_les_volets_avr_adulte`, `cover.avr_aline_tous_les_volets_avr_aline`) will be removed automatically by HA. Any automations referencing them must be updated to use the new singleton.

### Performance

- **`pos_sun`** (`coordinator.py`) — sun azimuth and elevation now share a single `hass.states.get("sun.sun")` lookup instead of two.
- **`_get_current_position`** (`coordinator.py`) — cover position read in one state lookup (was two indirect lookups via `_state_attr`).
- **`AdaptiveCoverAll._collect_positions`** (`cover.py`) — a single pass over `hass.states` for both `is_closed` and `current_cover_position` (previously two full passes per attribute access).

### Refactor

- **`state_attr` centralised** in `helpers.py` — removes the duplicated `_state_attr()` definitions previously living in `coordinator.py` and `calculation.py`. Single source of truth, easier to test.
- **`async_unload_entry`** (`__init__.py`) — when the last config entry is unloaded, the internal global-cover flag is now cleared, so re-adding an entry properly re-registers the singleton.

### Robustness

- **`_collect_positions`** (`cover.py`) — wraps `int(pos)` in `try/except` to defensively skip covers reporting non-numeric `current_position` (e.g. transient `unknown` strings).

---

## [1.7.2] — 2026-05-15

### Bug fixes

- **Guard `None` sur lux / irradiance** (`calculation.py`) — `float(value)` levait une `TypeError` quand le capteur lux ou irradiance était indisponible (`get_safe_state()` retournait `None`). Un contrôle explicite `if value is None: return False` est maintenant appliqué avant la conversion, évitant tout crash silencieux. (upstream PR #458)

- **`OptionsFlow.config_entry` lecture seule depuis HA 2025.12** (`config_flow.py`) — HA 2024.12 avait déprécié l'assignation de `self.config_entry` dans un `OptionsFlow` ; HA 2025.12 en a fait une propriété en lecture seule (core#155958), provoquant `AttributeError` à chaque reconfiguration de l'intégration. La ligne `self.config_entry = config_entry` est supprimée — le framework injecte automatiquement la valeur. (upstream PR #437/#438/#364/#348)

### Traductions

- **Espagnol (`es.json`)** — correction d'une erreur dans la traduction espagnole. (upstream PR #457)

### Dépendances

- `homeassistant` : `2023.11.1` → `2026.5.1`
- `python` : `^3.11` → `^3.12`
- `hass-nabucasa` : `0.75.1` → `2.2.0`
- `pandas` : `~=2.2` → `~=3.0`
- `pre-commit` : `4.0.1` → `4.6.0`
- `pre-commit-hooks` : `5.0.0` → `6.0.0`
- `pylint` : `4.0.2` → `4.0.5`
- `ruff` : `0.9.1` → `0.15.13`
- `pip` : `>=24.1.1,<25.4` → `>=26.0.0`
- `colorlog` : `~=6.8` → `~=6.10`
- `pvlib` : `~=0.11` → `~=0.15`
- `matplotlib` : `~=3.9` → `~=3.10`
- `ipykernel` : `~=6.29` → `~=7.2`

### Documentation

- README anglais et français entièrement réécrits : schéma Mermaid du flowchart de décision, tableaux de variables complets avec valeurs par défaut et plages, section Modes détaillée, entités v1.7.x, suppression de la section Blueprint dépréciée.
- Badge Home Assistant `2026.05+` ajouté dans les deux README.
- `README.fr.md` ajouté à la racine du dépôt.
- `CHANGELOG.md` ajouté à la racine du dépôt.

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
