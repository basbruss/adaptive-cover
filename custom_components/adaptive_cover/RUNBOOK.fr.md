# Adaptive Cover — Runbook opérationnel

Version cible : **1.8.11**  
Dépôt : `https://github.com/kamahat/adaptive-cover`

---

## 1. Procédure de release

### Prérequis

- Accès SSH à **claude-mgmt** (`192.168.20.150`)
- `GITHUB_TOKEN` exporté dans `~/.bashrc` sur claude-mgmt
- Clone local à jour sur claude-mgmt

### Étapes

```bash
# 1. Connexion à claude-mgmt
plink -batch -i "C:\Users\yoyo\Documents\_moa\ssh_key_home_ecdsa.ppk" root@192.168.20.150

# 2. Vérifier / modifier la version dans les deux fichiers
grep '"version"' /path/to/adaptive_cover/manifest.json
grep '^version' /path/to/pyproject.toml

# 3. Bumper la version (remplacer X.Y.Z)
NEW_VERSION="X.Y.Z"
sed -i "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/" manifest.json
sed -i "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml

# 4. Mettre à jour le badge dans README.fr.md et README.md
sed -i "s/version-[0-9.]*-blue/version-$NEW_VERSION-blue/" README.fr.md README.md

# 5. Mettre à jour CHANGELOG.md (ajouter section ## [X.Y.Z])

# 6. Commit et push
git add -A
git commit -m "release: v$NEW_VERSION"
git push origin main

# 7. Créer la release GitHub via l'API
python3 - <<'EOF'
import json, subprocess, urllib.request
token = subprocess.run(
    ["bash", "-i", "-c", "echo $GITHUB_TOKEN"],
    capture_output=True, text=True
).stdout.strip()
data = json.dumps({
    "tag_name": f"v{NEW_VERSION}",
    "name": f"v{NEW_VERSION}",
    "body": "Voir CHANGELOG.md",
    "draft": False,
    "prerelease": False,
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
- [ ] `pyproject.toml` version à jour
- [ ] `CHANGELOG.md` section ajoutée avec date et description
- [ ] `README.fr.md` badge version mis à jour
- [ ] Tests manuels : redémarrage HA, volet se positionne, Alexa répond

---

## 2. Diagnostic des problèmes courants

### 2.1 Volet ne bouge pas

1. Vérifier `switch.toggle_control_<nom>` → doit être ON
2. Vérifier `binary_sensor.manual_control_<nom>` → si ON, appuyer sur `button.reset_manual_control_<nom>`
3. Vérifier `sensor.control_method_<nom>` → doit afficher `sun`, `summer`, `winter` ou `intermediate`
4. Vérifier que l'heure courante est dans la fenêtre `start_time` / `end_time`
5. Vérifier que le soleil est dans le champ de vision : `sensor.start_sun` et `sensor.end_sun`

### 2.2 Branche climatique incorrecte

Lire le capteur `sensor.climate_debug_<nom>` :

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

**Arbre de décision :**
- `is_winter=True` + `sun_in_window=True` → devrait être à 100 %
- `is_summer=True` + store opaque → devrait être à 0 %
- `active_branch=intermediate` + `lux_below_threshold=True` → position par défaut attendue

### 2.3 Hub "All Blinds" absent après installation

L'entrée hub est créée automatiquement lors du premier démarrage d'une entrée régulière.
Si elle est absente :
1. Vérifier `hass.data["adaptive_cover"]["_hub_bootstrapped"]` (logs HA)
2. Créer manuellement via **Paramètres → Intégrations → Adaptive Cover → Configurer → All Blinds**
3. En dernier recours : redémarrer HA

### 2.4 Entités cover dupliquées sur un appareil

Symptôme : deux entités `cover.*` apparaissent sur le même appareil régulier.
Cause : résidu d'une version < 1.8.11.
Solution : `_cleanup_orphan_cover_entities()` s'exécute automatiquement au chargement de la plateforme `cover`. Redémarrer HA suffit.

### 2.5 Interrupteurs OFF après redémarrage

Résolu en v1.7.0. Si le problème persiste :
1. Vérifier la version dans **Paramètres → Intégrations → Adaptive Cover**
2. Mettre à jour via HACS

### 2.6 Alexa ne comprend pas "active les volets"

Vérifier que le switch hub a bien `_attr_has_entity_name=False` (résolu en v1.8.7).  
Dans le voix Alexa, le nom doit être exactement **"Les volets"** sans préfixe "All Blinds".  
Procédure de re-découverte Alexa : demander à Alexa "découvre mes appareils".

---

## 3. Migrations

### 3.1 Migration depuis < 1.8.0

L'entrée hub est créée automatiquement. L'ancien device `(DOMAIN, "all_covers")` est supprimé automatiquement par `_cleanup_v18_leftover_device()` au premier démarrage.  
Aucune action manuelle requise.

### 3.2 Migration depuis < 1.7.1 (state_attr supprimé de HA core)

Mettre à jour l'intégration. Le helper `state_attr()` local dans `helpers.py` remplace l'ancien import depuis `homeassistant.helpers.template`.

### 3.3 Migration depuis < 1.7.0 (switches OFF au démarrage)

Mettre à jour. `super().async_added_to_hass()` est maintenant appelé correctement.

---

## 4. Points d'attention au développement

| Point | Détail |
|-------|--------|
| `OptionsFlow.config_entry` | Read-only depuis HA 2025.12 — ne pas assigner |
| `state_attr` | Supprimé de HA core — utiliser `helpers.state_attr(hass, entity_id, attr)` |
| `_lux_toggle` / `_irradiance_toggle` | Initialisés à `True` (pas `None`) quand l'entité est configurée |
| `_HUB_BOOTSTRAPPED` / `_V18_CLEANUP_DONE` | Flags one-shot dans `hass.data[DOMAIN]` — préfixés `_` pour être ignorés par `iter_regular_coordinators` |
| `iter_regular_coordinators` | Dans `helpers.py` — skip les clés `_*` et les `None` ; copie locale `_iter_coordinators` dans `cover.py` (à unifier éventuellement) |
| `check_position_delta` | Force `condition=True` pour les positions `sunset_pos`, `default_height`, 0 et 100 — toujours appliquer ces positions de référence |
| Scene unique_id | Suffix `_v2` pour forcer une nouvelle entrée de registre entité |

---

## 5. Structure des données en mémoire

```
hass.data["adaptive_cover"] = {
    "_hub_bootstrapped": True,         # flag one-shot bootstrap
    "_v18_cleanup_done": True,         # flag one-shot migration v1.8.0
    "<entry_id_regular_1>": AdaptiveDataUpdateCoordinator,
    "<entry_id_regular_2>": AdaptiveDataUpdateCoordinator,
    # L'entrée hub n'enregistre PAS de coordinateur sous son entry_id
}
```

`iter_regular_coordinators(hass)` dans `helpers.py` itère ce dict en skippant les clés `_*` et les valeurs `None`.

---

## 6. Références

| Ressource | Lien |
|-----------|------|
| Dépôt | https://github.com/kamahat/adaptive-cover |
| Documentation FR | [README.fr.md](README.fr.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |
| HA Custom Components | https://developers.home-assistant.io/docs/creating_integration_introduction |
