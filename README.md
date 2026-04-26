# Moli Add-ons

Repo d'add-ons Home Assistant pour la flotte Moli (`moli.energy`).

## Add-ons disponibles

- [`molini-agent`](./molini-agent/) — Agent Moli pour Home Assistant OS
  (heartbeat, backups age + MinIO, commandes admin centralisées).

## Installation dans Home Assistant OS

### Méthode 1 — Repository Git (recommandée pour la prod)

1. Settings → Add-ons → ⋮ (en haut à droite) → **Repositories**
2. Ajouter l'URL : `https://github.com/rudy-io/molini-addons`
3. Le repo apparaît dans le store, l'add-on **Moli Agent** est installable.

### Méthode 2 — Local (R&D / box pilote)

1. Sur la box (HAOS), accéder à `/addons/` via le **File Editor** ou SSH add-on.
2. Copier le contenu de `box/addons/molini-agent/` dans `/addons/molini-agent/`.
3. Settings → Add-ons → ⋮ → **Check for updates** (l'add-on local est détecté
   automatiquement, marqué « Local add-ons »).
4. Ouvrir l'add-on, configurer, démarrer.

## Configuration requise (chaque box client)

| Champ                        | Description                                                                    |
|------------------------------|--------------------------------------------------------------------------------|
| `central_url`                | `https://moli.energy` (par défaut)                                             |
| `client_token`               | Token agent généré côté admin lors de la création du client (préfixé `molini_`)|
| `backup_age_recipient`       | Clé publique `age` du super_admin (`age1...`) — sans elle, backups skippés     |
| `linky_*_entity`             | Entity IDs HA qui correspondent aux capteurs Linky du client                   |

Les autres champs ont des valeurs par défaut raisonnables. Voir
[`molini-agent/DOCS.md`](./molini-agent/DOCS.md) pour le détail.

## Différences avec l'agent Debian historique

L'agent dans le dossier `agent/` du repo principal Moli (privé) est conçu pour
les box Debian/Ubuntu avec Docker libre. Le présent add-on est sa
contrepartie pour les box **Home Assistant OS** (HA Green / Pi 5).

| Capacité                | Debian (`agent/`)             | HAOS (`box/addons/molini-agent`)       |
|-------------------------|-------------------------------|----------------------------------------|
| Heartbeat / metrics     | ✅                            | ✅                                     |
| Backup age + MinIO      | ✅ (chemins `/home/rudy/...`) | ✅ (chemins `/config`, `/share`)       |
| Commandes Linky / HA    | ✅ via API HA                 | ✅ via supervisor proxy                |
| `ha_restart`            | `docker restart homeassistant`| `POST /core/restart` supervisor        |
| `stack_update`          | `docker compose pull/up`      | `addon_update` pour chaque add-on      |
| `tunnel_install`        | écrit `cloudflared/compose.yml`| installe + start add-on cloudflared   |
| `agent_update` (OTA)    | self-update bundle.tar.gz     | délégué au store HA (désactivé)        |
| `ha_provision`          | écrit `packages/molini_*.yaml`| idem (`/config/packages/`)             |

Les deux variantes reportent au même central et utilisent le même schéma de
heartbeat. **Différenciation côté admin** : le champ `runtime: "haos" | "debian"`
envoyé dans le heartbeat fait remonter un badge dans la fiche client et adapte
les labels/tooltips des commandes. Le bouton "Mettre à jour l'agent" est
disabled pour les box HAOS (managed_by_supervisor).

## Source

Ce repo est miroir de `box/addons/` du repo Moli principal (privé). Les changements
font une PR sur le repo privé puis sont synchronisés ici. Les utilisateurs HA
n'ont besoin que de cette URL publique pour ajouter le repo dans leur store.

## Licence

Code propriétaire MARLOONA SASU (Moli). L'usage de l'add-on Moli Agent
nécessite un `client_token` valide délivré dans le cadre d'un contrat de
service Moli. Pas de redistribution sans accord écrit.
