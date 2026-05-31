# Changelog

All notable changes to **Adaptive Cover** are documented here.

---

## [1.9.0] — 2026-05-30

### New features

- **Security mode** — closes covers automatically when nobody is home, protecting
  the house while respecting the climate mode's intent.

  **Activation:** security switch ON **and** presence entity reports absence.
  If no presence entity is configured on an entry, security mode is inactive
  for that entry even when the switch is ON.

  **Position rules:**

  | Situation | Position cible |
  |---|---|
  | No climate mode | 0 % (fully closed) |
  | Climate mode + summer branch | 0 % (fully closed) |
  | Climate mode + winter branch | `CONF_MIN_POSITION` (or 0 if unset) |
  | Climate mode + intermediate branch | `CONF_MIN_POSITION` (or 0 if unset) |

  **Interaction with manual override:** covers flagged as manually controlled
  (`is_cover_manual=True`) are skipped — the user's explicit action takes
  precedence. Security mode does NOT call `mark_manual_control`, so the
  automatic return to adaptive positioning is not blocked when presence
  is restored.

  **Automatic return:** when the presence entity switches back to "home",
  the presence state-change event triggers a coordinator refresh which
  re-evaluates `security_active → False` and resumes adaptive positioning.

- **Per-entry security switch** (`switch.py`) — `AdaptiveCoverSwitch("Security Mode")`
  added to each regular entry that has a presence entity configured.
  Default state: OFF. Restored on HA restart via `RestoreEntity`.

- **Hub security switch** (`switch.py`) — `AdaptiveSecurityAllSwitch`
  ("Sécurité volets") added to the "All Blinds" hub device.
  Acts on all entries that have a presence entity configured.
  Entries without a presence entity are ignored (no-op).

- **`is_presence_detected()` helper** (`helpers.py`) — shared helper that
  implements presence detection for `device_tracker`, `zone`, `binary_sensor`,
  and `input_boolean`. Both `ClimateCoverData.is_presence` and the new
  `coordinator.security_active` now delegate to this function, eliminating
  duplicate logic.

- **`CONF_SECURITY_MODE` constant** (`const.py`) — documents the runtime key
  used by the security toggle; not stored in config options (the switch manages
  the coordinator toggle directly).

### Changes

- **`calculation.py` `ClimateCoverData.is_presence`** — now delegates to
  `helpers.is_presence_detected()` instead of duplicating the domain-check logic.

- **`coordinator.py`** — new `security_toggle` property/setter, `security_active`
  property, and `_apply_security_position()` method. Security check injected into
  `async_handle_state_change`, `async_handle_first_refresh`, and
  `async_handle_timed_refresh` — security position takes priority over adaptive
  positioning when active.

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

- **Alexa name prefix** — Hub entities (cover, switch) had `_attr_has_entity_name = True`, causing Alexa to prefix their names with the device name. Fixed by setting `_attr_has_entity_name = False` on all hub entities.

---

## [1.8.6] — 2026-05-18

### Changes

- **Hub switch re-added** — `AdaptiveControlAllSwitch` re-added alongside the select.
- **Scenes simplified to 2** — `all_open` and `all_closed` only. Adaptive on/off handled by the switch.

---

## [1.8.5] — 2026-05-18

### New features

- **Hub scenes** (`scene.py`) — Position shortcuts for Alexa and automations.
- **`iter_regular_coordinators`** moved to `helpers.py`.

---

## [1.8.4] — 2026-05-18

### Changes

- **Hub select** — `AdaptiveControlModeSelect` (4 states: auto / off / all_open / all_closed) with RestoreEntity.

---

## [1.8.3] — 2026-05-15

### New features

- **Hub switch** — `AdaptiveControlAllSwitch` for adaptive on/off on all entries.

---

## [1.8.2] — 2026-05-15

### New features

- **Auto-cleanup v1.8.0 leftover device** — idempotent, one-shot per boot.
- **Auto-bootstrap hub entry** — via `SOURCE_IMPORT` if no hub exists.

---

## [1.8.1] — 2026-05-15

### Changes

- **Dedicated hub config entry** — hub cover bound to its own singleton entry.
- **Cover platform only on hub** — regular entries no longer create a cover entity on the `cover` platform.

---

## [1.8.0] — 2026-05-15

### New features

- **Singleton aggregate cover** — `AdaptiveCoverAll` controls all entries.
- **Single-lookup optimisation** — `pos_sun` and `_get_current_position`.

---

## [1.7.2] — 2026-05-15

### Bug fixes

- **`None` lux / irradiance on first refresh** — `_lux_toggle` / `_irradiance_toggle` initialised to `True` (not `None`) when configured.
- **`OptionsFlow.config_entry` read-only** — All direct assignments removed (read-only since HA 2025.12).

---

## [1.7.1] — 2026-05-14

### Bug fixes

- **`state_attr` removed from HA core** — replaced by `helpers.state_attr()`.

---

## [1.7.0] — 2026-05-08

### New features

- **Global cover entity** — open/close/set_position / turn_on / turn_off.
- **Climate Debug diagnostic sensor** — full snapshot of climate decision inputs.

### Bug fixes

- **Switches turning OFF after HA restart** — `super().async_added_to_hass()` now called.
- **`control_method` stuck in summer/winter** — `if/elif/else` fix.
- **`temperature_for_winter` / `temperature_for_summer`** — dedicated properties.
- **`start_time` not assigned** — `self._start_time` now written in static path.

---

## [1.5.0] — 2026-05-07 (baseline)

Initial tracked version. Sun tracking, three cover types, FOV, climate mode, lux/irradiance thresholds, blind spot, tilt, interpolation.
