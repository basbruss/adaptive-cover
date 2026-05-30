# Adaptive Cover — Documentation française

🇬🇧 [English documentation](README.md)

[![Version](https://img.shields.io/badge/version-1.9.0-blue)](CHANGELOG.md)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.5+-green)](https://www.home-assistant.io)

Positionnez automatiquement vos volets (stores, banne, jalousie) en fonction de la position du soleil par rapport à chaque fenêtre. Un **mode climatique** adapte la position aux conditions de température, et un **mode sécurité** ferme les volets automatiquement en cas d'absence.

---

## Architecture

```mermaid
graph TB
    subgraph Inputs["Sources de données"]
        SUN["☀️ sun.sun\nazimut + élévation"]
        PRES["👤 Capteur de présence"]
        ENV["🌡️ Temp / Météo / Lux / Irradiance"]
    end

    subgraph HUB["🏠 Entrée Hub — All Blinds  (singleton)"]
        HC["cover.* Les volets\n↔ Alexa : ouvre / ferme les volets"]
        HS["switch.* Les volets\n↔ Alexa : active / désactive les volets"]
        HSEC["switch.* Sécurité volets\n↔ Alexa : active la sécurité des volets"]
        HSEL["select.* Mode de contrôle\nauto · off · all_open · all_closed"]
        HSCN["scene.* Volets ouverts\nscene.* Volets fermés"]
    end

    subgraph ENTRY["📦 Entrée régulière  (une par groupe de volets)"]
        COORD["Coordinateur\n_async_update_data()"]
        COVER["cover.*\nAdaptiveCoverEntry\nposition calculée"]
        SW["switch.*\nToggle Control · Manual Override\nSecurity Mode · Climate Mode\nLux · Irradiance"]
        SEN["sensor.*\nPosition · Start Sun · End Sun\nControl Method · Climate Debug"]
        BS["binary_sensor.* Manual Control"]
        BTN["button.* Reset Manual Control"]
    end

    SUN --> COORD
    PRES --> COORD
    ENV  --> COORD

    COORD -->|"position calculée"| COVER
    COORD --> SEN
    HUB   -.->|"itère tous les coordinateurs"| ENTRY
```

---

## Flux de décision par entrée

```mermaid
flowchart TD
    UPDATE(["🔄 _async_update_data()"])
    CTRL{control_toggle\nON ?}
    SEC{security_active ?}
    APPLY_SEC["_apply_security_position()"]
    ADAPT["Positionnement adaptatif\nNormalCoverState / ClimateCoverState"]
    MOVE(["📡 set_cover_position\ncover.*"])

    UPDATE --> CTRL
    CTRL -->|NON| SKIP(["⏸ Rien"])
    CTRL -->|OUI| SEC
    SEC -->|OUI| MANUAL{is_cover_manual ?}
    MANUAL -->|OUI| SKIP2(["⏸ Skip — override manuel résiste"])
    MANUAL -->|NON| APPLY_SEC --> MOVE
    SEC -->|NON| ADAPT --> MOVE
```

---

## Logique du mode sécurité

```mermaid
flowchart TD
    A(["🔒 security_toggle = ON ?"])
    B{"presence_entity\nconfiguré ?"}
    C{"Présence\ndétectée ?"}
    D(["✅ Adaptatif normal"])
    E(["🛡️ SÉCURITÉ ACTIVE"])
    F{"Mode climatique\n+ winter/intermediate ?"}
    G(["🔒 0% — fermeture totale"])
    H(["🔒 CONF_MIN_POSITION\n(ou 0%)"])

    A -->|NON| D
    A -->|OUI| B
    B -->|NON → pas de capteur| D
    B -->|OUI| C
    C -->|OUI → quelqu'un est là| D
    C -->|NON → absence| E
    E --> F
    F -->|NON| G
    F -->|OUI| H

    style E fill:#ff6b6b,color:#fff
    style G fill:#c0392b,color:#fff
    style H fill:#e67e22,color:#fff
    style D fill:#27ae60,color:#fff
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

1. Dans HACS → **Intégrations → Dépôts personnalisés**
2. Ajouter `https://github.com/kamahat/adaptive-cover` (catégorie : Intégration)
3. Rechercher *Adaptive Cover* et installer
4. Redémarrer Home Assistant

### Manuelle

1. Copier le dossier `adaptive_cover` dans `config/custom_components/`
2. Redémarrer Home Assistant

---

## Configuration

Ajouter via **Paramètres → Appareils & Services → Ajouter → Adaptive Cover**.

Au premier démarrage, le menu propose :
- **Créer une entrée volet** — configure un groupe (vertical / horizontal / tilt)
- **All Blinds** — crée l'entrée hub manuellement (normalement auto-créée)

### Base (obligatoire)

| Option | Description |
|--------|-------------|
| **Nom** | Libellé du groupe de volets |
| **Type de volet** | Vertical / Horizontal / Jalousie |
| **Azimut** | Direction de la fenêtre en degrés (0 = N, 90 = E, 180 = S, 270 = O) |
| **Champ de vision gauche / droite** | Plage angulaire (°) de part et d'autre de la normale |
| **Hauteur de la fenêtre** | Hauteur en mètres |
| **Profondeur de la zone ombragée** | Profondeur (m) à maintenir à l'ombre |
| **Position par défaut** | Position de repli (%) hors du champ de vision |

### Groupe de volets

| Option | Description |
|--------|-------------|
| **Volets** | Entités `cover.*` contrôlées par cette entrée |

### Fenêtre temporelle

| Option | Description |
|--------|-------------|
| **Heure de début / entité** | Début du contrôle adaptatif |
| **Heure de fin / entité** | Fin du contrôle adaptatif |
| **Décalage lever / coucher** | Décalage en minutes par rapport au soleil |
| **Position au coucher** | Position appliquée au coucher du soleil |
| **Retour au coucher** | Restaurer la position par défaut plutôt qu'appliquer la position coucher |

### Limites de position

| Option | Description |
|--------|-------------|
| **Position minimale** | Seuil bas (%) — utilisé aussi par le mode sécurité en hiver/intermédiaire |
| **Position maximale** | Seuil haut (%) |

### Mode climatique

À activer via **Paramètres → Intégrations → [entrée] → Configurer → Paramètres climatiques**.

```mermaid
flowchart TD
    SV{"Soleil dans\nle champ de vision ?"}
    DEF["Position par défaut"]
    WIN{"HIVER ?\ntemp_inside < temp_low"}
    SUM{"ÉTÉ ?\ntemp_ref > temp_high\nAND outside_high"}
    OPEN["100% ouvert\n(apports solaires)"]
    TRANS{"Store\ntransparent ?"}
    CLOSED["0% fermé\n(bloquer la chaleur)"]
    CALC_SUM["Position calculée\n(atténuation seulement)"]
    CLOUDS{"Nuageux / lux faible\nirradiance faible ?"}
    CALC_INT["Position calculée\n(suivi solaire)"]

    SV -->|NON| DEF
    SV -->|OUI| WIN
    WIN -->|OUI| OPEN
    WIN -->|NON| SUM
    SUM -->|OUI| TRANS
    TRANS -->|OUI| CALC_SUM
    TRANS -->|NON| CLOSED
    SUM -->|NON — intermédiaire| CLOUDS
    CLOUDS -->|OUI| DEF
    CLOUDS -->|NON| CALC_INT

    style OPEN fill:#27ae60,color:#fff
    style CLOSED fill:#c0392b,color:#fff
    style DEF fill:#7f8c8d,color:#fff
```

> **Sans présence** → position minimale configurée (ou 0 %).

| Option | Description |
|--------|-------------|
| **Entité de température** | Capteur intérieur |
| **Entité de température extérieure** | Capteur extérieur (optionnel) |
| **Entité météo** | Source de température si pas de capteur |
| **Temp basse / haute** | Seuils hiver (°C) / été (°C) |
| **Utiliser la température extérieure** | Comparer la temp. ext. à `temp_haute` |
| **Conditions météo** | États météo considérés comme « ensoleillé » |
| **Entité de présence** | Utilisée pour le mode climatique **et** le mode sécurité |

### Mode sécurité

> Nécessite un **capteur de présence** configuré dans l'entrée. Sans capteur, le switch est inactif même s'il est ON.

**Règles de position :**

| Situation | Position cible |
|---|---|
| Sans mode climatique | 0 % (fermeture totale) |
| Climatique + branche `summer` | 0 % (fermeture totale) |
| Climatique + branche `winter` ou `intermediate` | `CONF_MIN_POSITION` (ou 0 si non configuré) |

**Comportements clés :**
- Override manuel résiste (le volet en contrôle manuel n'est pas touché)
- Retour automatique à la présence sans intervention manuelle
- Fail-safe : capteur `unavailable` → sécurité inactive (pas de fermeture sur erreur)

### Seuil lumineux

| Option | Description |
|--------|-------------|
| **Lux / seuil** | En-dessous → considéré « non ensoleillé » en mode intermédiaire |
| **Irradiance / seuil** | Idem |

### Contrôle manuel

| Option | Description |
|--------|-------------|
| **Durée du contrôle manuel** | Minutes de pause après déplacement manuel |
| **Réinitialisation** | Heure de réinitialisation automatique |
| **Seuil de déplacement** | Delta (%) considéré comme un déplacement manuel |
| **Ignorer les positions intermédiaires** | Seuls les mouvements ouvert/fermé complets comptent |

---

## Entités créées

### Appareil « All Blinds » (hub)

| Entité | Nom | Alexa | Description |
|--------|-----|-------|-------------|
| `cover.*` | Les volets | "ouvre / ferme les volets" | Aggregate cover — toutes les entrées |
| `switch.*` | Les volets | "active / désactive les volets" | Contrôle adaptatif ON/OFF |
| `switch.*` | Sécurité volets | "active la sécurité des volets" | Mode sécurité — entrées avec capteur de présence |
| `select.*` | Mode de contrôle | — | `auto` · `off` · `all_open` · `all_closed` |
| `scene.*_all_open` | Volets ouverts | "allume Volets ouverts" | Tous à 100 % |
| `scene.*_all_closed` | Volets fermés | "allume Volets fermés" | Tous à 0 % |

### Appareils par entrée régulière

#### Interrupteurs

| Entité | Défaut | Description |
|--------|--------|-------------|
| `switch.toggle_control_<nom>` | ON | Activer / désactiver le positionnement adaptatif |
| `switch.manual_override_<nom>` | ON | Pause manuelle (auto-activé sur déplacement) |
| `switch.security_mode_<nom>` | **OFF** | **Mode sécurité** — ferme les volets en absence *(visible si capteur de présence configuré)* |
| `switch.climate_mode_<nom>` | ON | Mode climatique *(visible si configuré)* |
| `switch.outside_temperature_<nom>` | OFF | Temp. extérieure pour détection été |
| `switch.lux_<nom>` | ON | Seuil lux |
| `switch.irradiance_<nom>` | ON | Seuil irradiance |

#### Capteurs

| Entité | Description |
|--------|-------------|
| `cover.<nom>` | **Entité principale** — position adaptative ; open/close/set_position sur le groupe |
| `sensor.cover_position_<nom>` | Position cible calculée (%) |
| `sensor.start_sun_<nom>` / `sensor.end_sun_<nom>` | Timestamps entrée/sortie du soleil dans le champ de vision |
| `sensor.control_method_<nom>` | Branche active (`summer` / `winter` / `intermediate`) |
| `sensor.climate_debug_<nom>` *(diagnostic)* | Snapshot complet de la décision climatique |
| `binary_sensor.manual_control_<nom>` | ON si au moins un volet est en contrôle manuel |
| `button.reset_manual_control_<nom>` | Réinitialise le contrôle manuel immédiatement |

---

## Intégration Alexa

| Commande Alexa | Entité | Action |
|----------------|--------|--------|
| "ouvre les volets" | `cover.*` hub | → 100 % |
| "ferme les volets" | `cover.*` hub | → 0 % |
| "active les volets" | `switch.*` adaptatif hub | Adaptatif ON |
| "désactive les volets" | `switch.*` adaptatif hub | Adaptatif OFF |
| "active la sécurité des volets" | `switch.*` sécurité hub | Sécurité ON |
| "désactive la sécurité des volets" | `switch.*` sécurité hub | Sécurité OFF |
| "allume Volets ouverts" | `scene.*_all_open` | 100 % |
| "allume Volets fermés" | `scene.*_all_closed` | 0 % |

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
| Volet bloqué en mode manuel | Override manuel actif | Bouton de réinitialisation |
| Volet reste fermé malgré retour à la maison | Security switch ON + presence entity absent ou unavailable | Vérifier capteur de présence |
| Switch sécurité absent | Pas de capteur de présence configuré | Ajouter `presence_entity` dans les options |
| Branche climatique toujours « intermediate » | Pas d'entité de température | Ajouter un capteur |
| Entité cover dupliquée | Résidu v1.7.x | Auto-nettoyé au démarrage (v1.8.11+) |

---

## Liens

- [Journal des modifications](CHANGELOG.md)
- [Runbook opérationnel](RUNBOOK.fr.md)
- [Releases](https://github.com/kamahat/adaptive-cover/releases)
- [Signaler un bug](https://github.com/kamahat/adaptive-cover/issues)
