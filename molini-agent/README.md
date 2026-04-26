# Moli Agent — Add-on Home Assistant

Agent Moli pour Home Assistant OS — version add-on natif HAOS de l'agent
Python historiquement déployé en container Docker autonome sur les box
Debian (cf. `agent/` à la racine du repo Moli).

## Quoi ?

- Heartbeat 5 min vers le central `moli.energy` : métriques système (CPU,
  RAM, disk via psutil), métriques HA (entités, Linky, Tempo), liste des
  add-ons installés (via supervisor API).
- Backups quotidiens à 3 h (heure locale) : tar de `/config` + `/share` →
  chiffré avec `age` → upload vers MinIO via le central.
- Polling des commandes admin en attente après chaque heartbeat :
  `backup_now`, `ha_restart` (supervisor `/core/restart`), `agent_restart`,
  `agent_update` (skipped — géré par le store HA), `stack_update`
  (update tous les add-ons éligibles), `tunnel_install`/`tunnel_uninstall`
  (gère l'add-on cloudflared communautaire), `ha_provision` (écrit
  `/config/packages/molini_discovered.yaml` selon les entités détectées).

## Comment ?

Cet add-on hérite de la base image officielle HA
`ghcr.io/home-assistant/{arch}-base-python:3.12-alpine3.20` qui apporte
bashio + s6-overlay + Python 3.12. Le superviseur HA build l'image
localement à l'install.

L'auth vers HA Core se fait via le proxy supervisor
(`http://supervisor/core/api`) avec le token `SUPERVISOR_TOKEN` injecté
automatiquement — **pas besoin de Long-Lived Access Token côté utilisateur**.

## Différence vs container Debian historique

Voir le [README parent](../README.md#différences-avec-lagent-debian-historique)
pour la matrice complète. Résumé :

- L'agent **ne touche plus à `docker.sock`** — toutes les actions stack
  passent par l'API supervisor.
- L'agent **n'a plus d'OTA self-update** — les MAJ sont publiées dans le
  repo add-on, le store HA s'occupe du reste.
- Les volumes de backup par défaut sont `/config` + `/share/zigbee2mqtt`
  (mappés par `config.yaml` dans la section `map`).

## Build & test local

L'image est buildée par le superviseur lui-même quand on installe l'add-on
en local. Pour tester manuellement sur ton poste de dev :

```bash
cd box/addons/molini-agent
docker build \
  --build-arg BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.12-alpine3.20 \
  -t molini-agent-local .
```

L'image résultante n'est pas runnable telle quelle hors HA OS (il manque
le superviseur qui injecte SUPERVISOR_TOKEN), mais `docker run` permet de
vérifier que l'image se construit, que `python -m molini_agent` se charge,
et que `tar` + `age` + `psutil` sont OK.

## Structure

```
molini-agent/
├── config.yaml              ← manifeste add-on (slug, options, schema, map…)
├── build.yaml               ← base images officielles HA par arch
├── Dockerfile               ← apk add age tzdata + pip install + COPY agent
├── requirements.txt         ← httpx, psutil
├── README.md                ← ce fichier (dev / maintainer)
├── DOCS.md                  ← documentation utilisateur (visible dans HA UI)
├── CHANGELOG.md             ← historique des versions add-on
├── rootfs/
│   └── etc/services.d/molini-agent/
│       ├── run              ← bashio → env vars → python -m molini_agent
│       └── finish           ← hook s6 (relance sur exit volontaire)
└── molini_agent/            ← package Python adapté HAOS
    ├── __init__.py
    ├── __main__.py
    ├── runtime.py           ← détection HAOS / debian
    ├── config.py            ← Config.from_env() + log level
    ├── ha_client.py         ← HTTP HA Core (via supervisor proxy)
    ├── supervisor_client.py ← HTTP supervisor (restart, addons CRUD)
    ├── service_status.py    ← liste des add-ons (ex docker_status)
    ├── metrics.py           ← psutil + HA + Linky → payload heartbeat
    ├── backup.py            ← tar + age + upload central
    ├── commands.py          ← dispatcher commandes admin (HAOS-flavored)
    ├── ha_discovery.py      ← écrit /config/packages/molini_discovered.yaml
    └── main.py              ← boucle heartbeat + commands polling
```

## TODO

- [ ] Publier l'add-on via repo Git (`github.com/molini/molini-addons`)
      pour permettre l'install propre en mode repo dans HA UI.
- [ ] Ajouter une icône `icon.png` 128×128 et `logo.png` 250×100.
- [ ] Brancher `tunnel_install` sur un slug cloudflared figé (déterminer
      le slug réel après ajout du repo communautaire — actuellement
      résolu dynamiquement par recherche dans la liste add-ons).
- [ ] Tester en conditions réelles sur Pi 5 avec HAOS 13+ (tag de la
      base image à valider lors du premier déploiement pilote).
- [ ] Adapter le central (`site/`) côté `/api/agent/heartbeat` pour
      stocker `runtime` (`haos` / `debian`) en plus de `agent_version`,
      pour permettre des dashboards segmentés.
