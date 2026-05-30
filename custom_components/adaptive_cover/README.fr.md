# Adaptive Cover — Documentation française

🇬🇧 [English documentation](README.md)

[![Version](https://img.shields.io/badge/version-1.8.11-blue)](CHANGELOG.md)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.5+-green)](https://www.home-assistant.io)

Positionnez automatiquement vos volets (stores, banne, jalousie) en fonction de la position du soleil par rapport à chaque fenêtre. L'intégration calcule la position optimale pour bloquer le rayonnement direct tout en conservant la luminosité ambiante, et propose un mode climatique pour réagir aux conditions de température.

---

## Architecture générale

```
Home Assistant
└── Adaptive Cover (DOMAIN: adaptive_cover)
    │
    ├── Entrée Hub « All Blinds » (is_hub=True) ← singleton, auto-créé
    │   ├── cover.*         — "Les volets"    → Alexa "ouvre / ferme les volets"
    │   ├── switch.*        — "Les volets"    → Alexa "active / désactive les volets"
    │   ├── select.*        — Mode de contrôle (auto / off / all_open / all_closed)
    │   └── scene.*         — "Volets ouverts" / "Volets fermés"
    │
    └── Entrées régulières (une par groupe de volets)
        ├── cover.*         — AdaptiveCoverEntry (position adaptative du groupe)
        ├── sensor.*        — Position / Start Sun / End Sun / Control Method / Climate Debug
        ├── switch.*        — Toggle Control / Manual Override / Climate Mode / Lux / Irradiance
        ├── binary_sensor.* — Manual Control
        └── button.*        — Reset Manual Control
```

**Flux de données par entrée régulière :**

```
sun.sun ──► Coordinator ──► NormalCoverState / ClimateCoverState
                │                      │
   capteurs ───►│                      ▼ position calculée (0-100 %)
   présence     │           ┌─── apply_max / apply_min ────────────►  cover.*
   météo        │           └─── interpolation / inverse
   lux/irr.     │
                └──► AdaptiveCoverEntry.current_cover_position
```

---

## Types de volets

| Type | Description |
|------|-------------|
| **Store vertical** (`cover_blind`) | Store enrouleur ou rideau — position en % (0 = ouvert, 100 = fermé) |
| **Banne horizontale** (`cover_awning`) | Banne extérieure déployée horizontalement |
| **Jalousie / tilt** (`cover_tilt`) | Store vénitien avec réglage de l'angle des lames |

---

## Installation

### HACS (recommandé)

1. Dans HACS, aller dans **Intégrations → Dépôts personnalisés**
2. Ajouter `https://github.com/kamahat/adaptive-cover` (catégorie : Intégration)
3. Rechercher *Adaptive Cover* et installer
4. Redémarrer Home Assistant

### Manuelle

1. Copier le dossier `adaptive_cover` dans `config/custom_components/`
2. Redémarrer Home Assistant

---

## Configuration

Ajouter l'intégration via **Paramètres → Appareils & Services → Ajouter une intégration → Adaptive Cover**.

Au premier démarrage, le menu propose trois choix :
- **Créer une entrée volet** — configure un groupe de volets (vertical / horizontal / tilt)
- **All Blinds** — crée l'entrée hub manuellement (normalement auto-créée)
- **Importer** — usage interne (bootstrap automatique)

### Base (obligatoire)

| Option | Description |
|--------|-------------|
| **Nom** | Libellé du groupe de volets |
| **Type de volet** | Vertical / Horizontal / Jalousie |
| **Azimut** | Direction de la fenêtre en degrés (0 = N, 90 = E, 180 = S, 270 = O) |
| **Champ de vision gauche / droite** | Plage angulaire (°) de part et d'autre de la normale de la fenêtre où le soleil tape |
| **Hauteur de la fenêtre** | Hauteur en mètres |
| **Profondeur de la zone ombragée** | Profondeur (m) à maintenir à l'ombre |
| **Position par défaut** | Position de repli (%) quand le soleil est hors du champ de vision |

### Groupe de volets

| Option | Description |
|--------|-------------|
| **Volets** | Une ou plusieurs entités `cover.*` contrôlées par cette entrée |

### Fenêtre temporelle

| Option | Description |
|--------|-------------|
| **Heure de début / entité** | Heure la plus tôt pour le contrôle adaptatif (statique ou `input_datetime`) |
| **Heure de fin / entité** | Heure la plus tardive |
| **Décalage lever du soleil** | Décalage en minutes par rapport au lever du soleil (positif = plus tard) |
| **Position au coucher** | Position à appliquer au coucher du soleil |
| **Décalage coucher** | Minutes avant/après le coucher pour appliquer la position |
| **Retour au coucher** | Restaurer la position par défaut au lieu d'appliquer la position coucher |

### Limites de position

| Option | Description |
|--------|-------------|
| **Activer position min** | Empêche le volet de descendre sous un seuil |
| **Position minimale** | Seuil bas (%) |
| **Activer position max** | Empêche le volet de monter au-dessus d'un seuil |
| **Position maximale** | Seuil haut (%) |

### Zone aveugle (Blind Spot)

Évite que le volet ne s'arrête dans une plage d'azimut où le soleil passe directement à travers l'espace entre les lames ou arrive à un angle extrême.

| Option | Description |
|--------|-------------|
| **Activer la zone aveugle** | Active la fonctionnalité |
| **Zone aveugle gauche / droite** | Plage d'azimut (°) définissant la zone aveugle |
| **Élévation de la zone aveugle** | Élévation solaire minimale (°) pour que la zone aveugle s'applique |

### Options spécifiques à la jalousie (tilt)

| Option | Description |
|--------|-------------|
| **Profondeur de lame** | Profondeur physique d'une lame (mm) |
| **Espacement des lames** | Espace entre les lames (mm) |
| **Mode tilt** | `mode1` — monodirectionnel (0°–90°) ; `mode2` — bidirectionnel (0°–180°) |

### Store transparent

Quand cette option est activée, l'intégration tient compte de la lumière directe qui traverse un store semi-transparent et ajuste la position en conséquence.

### Interpolation

Permet de mapper la position calculée (basée sur le soleil) sur une courbe personnalisée plutôt que sur une échelle linéaire 0–100.

| Option | Description |
|--------|-------------|
| **Activer l'interpolation** | Active la fonctionnalité |
| **Début / fin de l'interpolation** | Plage d'angle solaire sur laquelle l'interpolation s'applique |
| **Liste d'interpolation** | Valeurs de position séparées par des virgules pour la courbe personnalisée |

### Mode climatique

À activer via **Paramètres → Appareils & Services → Configurer** après la création de l'entrée.

Quand le mode climatique est actif, l'intégration choisit l'une des trois stratégies suivantes :

#### Arbre de décision (présence = vraie)

```
Soleil dans le champ de vision ?
├─ NON → position par défaut
└─ OUI
    ├─ HIVER (temp_inside < temp_low) → 100 % ouvert (apports solaires)
    ├─ ÉTÉ (temp_ref > temp_high AND outside_high)
    │   ├─ store transparent → position calculée (atténuation seulement)
    │   └─ store opaque      → 0 % fermé (bloquer la chaleur)
    └─ INTERMÉDIAIRE
        ├─ nuageux / lux faible / irradiance faible → position par défaut
        └─ ensoleillé → position calculée (suivi solaire)
```

Quand **personne n'est présent** → position minimale configurée (ou 0 %).

| Option | Description |
|--------|-------------|
| **Entité de température** | Capteur de température intérieure |
| **Entité de température extérieure** | Capteur de température extérieure (optionnel) |
| **Entité météo** | Entité météo HA utilisée comme source de température en l'absence de capteur |
| **Temp basse** | Seuil hiver (°C) — en dessous, ouverture pour gains solaires |
| **Temp haute** | Seuil été (°C) — au-dessus, fermeture pour bloquer la chaleur |
| **Utiliser la température extérieure** | Comparer la temp. extérieure à `temp_haute` (détection chaleur entrante) |
| **Conditions météo** | États météo considérés comme « ensoleillé » |
| **Entité de présence** | Ignore le mode climatique si personne n'est à la maison |

### Seuil lumineux

| Option | Description |
|--------|-------------|
| **Entité lux** | Capteur d'éclairement (`sensor.*`) |
| **Seuil lux** | En dessous de cette valeur (lx), considéré comme « non ensoleillé » en mode intermédiaire |
| **Entité irradiance** | Capteur d'irradiance solaire (`sensor.*`) |
| **Seuil irradiance** | En dessous de cette valeur (W/m²), considéré comme « non ensoleillé » |

### Contrôle manuel

| Option | Description |
|--------|-------------|
| **Durée du contrôle manuel** | Minutes de pause du contrôle adaptatif après un déplacement manuel |
| **Réinitialisation du contrôle manuel** | Heure à laquelle le mode manuel est automatiquement réinitialisé |
| **Seuil de déplacement manuel** | Delta de position (%) considéré comme un déplacement manuel |
| **Ignorer les positions intermédiaires** | Ne considère comme manuels que les déplacements totalement ouvert/fermé |

---

## Entités créées

### Appareil « All Blinds » (hub)

Créé automatiquement au premier démarrage. Il agrège **toutes** les entrées régulières.

| Entité | Nom | Alexa | Description |
|--------|-----|-------|-------------|
| `cover.*` | Les volets | "ouvre / ferme les volets" | Aggregate cover : open/close/set_position sur tous les volets |
| `switch.*` | Les volets | "active / désactive les volets" | Active/désactive le contrôle adaptatif sur toutes les entrées |
| `select.*` | Mode de contrôle | — | Dropdown 4 états (voir ci-dessous) |
| `scene.*_all_open` | Volets ouverts | "allume Volets ouverts" | Met tous les volets à 100 % |
| `scene.*_all_closed` | Volets fermés | "allume Volets fermés" | Met tous les volets à 0 % |

#### États du select « Mode de contrôle »

| État | Comportement |
|------|-------------|
| `auto` | Contrôle adaptatif activé, overrides manuels effacés |
| `off` | Contrôle adaptatif désactivé, volets immobiles |
| `all_open` | Tous les volets à 100 %, override manuel activé |
| `all_closed` | Tous les volets à 0 %, override manuel activé |

#### Attributs du cover hub

| Attribut | Description |
|----------|-------------|
| `adaptive_control` | `true` si le contrôle adaptatif est actif sur toutes les entrées |
| `manual_override` | `true` si au moins un volet est en contrôle manuel |
| `covers` | Liste de tous les `entity_id` de volets physiques |
| `config_entries` | Nombre d'entrées régulières actives |

### Appareils par entrée régulière

#### Volet de groupe

| Entité | Description |
|--------|-------------|
| `cover.<nom>` | **Entité principale** — affiche la position adaptative calculée ; open/close/set_position agit sur tous les volets du groupe |

#### Capteurs

| Entité | Description |
|--------|-------------|
| `sensor.cover_position_<nom>` | Position cible calculée (%) |
| `sensor.start_sun_<nom>` | Horodatage d'entrée du soleil dans le champ de vision |
| `sensor.end_sun_<nom>` | Horodatage de sortie du soleil du champ de vision |
| `sensor.control_method_<nom>` | Branche de contrôle active (`summer` / `winter` / `intermediate`) |
| `sensor.climate_debug_<nom>` *(diagnostic)* | Instantané complet de tous les paramètres de la décision climatique |

#### Interrupteurs

| Entité | Défaut | Description |
|--------|--------|-------------|
| `switch.toggle_control_<nom>` | ON | Activer / désactiver le positionnement adaptatif |
| `switch.manual_override_<nom>` | ON | Mettre en pause le contrôle adaptatif (activé automatiquement lors d'un déplacement manuel) |
| `switch.climate_mode_<nom>` | ON | Basculer le mode climatique (visible uniquement si configuré) |
| `switch.outside_temperature_<nom>` | OFF | Utiliser la temp. extérieure pour la détection été |
| `switch.lux_<nom>` | ON | Activer le seuil lux |
| `switch.irradiance_<nom>` | ON | Activer le seuil d'irradiance |

#### Capteur binaire

| Entité | Description |
|--------|-------------|
| `binary_sensor.manual_control_<nom>` | `ON` si au moins un volet du groupe est en contrôle manuel |

#### Bouton

| Entité | Description |
|--------|-------------|
| `button.reset_manual_control_<nom>` | Réinitialise immédiatement le contrôle manuel pour tous les volets |

---

## Capteur de diagnostic climatique

Le capteur `sensor.climate_debug_<nom>` (visible dans la section *Diagnostic* de l'appareil) expose toutes les valeurs intermédiaires utilisées dans l'arbre de décision climatique.

| Attribut | Type | Description |
|----------|------|-------------|
| `is_winter` | bool | Temp. intérieure < `temp_basse` |
| `is_summer` | bool | Temp. de référence > `temp_haute` ET `outside_high` |
| `is_presence` | bool | Capteur de présence actif |
| `sun_in_window` | bool | Azimut du soleil dans le champ de vision |
| `temp_inside` | float | Valeur brute du capteur intérieur |
| `temp_outside` | float | Valeur brute du capteur extérieur |
| `temp_used_winter` | float | Valeur comparée à `temp_basse` (intérieure en priorité) |
| `temp_used_summer` | float | Valeur comparée à `temp_haute` (extérieure si `temp_switch=True`) |
| `temp_low` | float | Seuil hiver configuré |
| `temp_high` | float | Seuil été configuré |
| `temp_switch` | bool | Temp. extérieure utilisée pour la détection été |
| `is_sunny` | bool | Météo correspond aux états « ensoleillé » configurés |
| `lux_below_threshold` | bool | Capteur lux sous le seuil (→ non ensoleillé) |
| `irradiance_below_threshold` | bool | Capteur irradiance sous le seuil (→ non ensoleillé) |
| `active_branch` | str | `summer` / `winter` / `intermediate` |

---

## Intégration Alexa

Le hub "All Blinds" expose des entités nommées sans préfixe d'appareil (`_attr_has_entity_name=False`) pour une reconnaissance vocale optimale :

| Commande Alexa | Entité cible | Action |
|----------------|-------------|--------|
| "Alexa, ouvre les volets" | `cover.*` (hub) | `open_cover` → 100 % sur tous |
| "Alexa, ferme les volets" | `cover.*` (hub) | `close_cover` → 0 % sur tous |
| "Alexa, active les volets" | `switch.*` (hub) | `turn_on` → contrôle adaptatif ON |
| "Alexa, désactive les volets" | `switch.*` (hub) | `turn_off` → contrôle adaptatif OFF |
| "Alexa, allume Volets ouverts" | `scene.*_all_open` | Tous à 100 % |
| "Alexa, allume Volets fermés" | `scene.*_all_closed` | Tous à 0 % |

> **Note** : Cover ET switch ont le même nom « Les volets ». Alexa route par verbe : ouvre/ferme → cover ; active/désactive → switch.

---

## Exemples d'automatisation

### Réactiver le contrôle adaptatif chaque matin

```yaml
automation:
  - alias: "Réinitialiser les volets au lever du soleil"
    trigger:
      - platform: sun
        event: sunrise
    action:
      - service: cover.turn_on
        target:
          entity_id: cover.les_volets  # entité hub
```

### Bouton de tableau de bord

```yaml
type: button
name: Volets — mode adaptatif
tap_action:
  action: toggle
entity: switch.toggle_control_salon
```

### Mode soirée via select

```yaml
automation:
  - alias: "Fermer tous les volets le soir"
    trigger:
      - platform: time
        at: "21:00:00"
    action:
      - service: select.select_option
        target:
          entity_id: select.mode_de_controle
        data:
          option: all_closed
```

---

## Dépannage

| Symptôme | Cause probable | Solution |
|----------|---------------|----------|
| Le volet ne bouge pas | `switch.toggle_control` est OFF | Activer l'interrupteur |
| Volet bloqué en mode manuel | Contrôle manuel actif | Appuyer sur le bouton de réinitialisation ou attendre la durée configurée |
| Les interrupteurs passent à OFF après redémarrage | Bug résolu en v1.7.0 | Mettre à jour vers la dernière version |
| Attributs de température indisponibles | Helper `state_attr` supprimé dans les versions récentes de HA | Résolu en v1.7.1 |
| Branche climatique toujours « intermediate » | Pas d'entité de température configurée | Ajouter un capteur de température dans les options |
| Entité cover dupliquée sur l'appareil | Résidu d'une ancienne version (v1.7.x) | Résolu automatiquement au démarrage en v1.8.11 |
| L'entité hub "All Blinds" n'apparaît pas | Hub non encore bootstrappé | Redémarrer HA ou créer l'entrée manuellement via la config flow |
| Branche climatique bloquée en « summer » | Bug if/if corrigé | Résolu en v1.8.x — mettre à jour |

---

## Liens

- [Journal des modifications](CHANGELOG.md)
- [Runbook opérationnel](RUNBOOK.fr.md)
- [Signaler un bug](https://github.com/kamahat/adaptive-cover/issues)
- [Communauté Home Assistant](https://community.home-assistant.io)
