# Changelog

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
