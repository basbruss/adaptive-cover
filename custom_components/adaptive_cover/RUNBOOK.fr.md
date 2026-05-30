# Adaptive Cover — Runbook opérationnel

Version cible : **1.9.0**  
Dépôt : `https://github.com/kamahat/adaptive-cover`

---

## 1. Procédure de release

### Prérequis

- Accès SSH à **claude-mgmt** (`192.168.20.150`)
- `GITHUB_TOKEN` exporté dans `~/.bashrc` sur claude-mgmt

### Étapes

```bash
# 1. Connexion à claude-mgmt
plink -batch -i "C:\Users\yoyo\Documents\_moa\ssh_key_home_ecdsa.ppk" root@192.168.20.150

# 2. Bumper la version (remplacer X.Y.Z)
NEW_VERSION="X.Y.Z"
sed -i "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/" manifest.json
sed -i "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml
sed -i "s/version-[0-9.]*-blue/version-$NEW_VERSION-blue/" README.fr.md README.md

# 3. Mettre à jour CHANGELOG.md (ajouter section ## [X.Y.Z])

# 4. Commit et push
git add -A && git commit -m "release: v$NEW_VERSION" && git push origin main

# 5. Créer la release GitHub via l'API
python3 - <<'EOF'
import json, subprocess, urllib.request
token = subprocess.run(
    ["bash", "-i", "-c", "echo $GITHUB_TOKEN"],
    capture_output=True, text=True
).stdout.strip()
NEW_VERSION = "X.Y.Z"  # à remplacer
data = json.dumps({
    "tag_name": f"v{NEW_VERSION}",
    "name": f"v{NEW_VERSION}",
    "body": "Voir CHANGELOG.md",
    "draft": False, "prerelease": False,
}).encode()
req = urllib.request.Request(
    "https://api.github.com/repos/kamahat/adaptive-cover/releases",
    data=data,
    headers={"Authorization": f"token {token}", "Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req) as r:
    print(json.load(r)["html_url"])
EOF
```

### Checklist pré-release

- [ ] `manifest.json` version à jour
- [ ] `CHANGELOG.md` section ajoutée avec date et description
- [ ] `README.fr.md` et `README.md` badges mis à jour
- [ ] Tests manuels : restart HA, volet se positionne, sécurité ferme en absence, retour adaptatif à la présence, Alexa répond

---

## 2. Diagnostic des problèmes courants

### 2.1 Volet ne bouge pas

1. Vérifier `switch.toggle_control_<nom>` → doit être ON
2. Vérifier `binary_sensor.manual_control_<nom>` → si ON, appuyer sur `button.reset_manual_control_<nom>`
3. Vérifier `sensor.control_method_<nom>` → doit afficher `sun`, `summer`, `winter` ou `intermediate`
4. Vérifier que l'heure courante est dans la fenêtre `start_time` / `end_time`
5. Vérifier `sensor.start_sun` et `sensor.end_sun`

### 2.2 Branche climatique incorrecte

Lire `sensor.climate_debug_<nom>` :

```
Attributs clés :
  is_winter              → temp_inside < temp_low ?
  is_summer              → temp_ref > temp_high AND outside_high ?
  sun_in_window          → soleil dans le champ de vision ?
  active_branch          → summer / winter / intermediate
  temp_used_winter       → valeur comparée à temp_low (intérieure)
  temp_used_summer       → valeur comparée à temp_high (extérieure si temp_switch=True)
  lux_below_threshold    → si True, mode intermédiaire → position par défaut
  irradiance_below_threshold → idem
```

### 2.3 Mode sécurité — volets restent fermés malgré retour à la maison

**Diagnostic pas à pas :**

1. Vérifier que `switch.security_mode_<nom>` est bien ON
2. Vérifier l'état du capteur de présence :
   ```
   États attendus selon le domaine :
     device_tracker → "home"
     zone           → > 0
     binary_sensor  → "on"
     input_boolean  → "on"
   ```
3. Vérifier dans les logs HA que `security_active` est bien `False` après le retour :
   ```
   grep "Security active" home-assistant.log
   ```
4. Si `switch.security_mode` est OFF mais les volets sont toujours fermés → override manuel actif — appuyer sur le bouton reset.
5. Si le capteur de présence est `unavailable` → `is_presence_detected` retourne `True` (fail-safe), sécurité inactive — vérifier la connectivité du capteur.

**Cause fréquente :** le switch sécurité est resté ON mais le capteur de présence est absent ou unavailable.

### 2.4 Switch sécurité absent (non visible dans HA)

Cause : aucun `presence_entity` configuré dans les options de l'entrée.  
Solution : aller dans **Paramètres → Intégrations → Adaptive Cover → [entrée] → Configurer → Paramètres climatiques** → ajouter un capteur de présence.

