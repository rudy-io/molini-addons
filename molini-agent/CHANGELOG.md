# Changelog

## 0.5.0 — 2026-05-25 (chantier A — agent-first onboarding)

Première itération post-pilote Carole (25/05/2026). L'installateur ne fait
plus que (1) brancher la box et (2) installer l'add-on Moli Agent avec son
client token. **Tout le reste** (broker Mosquitto, Z2M, cloudflared, patch HA
`trusted_proxies` + `recorder.purge_keep_days`) est provisionné automatiquement
par l'agent dès que le central enqueue `bootstrap_stack`.

### Ajouts

- **Module `bootstrap.py`** : orchestre l'installation idempotente de la stack
  Moli via l'API supervisor. Retourne un rapport structuré (`actions[]`,
  `ha_config_patch`, `ha_restart_pending`, `errors[]`, `summary`).
- **Module `yaml_patch.py`** : patch idempotent deep-merge de
  `/config/configuration.yaml` via ruamel.yaml (round-trip, commentaires
  préservés). Inclut une **white-list stricte** des clés top-level patchables
  (`http`, `recorder`, `frontend`, `logger`, ...) — `python_script`, `shell_command`,
  `automation`, etc. sont volontairement **non patchables** (surface RCE).
- **Nouvelles commandes admin** (côté agent + enum central) :
  - `bootstrap_stack` — provisionne broker + z2m + cloudflared (sans démarrage,
    en attente du token) + patch `trusted_proxies` + `purge_keep_days`. Idempotent.
  - `install_addon` — installe un add-on précis depuis la white-list
    `{mosquitto, zigbee2mqtt, cloudflared}` avec options optionnelles.
  - `patch_ha_config` — patch deep-merge `configuration.yaml` avec validation
    white-list. Lève sur clé interdite.
- **Heartbeat enrichi** : nouveau champ `bootstrap_state` (sous HAOS uniquement)
  exposant `mosquitto/zigbee2mqtt/cloudflared` (state ou `not_installed`),
  `trusted_proxies_ok` (bool), `purge_keep_days_ok` (bool), `ha_restart_pending`
  (bool). Le central l'utilise pour le wizard d'install (chantier B).
- **Côté central `site/`** :
  - Enum `commandTypeEnum` (Drizzle) étendu avec les 3 nouveaux types.
  - `CommandsPanel` UI : nouveaux boutons "Bootstrap auto", "Install add-on",
    "Patch config HA" (super_admin only pour les 2 derniers).
  - Endpoint `/api/admin/clients/[id]/commands` valide le payload via Zod
    avec schémas dédiés (slug white-list, config white-list).
- **Slug add-ons figés** :
  - Mosquitto → `core_mosquitto` (slug exact officiel HA)
  - Z2M → `45df7312_zigbee2mqtt` (slug officiel community repo hash)
    avec fallback pattern `*_zigbee2mqtt`
  - Cloudflared → résolu dynamiquement (pattern `*_cloudflared`), repo
    `https://github.com/brenner-tobias/ha-addons` ajouté à la volée si
    nécessaire, polling `/store/addons` toutes les 2 s pendant 60 s max.
- **Helpers supervisor** : ajout de `store_addons_list()` et `store_info()`
  pour le polling du catalogue store post ajout repo.

### Modifications

- `requirements.txt` : ajout `ruamel.yaml>=0.18,<1` (parseur YAML round-trip).
- `config.yaml`, `Dockerfile`, `config.py` : version bumpée à `0.5.0`.

### Sécurité

- **White-list slugs** : `install_addon` rejette tout slug hors
  `{mosquitto, zigbee2mqtt, cloudflared}` côté agent **et** côté API admin
  (deux barrières).
- **White-list clés YAML** : `patch_ha_config` rejette toute clé top-level hors
  `PATCHABLE_TOP_KEYS` (=`{http, recorder, frontend, logger, ...}`). Les clés
  qui peuvent exécuter du code (`python_script`, `shell_command`, `automation`,
  `homeassistant.allow_*`, `command_line`, etc.) sont volontairement absentes.
- **Idempotence** : un même `bootstrap_stack` joué 2x = 0 modification au 2e
  passage (les pruning de patch retournent `changed: False`).
- **Pas de logs de secrets** : les tokens (client_token, tunnel_token, age
  recipient) ne sont jamais loggés en clair — tronqués à 14 chars max.

### Limitations connues

- Pas encore d'icône `icon.png` / `logo.png` (l'add-on s'affiche avec
  l'icône par défaut HA).
- Le slug Z2M `45df7312_zigbee2mqtt` dépend du hash du repo officiel — si HA
  change ce hash, le fallback pattern reste valide.
- Le HA restart (nécessaire après patch `http`/`recorder`) **n'est pas** déclenché
  automatiquement par `bootstrap_stack` — le rapport flag `ha_restart_pending`
  et c'est au central de déclencher `ha_restart` ensuite (laisse à l'admin le
  contrôle du timing — un restart coupe ~30s la box).

## 0.4.0 — 2026-04-26 (initial HAOS port)

Première version add-on Home Assistant OS, dérivée de l'agent Python
container Debian existant (dossier `agent/` à la racine du repo Moli,
v0.4.0).

### Ajouts

- Add-on natif HA OS, base `ghcr.io/home-assistant/{arch}-base-python:3.12-alpine3.20`,
  multi-arch `amd64` + `aarch64` (Raspberry Pi 5, mini PC N100/i5 reconditionnés).
- Détection automatique du runtime (`MOLINI_RUNTIME=haos` posé par `run.sh`).
- Auth HA Core via proxy supervisor (`SUPERVISOR_TOKEN`), plus besoin de
  Long-Lived Access Token côté utilisateur.
- Nouveau module `supervisor_client.py` qui wrappe l'API supervisor pour
  les commandes admin qui touchent à la stack.
- Le module `service_status.py` remplace `docker_status.py` en mode HAOS :
  on liste les add-ons via supervisor au lieu du socket Docker.
- Backup volumes par défaut adaptés HAOS : `/config` + `/share/zigbee2mqtt`
  au lieu de `/home/rudy/docker/...`.
- Heartbeat enrichi avec le champ `runtime` (= `haos` ou `debian`).

### Modifications par rapport à `agent/` (Debian)

- `ha_restart` : utilise `POST /core/restart` du supervisor (était
  `docker restart homeassistant`).
- `stack_update` : itère les add-ons HA et `addon_update` ceux qui ont
  `update_available=true` (était `docker compose pull/up` sur les
  sous-dossiers de `/home/rudy/docker`).
- `tunnel_install` / `tunnel_uninstall` : passent par l'add-on
  cloudflared communautaire (était écriture d'un docker-compose.yml local).
- `agent_update` : **désactivé** (les MAJ passent par le store HA add-on).

### Limitations connues

- Le slug exact de l'add-on cloudflared n'est pas encore figé : l'agent
  cherche le 1er add-on qui contient `cloudflared` dans son nom ou son slug.
- Pas encore d'icône `icon.png` / `logo.png` (l'add-on s'affiche avec
  l'icône par défaut HA).
- Pas encore publié sur Git → install en mode local uniquement
  (copier `box/addons/molini-agent/` dans `/addons/molini-agent/` sur la
  box HA).
