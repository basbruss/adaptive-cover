# Adaptive Cover — Documentation française

🇬🇧 [English documentation](README.md)

[![Version](https://img.shields.io/badge/version-1.7.1-blue)](CHANGELOG.md)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1+-green)](https://www.home-assistant.io)

Positionnez automatiquement vos volets (stores, banne, jalousie) en fonction de la position du soleil par rapport à chaque fenêtre. L'intégration calcule la position optimale pour bloquer le rayonnement direct tout en conservant la luminosité ambiante, et propose un mode climatique pour réagir aux conditions de température.

---

## Types de volets

| Type | Description |
|------|-------------|
| **Store vertical** | Store enrouleur ou rideau — position en % (0 = ouvert, 100 = fermé) |
| **Banne horizontale** | Banne extérieure déployée horizontalement |
| **Jalousie (tilt)** | Store vénitien avec réglage de l'angle des lames |

---

## Installation

### HACS (recommandé)

1. Dans HACS, aller dans **Intégrations → Dépôts personnalisés**
2. Ajouter `https://github.com/basbruss/adaptive-cover` (catégorie : Intégration)
3. Rechercher *Adaptive Cover* et installer
4. Redémarrer Home Assistant

### Manuelle

1. Copier le dossier `adaptive_cover` dans `config/custom_components/`
2. Redémarrer Home Assistant

---

## Configuration

Ajouter l'intégration via **Paramètres → Appareils & Services → Ajouter une intégration → Adaptive Cover**.

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
| **Mode tilt** | `basic` — angle uniquement ; `enhanced` — ajuste aussi la position verticale |

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

| Branche | Condition | Comportement |
|---------|-----------|--------------|
| **Été** | Temp. extérieure (ou de référence) > `temp_haute` ET soleil dans le champ de vision | Fermeture pour bloquer la chaleur |
| **Hiver** | Temp. intérieure < `temp_basse` | Ouverture pour profiter des apports solaires passifs |
| **Intermédiaire** | Aucune des conditions ci-dessus | Suivi standard de la position solaire |

| Option | Description |
|--------|-------------|
| **Entité de température** | Capteur de température intérieure |
| **Entité de température extérieure** | Capteur de température extérieure (optionnel) |
| **Entité météo** | Entité météo HA utilisée comme source de température en l'absence de capteur |
| **Temp basse** | Seuil hiver (°C) — en dessous, ouverture pour gains solaires |
| **Temp haute** | Seuil été (°C) — au-dessus, fermeture pour bloquer la chaleur |
| **Utiliser la température extérieure** | Comparer la temp. extérieure à `temp_haute` |
| **Conditions météo** | États météo considérés comme « ensoleillé » |
| **Entité de présence** | Ignore le mode climatique si personne n'est à la maison |

### Seuil lumineux

| Option | Description |
|--------|-------------|
| **Entité lux** | Capteur d'éclairement (`sensor.*`) |
| **Seuil lux** | En dessous de cette valeur (lx), le volet s'ouvre quelles que soient les conditions |
| **Entité irradiance** | Capteur d'irradiance solaire (`sensor.*`) |
| **Seuil irradiance** | En dessous de cette valeur (W/m²), le volet s'ouvre |

### Contrôle manuel

| Option | Description |
|--------|-------------|
| **Durée du contrôle manuel** | Minutes de pause du contrôle adaptatif après un déplacement manuel |
| **Réinitialisation du contrôle manuel** | Heure à laquelle le mode manuel est automatiquement réinitialisé |
| **Seuil de déplacement manuel** | Delta de position (%) considéré comme un déplacement manuel |
| **Ignorer les positions intermédiaires** | Ne considère comme manuels que les déplacements totalement ouvert/fermé |

---

## Entités créées

Chaque entrée de configuration crée un appareil contenant les entités suivantes :

### Capteurs

| Entité | Description |
|--------|-------------|
| `sensor.cover_position_<nom>` | Position cible calculée (%) |
| `sensor.start_sun_<nom>` | Horodatage d'entrée du soleil dans le champ de vision |
| `sensor.end_sun_<nom>` | Horodatage de sortie du soleil du champ de vision |
| `sensor.control_method_<nom>` | Branche de contrôle active (`sun` / `climate` / `manual`) |
| `sensor.climate_debug_<nom>` *(diagnostic)* | Instantané complet de tous les paramètres de la décision climatique |

### Interrupteurs

| Entité | Défaut | Description |
|--------|--------|-------------|
| `switch.toggle_control_<nom>` | ON | Activer / désactiver le positionnement adaptatif |
| `switch.manual_override_<nom>` | ON | Mettre en pause le contrôle adaptatif (activé automatiquement lors d'un déplacement manuel) |
| `switch.climate_mode_<nom>` | ON | Basculer le mode climatique (visible uniquement si configuré) |
| `switch.outside_temperature_<nom>` | OFF | Utiliser la temp. extérieure pour la détection été |
| `switch.lux_<nom>` | ON | Activer le seuil lux |
| `switch.irradiance_<nom>` | ON | Activer le seuil d'irradiance |

### Capteur binaire

| Entité | Description |
|--------|-------------|
| `binary_sensor.manual_control_<nom>` | `ON` si au moins un volet du groupe est en contrôle manuel |

### Bouton

| Entité | Description |
|--------|-------------|
| `button.reset_manual_control_<nom>` | Réinitialise immédiatement le contrôle manuel pour tous les volets |

### Volet global

| Entité | Description |
|--------|-------------|
| `cover.<nom>` | Volet agrégé — open/close/set_position agit sur **tous** les volets du groupe ; `turn_on` / `turn_off` active ou désactive le contrôle adaptatif |

---

## Capteur de diagnostic climatique

Le capteur `sensor.climate_debug_<nom>` (visible dans la section *Diagnostic* de l'appareil) expose toutes les valeurs intermédiaires utilisées dans l'arbre de décision climatique.

| Attribut | Type | Description |
|----------|------|-------------|
| `is_winter` | bool | Temp. intérieure < `temp_basse` |
| `is_summer` | bool | Temp. de référence > `temp_haute` ET soleil dans le champ de vision |
| `is_presence` | bool | Capteur de présence actif |
| `sun_in_window` | bool | Azimut du soleil dans le champ de vision |
| `temp_inside` | float | Valeur brute du capteur intérieur |
| `temp_outside` | float | Valeur brute du capteur extérieur |
| `temp_used_winter` | float | Valeur comparée à `temp_basse` |
| `temp_used_summer` | float | Valeur comparée à `temp_haute` |
| `temp_low` | float | Seuil hiver configuré |
| `temp_high` | float | Seuil été configuré |
| `temp_switch` | bool | Temp. extérieure utilisée pour la détection été |
| `is_sunny` | bool | Météo correspond aux états « ensoleillé » configurés |
| `lux_below_threshold` | bool | Capteur lux sous le seuil |
| `irradiance_below_threshold` | bool | Capteur irradiance sous le seuil |
| `active_branch` | str | `summer` / `winter` / `intermediate` |

---

## Entité volet global

Le volet global agrège tous les volets physiques d'une entrée de configuration en une seule entité contrôlable :

- **Ouvrir / Fermer / Définir position** — déplace tous les volets et les marque comme *manuels* pour que le contrôle adaptatif ne les écrase pas immédiatement.
- **`cover.turn_on`** — réactive le contrôle adaptatif et efface tous les indicateurs manuels.
- **`cover.turn_off`** — désactive le contrôle adaptatif.
- **État** — rapporte la position moyenne ; `fermé` si tous les volets sont à 0 %.

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
          entity_id: cover.salon
```

### Bouton de tableau de bord

```yaml
type: button
name: Volets — mode adaptatif
tap_action:
  action: toggle
entity: switch.toggle_control_salon
```

---

## Dépannage

| Symptôme | Cause probable | Solution |
|----------|---------------|----------|
| Le volet ne bouge pas | `switch.toggle_control` est OFF | Activer l'interrupteur |
| Volet bloqué en mode manuel | Contrôle manuel actif | Appuyer sur le bouton de réinitialisation ou attendre la durée configurée |
| Les interrupteurs passent à OFF après redémarrage | Bug résolu en v1.7.1 | Mettre à jour vers la dernière version |
| Attributs de température indisponibles | Helper `state_attr` supprimé dans les versions récentes de HA | Résolu en v1.7.1 |
| Branche climatique toujours « intermediate » | Pas d'entité de température configurée | Ajouter un capteur de température dans les options |

---

## Liens

- [Journal des modifications](CHANGELOG.md)
- [Signaler un bug](https://github.com/basbruss/adaptive-cover/issues)
- [Communauté Home Assistant](https://community.home-assistant.io)
