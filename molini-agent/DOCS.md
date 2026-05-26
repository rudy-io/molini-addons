# Moli Agent

Agent Moli pour Home Assistant — communique avec le central `moli.energy`,
gère les backups chiffrés et exécute les commandes envoyées depuis l'admin.

## Configuration

Tous les champs sont exposés sous l'onglet **Configuration** de l'add-on.

### `central_url`

URL du central Moli. Valeur par défaut : `https://moli.energy`. Ne change
que si tu utilises une instance de test.

### `client_token`

**Obligatoire.** Token agent unique à la box. Il est généré côté admin
au moment de la création du client (préfixé `molini_`). Si tu ne l'as
pas, va dans `https://moli.energy/admin/clients/<id>` et copie-le depuis
la card « Agent ».

### `backup_age_recipient`

Clé publique `age` du super_admin (format `age1...`), utilisée pour
chiffrer les backups quotidiens. Si vide, les backups sont **skippés**
(et l'agent log un warning toutes les 24 h).

### `backup_volumes`

Liste séparée par virgules des chemins à inclure dans le tar du backup.
Par défaut : `/config,/share/zigbee2mqtt`. Sous HAOS :

- `/config` = configuration Home Assistant (automations, scripts, etc.)
- `/share` = volume partagé entre add-ons (Z2M data y est typiquement)

### `backup_hour_local`

Heure locale (0-23) à laquelle le backup quotidien est lancé. Défaut : **3**.

### `linky_*_entity`

Les `entity_id` des capteurs Linky / Tempo détectés sur cette installation.
Les défauts correspondent au schéma standard ZLinky + intégration
`hekmon/rtetempo`. Si tu utilises LiXee `sonde_linky_*` ou un autre nom,
adapte ces champs **ou** lance la commande `ha_provision` depuis l'admin
(elle détecte automatiquement les entités et écrit un fichier de mapping).

### `heartbeat_interval_s`

Intervalle entre deux heartbeats vers le central. Défaut : **300** (5 min).
Plage autorisée : 60 à 3600. À ne baisser que pour du debug.

### `log_level`

Niveau de log de l'agent (et de bashio). Défaut : `info`. Pour debug pose
sur `debug`. Visibles dans l'onglet **Log** de l'add-on.

## Premier démarrage

1. Vérifie que l'add-on **Mosquitto broker** est installé et démarré
   (l'agent ne lance pas MQTT pour toi — c'est le rôle d'un add-on tier).
2. Vérifie que l'intégration **Zigbee2MQTT** (en add-on aussi) est OK
   et que ton dongle Sonoff ZBDongle-P est appairé avec ton Linky.
3. Renseigne `central_url`, `client_token` et `backup_age_recipient` dans
   la configuration de cet add-on.
4. Démarre l'add-on, surveille l'onglet **Log** : tu dois voir
   `Heartbeat OK — power=...W cpu=...%`.
5. Côté admin `https://moli.energy/admin/clients/<id>`, le statut du client
   passe à « En ligne » dans les 30 s.

## Commandes admin

Les commandes peuvent être déclenchées depuis l'admin (card « Actions
distantes »). Elles sont récupérées par l'agent à chaque heartbeat
(donc avec une latence max d'environ `heartbeat_interval_s`).

| Commande           | Effet                                                                |
|--------------------|----------------------------------------------------------------------|
| `backup_now`       | Lance immédiatement un backup chiffré + upload central               |
| `ha_restart`       | Redémarre Home Assistant Core (via supervisor)                       |
| `agent_restart`    | Redémarre l'add-on Moli Agent                                        |
| `agent_update`     | **Skipped en HAOS** — les MAJ passent par le store add-on            |
| `stack_update`     | Met à jour tous les add-ons HA qui ont `update_available=true`       |
| `tunnel_install`   | Installe + démarre l'add-on cloudflared avec le token CF fourni      |
| `tunnel_uninstall` | Stop + uninstall l'add-on cloudflared                                |
| `ha_provision`     | Détecte les entités Linky/Tempo/Solaire et écrit un YAML d'override  |
| `bootstrap_stack`  | Provisionne Mosquitto + Z2M + cloudflared + patch HA (idempotent)    |
| `install_addon`    | Installe 1 add-on précis (mosquitto / zigbee2mqtt / cloudflared)     |
| `patch_ha_config`  | Patch deep-merge de `configuration.yaml` (clés white-listées)        |

## Bootstrap automatique (chantier A — depuis 0.5.0)

Pour réduire les frictions d'install (≈3 h documentés au pilote Carole le
25/05/2026), l'installateur ne fait plus que :

1. Brancher la box (RJ45 + USB-C) + SkyConnect Zigbee.
2. Faire l'onboarding HA (créer le compte Owner + `moli-support`).
3. Installer l'add-on Moli Agent depuis le repo `molini-addons`, coller
   le `client_token` + démarrer.

Au premier heartbeat, le central voit que `bootstrap_state.mosquitto` est
`not_installed`, et peut enqueue automatiquement la commande
`bootstrap_stack`. L'agent installe ensuite :

- Mosquitto broker (slug `core_mosquitto`) — démarré
- Zigbee2MQTT (slug `45df7312_zigbee2mqtt`) — démarré
- Cloudflared de Tobi (résolu dynamiquement, pattern `*_cloudflared`)
  — installé mais **pas démarré** (attend le token via `tunnel_install`)
- Patch `/config/configuration.yaml` :
  - `http.use_x_forwarded_for: true`
  - `http.trusted_proxies: [172.30.0.0/16]`
  - `recorder.purge_keep_days: 14`

Une 2e exécution de `bootstrap_stack` est **idempotente** : 0 ré-installation,
0 patch superflu. Le rapport `result.summary` indique précisément ce qui a
été fait : `2 installed, 1 skipped, 0 failed`.

**HA Restart pending** : après le patch `configuration.yaml`, le flag
`ha_restart_pending` du heartbeat passe à `true`. C'est au central de
déclencher ensuite `ha_restart` au bon moment (l'agent ne le fait pas tout
seul pour laisser le contrôle de timing à l'admin).

## Logs et debug

- Onglet **Log** dans l'add-on : niveau piloté par `log_level`.
- Onglet **Configuration** : valider la config en cliquant **Save** —
  l'add-on redémarre automatiquement.
- Sous **Settings → System → Logs → Supervisor**, on voit les appels
  API supervisor faits par l'agent (utile pour debug `ha_restart` ou
  `stack_update`).

## Sécurité

- Le `client_token` est l'**unique secret** qui permet à cette box de
  s'authentifier auprès du central. Ne le partage jamais.
- L'add-on a `hassio_role: manager` — il peut installer, désinstaller,
  démarrer et arrêter d'autres add-ons. C'est nécessaire pour
  `tunnel_install` et `stack_update`. Si tu veux durcir, désactive ces
  deux commandes côté central pour cette box.
- La clé privée `age` correspondant au `backup_age_recipient` reste **chez
  Rudy** (jamais sur la box). Sans elle, aucun backup n'est restaurable —
  c'est volontaire.

## Désinstallation

Stop l'add-on, puis désinstalle. Les volumes mappés (`/config`, `/share`)
ne sont **pas supprimés** — c'est HA qui les possède, l'add-on n'y touche
qu'en lecture (sauf `/config/packages/molini_discovered.yaml` créé par
`ha_provision`, à supprimer à la main si tu veux faire le ménage).
