# Changelog

## 0.8.0 — 2026-06-18 (panel front Moli — surcouche HA, écran Énergie)

- **Panel front custom** : nouvelle app Preact (`molini-panel/`) embarquée dans l'add-on, servie sur `/local/moli/moli-panel.js` et enregistrée comme `panel_custom` (« Moli » dans la sidebar HA **et** l'app mobile). HA reste le back (auth, appareils, historique, tunnel) ; le panel ne fait que la présentation via la connexion `hass` (WebSocket). Aucune API ni auth à héberger.
- **Écran Énergie** : production instantanée + aujourd'hui/total, **détail par panneau** regroupé par onduleur (tuiles compactes + mini-barres, numérotation par type), graphe 24 h (SVG maison), compteur HC/HP, tuile conso conditionnelle. Logique de détection PV portée en TS (depuis `panel_detail` 0.7.0).
- **Agent** : `panel_custom` ajouté à la white-list `PATCHABLE_TOP_KEYS` (JS client, pas de RCE serveur) + posé au provision via `MOLI_HA_CONFIG_PATCH` (idempotent) ; le `run` dépose le bundle dans `/config/www/moli`.
- Bundle single-file ~36 kB (gzip ~11 kB), styles isolés en shadow DOM. Coexiste avec les dashboards Lovelace (fallback) ; bascule en accueil par défaut + kiosk à venir.

## 0.7.0 — 2026-06-18 (détail par panneau — Phase 1 panel énergie)

- Page Énergie : **détail par panneau**. Grille de production par string générée dynamiquement par onduleur (cartes natives `grid` + `gauge`, une jauge par panneau bornée à 600 W). Détection auto des capteurs PV (SolarMan `*_pvN_power` et IzyPower `*_pvN`) depuis les entités HA réelles — un client à 12 panneaux voit ses 12 jauges sans config manuelle.
- Builder : marqueur `MOLINI_PANELS` dans le bloc `energie` remplacé par les cartes générées (`dashboard_builder.build_yaml(dynamic_cards=…)`, propagé via `build_and_write` et `execute_rebuild_dashboard`).
- Tuile **consommation conditionnelle** : aperçu « Consommation maison » affiché automatiquement dès que `sensor.molini_consommation_maison` existe (masqué sinon).

## 0.6.1 — 2026-06-18 (fix entity_id dashboard énergie)

- La page Énergie référençait les `unique_id` (`molini_solar_power_w`…), mais HA
  dérive l'`entity_id` d'un template sensor de son `name` (slug). Les vraies
  entités sont donc `sensor.molini_solaire_production` / `_aujourd_hui` /
  `_totale`. Le bloc `energie.yaml` pointe désormais dessus. (Les index Linky
  marchaient déjà, leur slug coïncidant avec l'unique_id.)

## 0.6.0 — 2026-06-18 (dashboard énergie générique)

- **Dashboard Lovelace modulaire opérationnel** : les blocs (`energie`, `_header`,
  `aide`, `_reglages`) sont packagés dans l'add-on et déposés sur la box au
  démarrage (`/config/dashboards/blocks/`) — ce qui débloque `rebuild_dashboard`
  (les fichiers de blocs n'étaient packagés nulle part avant, d'où le « Block
  file not found »).
- **Découverte multi-onduleurs** : `molini_solar_power_w` somme tous les onduleurs
  détectés (SolarMan `inverter*` + IzyPower `*puissance_pv` + Enphase/Huawei/
  SolarEdge), en DC homogène. Nouveaux capteurs `molini_solar_energy_total`,
  `molini_conso_power_w`. Index Linky reconnus depuis Zlinky `consommation_partie_*`.
- Page **Énergie** : production solaire (jauge + total + historique 24 h) + index
  compteur ; consommation / réseau / Tempo annoncés « à venir » (Linky TIC standard).

## 0.5.2 — 2026-06-18 (fixes wizard install + versioning)

- **install_addon idempotent** : `install_or_start_addon` détectait mal un add-on
  déjà installé (lisait `version_installed`/`installed` au lieu de `version`, et
  ignorait `source="installed_*"`) → il relançait l'install → 400
  `already_installed` → faux `failed` dans le wizard. Corrigé.
- **Versioning** : le `Dockerfile` lit désormais `BUILD_VERSION` (injecté par le
  superviseur au build) au lieu d'un `0.5.0` figé → le heartbeat rapporte la vraie version.

## 0.5.1 — 2026-06-18 (hotfix — conflits de merge 0.5.0 non résolus)

La 0.5.0 avait été publiée avec 4 conflits de merge git restés dans le code
(`commands.py` ×3, `tests/conftest.py` ×1), entre le chantier A (bootstrap_stack
/ install_addon / patch_ha_config) et le chantier E (rebuild_dashboard) →
SyntaxError → l'agent crashait au démarrage sur toute box passée en 0.5.0.
Conflits résolus en **union** (les deux chantiers sont complémentaires, aucune
fonction commune). Aucun changement de logique. Validé : py_compile, import,
34 tests bootstrap/security verts.

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
