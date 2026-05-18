# Changelog

All notable changes to **Adaptive Cover** are documented here.

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