### 2.5 Hub "All Blinds" absent après installation

L'entrée hub est créée automatiquement lors du premier démarrage d'une entrée régulière.  
Si absente → créer manuellement via **Paramètres → Intégrations → Adaptive Cover → Configurer → All Blinds**, ou redémarrer HA.

### 2.6 Entités cover dupliquées sur un appareil

Résidu d'une version < 1.8.11. `_cleanup_orphan_cover_entities()` s'exécute automatiquement au chargement. Redémarrer HA suffit.

### 2.7 Interrupteurs OFF après redémarrage

Résolu en v1.7.0. Si le problème persiste → mettre à jour via HACS.

### 2.8 Alexa ne comprend pas "active la sécurité des volets"

Vérifier que le switch hub a bien `_attr_has_entity_name = False` et `_attr_name = "Sécurité volets"`.  
Procédure : demander à Alexa "découvre mes appareils".

---

## 3. Migrations

### 3.1 Depuis < 1.9.0 (ajout mode sécurité)

Aucune migration de données nécessaire. Le switch sécurité est créé automatiquement au redémarrage si `presence_entity` est configuré. Il démarre en état OFF (désactivé par défaut).

### 3.2 Depuis < 1.8.0

L'entrée hub est créée automatiquement. L'ancien device `(DOMAIN, "all_covers")` est supprimé par `_cleanup_v18_leftover_device()`. Aucune action manuelle.

### 3.3 Depuis < 1.7.1 (state_attr supprimé de HA core)

Mettre à jour. Le helper `state_attr()` local dans `helpers.py` remplace l'ancien import.

---

## 4. Points d'attention au développement

| Point | Détail |
|-------|--------|
| `security_active` | Retourne False si `presence_entity` est None — la sécurité est inactive sans capteur |
| `_apply_security_position` | Ne marque PAS `manual_control` — le retour automatique n'est pas bloqué |
| `is_presence_detected` | Fail-safe : retourne True si entité unavailable — évite de fermer les volets sur erreur capteur |
| `OptionsFlow.config_entry` | Read-only depuis HA 2025.12 — ne pas assigner |
| `state_attr` | Supprimé de HA core → utiliser `helpers.state_attr(hass, entity_id, attr)` |
| `_lux_toggle` / `_irradiance_toggle` | Initialisés à `True` quand l'entité est configurée |
| `_HUB_BOOTSTRAPPED` / `_V18_CLEANUP_DONE` | Flags one-shot dans `hass.data[DOMAIN]` — préfixés `_` pour être ignorés par `iter_regular_coordinators` |
| `check_position_delta` | Force `condition=True` pour sunset_pos, default_height, 0, 100 |
| `_iter_coordinators` dans `cover.py` | Copie locale de `iter_regular_coordinators` (helpers.py) — à unifier si refacto |

---

## 5. Structure des données en mémoire

```
hass.data["adaptive_cover"] = {
    "_hub_bootstrapped": True,
    "_v18_cleanup_done": True,
    "<entry_id_regular>": AdaptiveDataUpdateCoordinator {
        ._security_toggle: bool          # géré par AdaptiveCoverSwitch("Security Mode")
        ._control_toggle: bool
        ._manual_toggle: bool
        ._switch_mode: bool              # climate mode
        ._lux_toggle: bool | None
        ._irradiance_toggle: bool | None
        .manager: AdaptiveCoverManager
    },
    # hub entry → pas de coordinateur enregistré
}
```

`iter_regular_coordinators(hass)` itère ce dict en skippant les clés `_*` et les valeurs `None`.

---

## 6. Logique sécurité — diagramme de priorité

```
Coordinator._async_update_data()
    │
    └── async_handle_state_change() / async_handle_first_refresh() / async_handle_timed_refresh()
            │
            ├── control_toggle = OFF → rien (log debug)
            │
            └── control_toggle = ON
                    │
                    ├── security_active = True
                    │       │
                    │       └── pour chaque cover :
                    │               ├── is_cover_manual ? → skip
                    │               └── _apply_security_position()
                    │                       ├── climate + (winter|intermediate) → min_position
                    │                       └── sinon → 0 %
                    │
                    └── security_active = False
                            └── logique adaptative normale
                                (check_adaptive_time, check_position_delta, check_time_delta, ...)
```

---

## 7. Références

| Ressource | Lien |
|-----------|------|
| Dépôt | https://github.com/kamahat/adaptive-cover |
| Documentation FR | [README.fr.md](README.fr.md) |
| Documentation EN | [README.md](README.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |
| HA Custom Components | https://developers.home-assistant.io/docs/creating_integration_introduction |
