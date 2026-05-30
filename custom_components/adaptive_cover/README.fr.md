# Adaptive Cover — Documentation française

🇬🇧 [English documentation](README.md)

[![Version](https://img.shields.io/badge/version-1.9.0-blue)](CHANGELOG.md)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.5+-green)](https://www.home-assistant.io)

Positionnez automatiquement vos volets (stores, banne, jalousie) en fonction de la position du soleil par rapport à chaque fenêtre. L'intégration calcule la position optimale pour bloquer le rayonnement direct tout en conservant la luminosité ambiante, et propose un mode climatique pour réagir aux conditions de température. Un **mode sécurité** ferme les volets automatiquement en cas d'absence.

---

## Architecture générale

```
Home Assistant
└── Adaptive Cover (DOMAIN: adaptive_cover)
    │
    ├── Entrée Hub « All Blinds » (is_hub=True) ← singleton, auto-créé
    │   ├── cover.*               — "Les volets"          → Alexa "ouvre / ferme les volets"
    │   ├── switch.* (adaptatif)  — "Les volets"          → Alexa "active / désactive les volets"
    │   ├── switch.* (sécurité)   — "Sécurité volets"     → Alexa "active la sécurité des volets"
    │   ├── select.*              — Mode de contrôle (auto / off / all_open / all_closed)
    │   └── scene.*               — "Volets ouverts" / "Volets fermés"
    │
    └── Entrées régulières (une par groupe de volets)
        ├── cover.*         — AdaptiveCoverEntry (position adaptative du groupe)
        ├── sensor.*        — Position / Start Sun / End Sun / Control Method / Climate Debug
        ├── switch.*        — Toggle Control / Manual Override / Security Mode /
        │                     Climate Mode / Lux / Irradiance
        ├── binary_sensor.* — Manual Control
        └── button.*        — Reset Manual Control
```

**Flux de données par entrée régulière :**

```
sun.sun ──► Coordinator ──► security_active ?
                │                  │ OUI → _apply_security_position()
   capteurs ───►│                  │ NON → NormalCoverState / ClimateCoverState
   présence     │                         │
   météo        │                         ▼ position calculée (0-100 %)
   lux/irr.     │               apply_max / apply_min / interpolation
                └──► AdaptiveCoverEntry.current_cover_position → cover.*
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
| **Champ de vision gauche / droite** | Plage angulaire (°) de part et d'autre de la normale de la fenêtre |
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
| **Heure de début / entité** | Heure la plus tôt pour le contrôle adaptatif |
| **Heure de fin / entité** | Heure la plus tardive |
| **Décalage lever du soleil** | Décalage en minutes par rapport au lever du soleil |
| **Position au coucher** | Position à appliquer au coucher du soleil |
| **Décalage coucher** | Minutes avant/après le coucher pour appliquer la position |
| **Retour au coucher** | Restaurer la position par défaut au lieu d'appliquer la position coucher |

### Limites de position

| Option | Description |
|--------|-------------|
| **Activer position min** | Empêche le volet de descendre sous un seuil |
| **Position minimale** | Seuil bas (%) — utilisé aussi par le mode sécurité hiver/intermédiaire |
| **Activer position max** | Empêche le volet de monter au-dessus d'un seuil |
| **Position maximale** | Seuil haut (%) |

### Zone aveugle (Blind Spot)

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

Quand activé, l'intégration tient compte de la lumière directe qui traverse un store semi-transparent.

### Interpolation

Mappe la position calculée sur une courbe personnalisée.

### Mode climatique

À activer via **Paramètres → Appareils & Services → Configurer** après la création de l'entrée.

#### Arbre de décision (présence = vraie)

```
Soleil dans le champ de vision ?
├─ NON → position par défaut
└─ OUI
    ├─ HIVER (temp_inside < temp_low) → 100 % ouvert (apports solaires)
    ├─ ÉTÉ (temp_ref > temp_high AND outside_high)
    │   ├─ store transparent → position calculée
    │   └─ store opaque      → 0 % fermé
    └─ INTERMÉDIAIRE
        ├─ nuageux / lux faible / irradiance faible → position par défaut
        └─ ensoleillé → position calculée
```

Quand **personne n'est présent** → position minimale configurée (ou 0 %).

| Option | Description |
|--------|-------------|
| **Entité de température** | Capteur de température intérieure |
| **Entité de température extérieure** | Capteur de température extérieure (optionnel) |
| **Entité météo** | Entité météo HA |
| **Temp basse** | Seuil hiver (°C) |
| **Temp haute** | Seuil été (°C) |
| **Utiliser la température extérieure** | Comparer la temp. extérieure à `temp_haute` |
| **Conditions météo** | États météo considérés comme « ensoleillé » |
| **Entité de présence** | Gère la présence pour le mode climatique **et** le mode sécurité |

### Mode sécurité

Le mode sécurité ferme les volets automatiquement en cas d'absence pour protéger la maison.

**Condition d'activation :** `switch.Security Mode` = ON **ET** capteur de présence = absent.

> Le mode sécurité nécessite qu'un **capteur de présence** soit configuré dans l'entrée.
> Sans capteur de présence, le switch est inactif même s'il est ON.

#### Arbre de décision sécurité

```
security_switch = ON ?
└─ OUI → presence_entity configuré ?
    ├─ NON → inactif (pas de capteur = pas de sécurité)
    └─ OUI → présence détectée ?
        ├─ OUI → mode adaptatif normal (sécurité inactive)
        └─ NON → sécurité ACTIVE
            ├─ Mode climatique ON + branche winter ou intermediate
            │   → fermeture à CONF_MIN_POSITION (ou 0 si non configuré)
            └─ Tous les autres cas (pas de climatique, ou branche summer)
                → fermeture à 0 % (fermeture totale)
```

**Priorités :**
- Sécurité > adaptatif normal
- Override manuel résiste : un volet déjà en contrôle manuel n'est **pas** déplacé par la sécurité
- Retour automatique : quand la présence est restaurée, les volets reprennent le positionnement adaptatif sans intervention manuelle

**Note :** La position sécurité n'est **pas** marquée comme override manuel — le retour automatique à la présence n'est pas bloqué.

### Seuil lumineux

| Option | Description |
|--------|-------------|
| **Entité lux / seuil** | En-dessous du seuil → considéré « non ensoleillé » |
| **Entité irradiance / seuil** | Idem pour l'irradiance |

### Contrôle manuel

| Option | Description |
|--------|-------------|
| **Durée du contrôle manuel** | Minutes de pause après un déplacement manuel |
| **Réinitialisation** | Heure de réinitialisation automatique |
| **Seuil de déplacement** | Delta (%) considéré comme un déplacement manuel |
| **Ignorer les positions intermédiaires** | Seuls les mouvements totalement ouvert/fermé comptent comme manuels |

---

## Entités créées

### Appareil « All Blinds » (hub)

| Entité | Nom | Alexa | Description |
|--------|-----|-------|-------------|
| `cover.*` | Les volets | "ouvre / ferme les volets" | Aggregate cover |
| `switch.*` (adaptatif) | Les volets | "active / désactive les volets" | ON/OFF contrôle adaptatif |
| `switch.*` (sécurité) | Sécurité volets | "active la sécurité des volets" | ON/OFF mode sécurité sur toutes les entrées avec capteur de présence |
| `select.*` | Mode de contrôle | — | Dropdown 4 états |
| `scene.*_all_open` | Volets ouverts | "allume Volets ouverts" | 100 % |
| `scene.*_all_closed` | Volets fermés | "allume Volets fermés" | 0 % |

#### États du select « Mode de contrôle »

| État | Comportement |
|------|-------------|
| `auto` | Adaptatif ON, overrides manuels effacés |
| `off` | Adaptatif OFF |
| `all_open` | Tous à 100 % |
| `all_closed` | Tous à 0 % |

### Appareils par entrée régulière

#### Volet de groupe

| Entité | Description |
|--------|-------------|
| `cover.<nom>` | Entité principale — position adaptative calculée ; open/close/set_position sur le groupe |

#### Capteurs

| Entité | Description |
|--------|-------------|
| `sensor.cover_position_<nom>` | Position cible calculée (%) |
| `sensor.start_sun_<nom>` | Entrée du soleil dans le champ de vision |
| `sensor.end_sun_<nom>` | Sortie du soleil du champ de vision |
| `sensor.control_method_<nom>` | Branche active (`summer` / `winter` / `intermediate`) |
| `sensor.climate_debug_<nom>` *(diagnostic)* | Snapshot complet de la décision climatique |

#### Interrupteurs

| Entité | Défaut | Description |
|--------|--------|-------------|
| `switch.toggle_control_<nom>` | ON | Activer / désactiver le positionnement adaptatif |
| `switch.manual_override_<nom>` | ON | Pause manuelle (auto-activé sur déplacement manuel) |
| `switch.security_mode_<nom>` | **OFF** | **Mode sécurité** — ferme les volets en cas d'absence (visible si capteur de présence configuré) |
| `switch.climate_mode_<nom>` | ON | Mode climatique (visible si configuré) |
| `switch.outside_temperature_<nom>` | OFF | Temp. extérieure pour détection été |
| `switch.lux_<nom>` | ON | Seuil lux |
| `switch.irradiance_<nom>` | ON | Seuil irradiance |

#### Capteur binaire

| Entité | Description |
|--------|-------------|
| `binary_sensor.manual_control_<nom>` | ON si au moins un volet est en contrôle manuel |

#### Bouton

| Entité | Description |
|--------|-------------|
| `button.reset_manual_control_<nom>` | Réinitialise le contrôle manuel immédiatement |

---

## Capteur de diagnostic climatique

`sensor.climate_debug_<nom>` — section *Diagnostic* du device.

| Attribut | Type | Description |
|----------|------|-------------|
| `is_winter` | bool | Temp. intérieure < `temp_basse` |
| `is_summer` | bool | Temp. de référence > `temp_haute` ET `outside_high` |
| `is_presence` | bool | Présence détectée |
| `sun_in_window` | bool | Soleil dans le champ de vision |
| `temp_inside` | float | Valeur brute capteur intérieur |
| `temp_outside` | float | Valeur brute capteur extérieur |
| `temp_used_winter` | float | Valeur comparée à `temp_basse` |
| `temp_used_summer` | float | Valeur comparée à `temp_haute` |
| `temp_low` | float | Seuil hiver configuré |
| `temp_high` | float | Seuil été configuré |
| `temp_switch` | bool | Temp. extérieure pour détection été |
| `is_sunny` | bool | Météo ensoleillée |
| `lux_below_threshold` | bool | Lux sous le seuil |
| `irradiance_below_threshold` | bool | Irradiance sous le seuil |
| `active_branch` | str | `summer` / `winter` / `intermediate` |

---

## Intégration Alexa

| Commande Alexa | Entité cible | Action |
|----------------|-------------|--------|
| "Alexa, ouvre les volets" | `cover.*` (hub) | `open_cover` → 100 % |
| "Alexa, ferme les volets" | `cover.*` (hub) | `close_cover` → 0 % |
| "Alexa, active les volets" | `switch.*` adaptatif (hub) | Contrôle adaptatif ON |
| "Alexa, désactive les volets" | `switch.*` adaptatif (hub) | Contrôle adaptatif OFF |
| "Alexa, active la sécurité des volets" | `switch.*` sécurité (hub) | Sécurité ON |
| "Alexa, désactive la sécurité des volets" | `switch.*` sécurité (hub) | Sécurité OFF |
| "Alexa, allume Volets ouverts" | `scene.*_all_open` | 100 % |
| "Alexa, allume Volets fermés" | `scene.*_all_closed` | 0 % |

> Cover ET switch adaptatif ont le même nom « Les volets ». Alexa route par verbe.

---

## Exemples d'automatisation

### Activer la sécurité au départ

```yaml
automation:
  - alias: "Sécurité volets au départ"
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

### Réactiver le contrôle adaptatif au retour

```yaml
automation:
  - alias: "Retour adaptatif à l'arrivée"
    trigger:
      - platform: state
        entity_id: binary_sensor.presence_home
        to: "on"
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.security_mode_salon
```

> **Note :** le mode sécurité gère lui-même le retour automatique à la présence si le switch reste ON — ces automatisations sont optionnelles (utiles pour désactiver le switch visuellement).

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
| Volet bloqué en mode manuel | Contrôle manuel actif | Bouton de réinitialisation |
| Les interrupteurs passent à OFF après redémarrage | Bug résolu en v1.7.0 | Mettre à jour |
| Attributs de température indisponibles | `state_attr` supprimé de HA core | Résolu en v1.7.1 |
| Branche climatique toujours « intermediate » | Pas d'entité de température | Ajouter un capteur |
| Volet reste fermé malgré retour à la maison | Security switch toujours ON ET presence entity absente | Vérifier `switch.security_mode` ou ajouter un `CONF_PRESENCE_ENTITY` |
| Switch sécurité absent | Pas de capteur de présence configuré | Ajouter `presence_entity` dans les options de l'entrée |
| Entité cover dupliquée | Résidu v1.7.x | Résolu automatiquement en v1.8.11 |

---

## Liens

- [Journal des modifications](CHANGELOG.md)
- [Runbook opérationnel](RUNBOOK.fr.md)
- [Signaler un bug](https://github.com/kamahat/adaptive-cover/issues)
- [Communauté Home Assistant](https://community.home-assistant.io)
