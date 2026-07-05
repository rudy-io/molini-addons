# Changelog

## 0.18.1

**🐛 Fix nommage entity_id (régression 0.18.0)** : HA dérive l'`entity_id` d'un
capteur template de son **`name`** (slugifié), pas de son `unique_id`. Plusieurs
capteurs 0.18.0 avaient `slug(name) ≠ unique_id ≠ référence` (ex. name « MOLINI
Réseau » → `sensor.molini_reseau`, mais packages/dashboard référençaient
`molini_reseau_w`) → capteurs conso/autoconso/chauffe-eau introuvables. Aligné
`slug(name) == unique_id == référence` pour `molini_reseau`, `molini_chauffe_eau`
(+ switch `switch.molini_chauffe_eau`), `molini_taux_autoconsommation`. **Test
garde-fou** ajouté (`test_*_slug_matches_unique_id`) pour verrouiller l'invariant.

## 0.18.0

**⚡ Consommation totale + autoconsommation via pince Shelly Pro 3EM** (débloque
ce que le Linky seul ne pouvait pas mesurer — modèle retiré en 0.15.0 faute de
pince, ressuscité ici avec une mesure réseau précise et signée) :

- **ha_discovery** : nouveaux rôles génériques (aucune MAC en dur) —
  `grid_power` (Shelly Pro 3EM/EM, puissance réseau **signée** : >0 soutiré,
  <0 injecté), `grid_import_total` / `grid_export_total` (énergies cumulées),
  et détection du **chauffe-eau** (switch renommé « Chauffe-eau » → alias stable
  `switch.molini_chauffe_eau` + capteur `sensor.molini_chauffe_eau_w`).
- **Consolidation des sources de vérité** : le solaire repasse sur le nommage FR
  canonique (`molini_solaire_production*`, aligné dashboard/panel/rapport) —
  plus de `molini_solar_power_w` divergent.
- **Package `molini_energy`** : `molini_consommation_maison` (= production +
  réseau), `molini_autoconsommation`, `molini_taux_autoconso`,
  `molini_couverture_solaire`, soutiré/injecté temps réel + compteurs jour
  (3EM). Dégradation gracieuse : sans pince, repli Linky et conso masquée (on
  n'invente rien).
- **Dashboard Énergie** : section consommation + autoconso, courbe 24 h
  prod/conso/réseau, **carte chauffe-eau avec bouton marche/arrêt manuel**,
  retrait des placeholders « pince à venir ».

## 0.17.1

**🔥 Fix build bloquant (bug latent depuis des mois)** : le `pip install`
échouait sur toute box qui buildait l'image SANS cache de layer (« gcc: No
such file » en compilant psutil depuis les sources — pas toujours de wheel
musl/aarch64). Le cache masquait le problème tant que `requirements.txt` ne
changeait pas et que l'image de base n'était pas rafraîchie ; le `--pull` du
2026-07-02 l'a révélé. **Concrètement : une box VIERGE ne pouvait pas
installer l'add-on.** Fix : toolchain de build temporaire dans le Dockerfile
(`apk add --virtual .build-deps gcc musl-dev python3-dev linux-headers` →
pip install → `apk del .build-deps`).

## 0.17.0

**Onboarding v0.8 — pose automatique de la config HA Moli** (fini le « posé à
la main chez Carole ») :

- Nouveau module `moli_config.py` : pose `homeassistant: packages:
  !include_dir_named packages` + `lovelace: dashboards: moli-energie:` (clé
  avec tiret, mode yaml, `dashboards/molini.yaml`) dans `configuration.yaml`.
  - **Contenu FIGÉ dans le code** (aucun payload du central) — c'est le
    « mécanisme dédié hors white-list patch » : `homeassistant`/`lovelace`
    restent interdits à `patch_ha_config`.
  - **Conservateur** : n'écrit que ce qui MANQUE, ne modifie jamais une valeur
    existante (un `packages:` custom ou un dashboard `moli-energie` perso sont
    laissés intacts). Idempotent, backup `.bak-YYYYMMDD`, écriture atomique.
  - Erreur de parse YAML → on ne touche PAS au fichier.
- **Appelé au boot de l'agent** (HAOS) : une box neuve a sa config posée dès le
  premier démarrage de l'add-on. Le restart HA qui la charge reste piloté par
  le central (jamais auto au boot → pas de boucle de restart).
- **Appelé par `bootstrap_stack`** (rapport `moli_config` +
  `ha_restart_pending` fusionné) et disponible en commande dédiée
  `ensure_moli_config`.
- Heartbeat : `bootstrap_state.moli_config_ok` (true/false/null) — le wizard
  central sait si la config est posée.
- Tests : +11 (`test_moli_config.py`), suite verte 180/180.

## 0.16.1

**Garde-fou ZHA** (audit 2026-07-02) — ne JAMAIS poser Zigbee2MQTT sur une box
déjà en ZHA (conflit de coordinateur — cas Carole, dongle ZBT-2) :

- Nouveau module `zigbee.py` : détection du stack (`zha`/`z2m`/`both`/`none`/
  `unknown`) via les config entries HA Core (sonde ZHA) + les add-ons
  superviseur (sonde Z2M). Best-effort, ne lève jamais.
- `install_addon zigbee2mqtt` **refusé** si ZHA détecté
  (`zha_detected_conflict`). Override explicite : `{"force_z2m": true}`.
- `bootstrap_stack` **skip** Z2M si ZHA détecté (action `skipped` avec
  `reason: zha_detected` dans le rapport) — le reste de la stack s'installe
  normalement. Même override `force_z2m`.
- Détection `unknown` = fail-open (une sonde KO ne bloque pas une install
  saine — le blocage ne vise que le conflit avéré).
- Heartbeat : `bootstrap_state.zigbee_stack` remonte le stack au central
  (badge admin + wizard qui masque l'install Z2M sur box ZHA, à venir côté
  central).
- **Fix** `DEFAULT_BLOCKS` : retrait de `chauffage` (bloc white-listé mais
  jamais livré dans rootfs/ → `rebuild_dashboard` sans payload échouait sur
  `Block file not found`, gotcha prod 0.9.0). `DEFAULT_BLOCKS` = uniquement
  des blocs embarqués.
- Tests : +13 tests (`test_zigbee_guard.py`), suite verte 169/169 dans le repo
  standalone (conftest : fallback blocs `rootfs/`, tests dashboards alignés
  sur les blocs livrés + layout `sections`).
- CI GitHub Actions : pytest + py_compile sur chaque push/PR (la 0.5.0 cassée
  ne doit plus pouvoir arriver sur le store).

## 0.16.0

- **Conversation Moli AI dans Assist** : l'add-on déploie un composant HA (`custom_components/moli_ai`) qui branche l'agent de conversation de Home Assistant sur le cerveau central Moli AI (`/api/agent/converse`). L'occupant peut désormais **discuter avec Moli en français** depuis Assist (état de la maison, énergie…). Auto-configuré au démarrage (central_url + token déposés par l'add-on ; marqueur `moli_ai:` dans `configuration.yaml`). Après MAJ : **redémarrer HA**, puis Réglages → Assist : choisir « Moli AI » comme agent de conversation + exposer les entités.

## 0.15.0

- **Dashboard honnête (le Linky ne mesure que le réseau, pas la conso totale)** : le compteur de Carole n'expose pas l'injection, et le solaire autoconsommé lui est invisible → impossible de calculer la conso totale / l'autoconso sans une pince de mesure dédiée. On arrête donc d'afficher une fausse conso. Le dashboard montre désormais ce qui est **fiable et utile** : production solaire + **« Réseau (EDF) »** (le soutiré = ce qu'elle achète à EDF) + **« Tiré du réseau aujourd'hui »** en kWh et en € (compteur journalier `utility_meter` sur l'EAST). Mention « conso totale & autoconso : à l'installation de la pince ».
- Retrait des capteurs faux (`molini_consommation_maison`/`_autoconsommation`/`_reseau_injecte` basés sur la « puissance totale » qui s'est avérée être un artefact figé en 0.14.0). Nouveau rôle `linky_soutire_total` → `molini_soutire_total` (EAST), `linky_net_power` retiré.

## 0.14.0

- **Fix conso = prod en journée** : le compteur de Carole ne sort pas le SINSTI standard, donc en injection (surplus le jour) le soutiré=0 et `molini_consommation_maison` retombait sur la production (prod et conso superposées). L'injection est en fait dans la **puissance réseau totale** (ElectricalMeasurement `total_active_power` = magnitude du flux net). Nouveau rôle `linky_net_power` → `molini_puissance_totale`, et modèle corrigé : `injecté = puissance_totale quand soutiré ~0` (sinon 0, pas de faux positif en soutirage) ; **conso = prod + soutiré − injecté** ; autoconso = prod − injecté. Dégrade proprement (injecté=0) si la puissance totale n'est pas détectée.

## 0.13.0

- Modèle **consommation / autoconsommation** : nouveaux capteurs `molini_consommation_maison` (= production + puissance réseau), `molini_reseau_soutire`, `molini_reseau_injecte`, `molini_autoconsommation` (package `molini_energy.yaml` auto-déployé dans `/config/packages`). Conçu pour rester juste que la puissance réseau soit « soutiré seul » ou « nette signée ».
- `ha_discovery` détecte la puissance réseau active du Linky (`*zlinky*_puissance`) → `molini_puissance_soutiree` ; rôle `conso_power` (qui mappait à tort le soutiré comme « conso ») retiré au profit du capteur dérivé.
- Dashboard : jauge consommation (enfin alimentée), consommation ajoutée à la courbe 24 h, et section « Répartition en direct » (production / conso / autoconsommée / soutiré / injecté).

## 0.12.0

- Mode « appliance Moli » : pour les utilisateurs **non-admin** (kiosk-mode chargé via `extra_module_url`), la **sidebar HA est masquée** — ils ne voient que le dashboard Moli. Les admins gardent l'interface complète.
- Bouton **« Configurer Home Assistant »** (onglet Réglages) → `?disable_km` → réaffiche l'interface HA complète (on ne verrouille personne).
- Suppression de l'ancien panneau `panel_custom` Moli (front Preact abandonné) : retiré du patch + nouvelle capacité `patch_ha_config` `{"remove": ["panel_custom"]}` pour le retirer des box existantes.
- `kiosk-mode.js` embarqué dans l'add-on (comme button-card/apexcharts), zéro HACS manuel.

## 0.11.1

- Fix de l'auto-calibrage 0.11.0 : l'historique HA ne remonte en pratique que **~2 j** (le recorder purge au-delà → requête vide), donc le calibrage retombait sur les **planchers** (3000 W / 450). Désormais le **pic max-ever est mémorisé** dans un store persisté `/config/.moli_capacities.json`, **alimenté en continu par le heartbeat** (toutes les 5 min, depuis les états déjà lus — aucun appel HA en plus) + seedé par une fenêtre historique courte (2 j) au rebuild. Le calibrage ne perd plus jamais le pic réel observé.

## 0.11.0

- Jauge production et remplissage des panneaux **auto-calibrés sur la capacité réelle** de chaque installation : le plafond = pic observé (historique 14 j) + 10 % de marge, avec planchers de sécurité (prod 3000 W, panneau 450 W). Chaque panneau se remplit par rapport à SON propre pic. Fini les valeurs en dur. (jauge conso inchangée pour l'instant — pas de données conso.)
- Fix : ordre de substitution des tokens (`__PRIX_KWH__` était un préfixe de `__PRIX_KWH_FR__` → tarif affiché cassé). Substitution désormais des tokens les plus longs d'abord.

## 0.10.0

- Jauges et remplissage panneaux : plafonds relevés (mesurés sur la vraie installation de Carole). Jauge **Production** max 5000 → **6000 W** (elle saturait : pic du jour ~5200 W), jauge **Consommation** max 6000 → **9000 W**, remplissage **par panneau** `PANEL_MAX_W` 400 → **600 W** (strings SolarMan ~430 W / IzyPower ~460 W au pic). Segments des jauges ré-échelonnés en conséquence.

## 0.9.0

- Prix de l'électricité configurable (option `prix_kwh`, défaut 0.2516 €/kWh) : le champ « € économisés » du dashboard utilise désormais le vrai tarif du client (substitution `__PRIX_KWH__` à la génération du dashboard).
- Thème « Moli » (fond navy de marque, accents vert/ambre, cartes arrondies) ajouté à `frontend.themes` et appliqué aux vues du dashboard via `theme: Moli`.

## 0.8.9 — 2026-06-19 (dashboard en une seule colonne)

- Vue Énergie en **une seule colonne** (`max_columns: 1`) : les grandes sections (production, panneaux, courbe, compteur) s'empilent les unes sous les autres.
- Sert aussi de release de **validation de l'update à distance on-demand** (déployée via `agent_self_update`, sans MAJ manuelle).

## 0.8.8 — 2026-06-19 (fix update on-demand + retouches dashboard)

- **Fix `agent_self_update`** : on **rafraîchit l'entité update** (`homeassistant.update_entity`) AVANT `update.install`. Sans ça, `update.install` réinstalle la version périmée que l'entité croit être la dernière (= no-op, constaté en 0.8.7). Devrait débloquer la MAJ on-demand à distance.
- **Dashboard** : panneaux button-card avec **icône** + style amélioré ; jauges **production/consommation côte à côte** (2 colonnes ; conso visible dès que le capteur existe) ; « Produit aujourd'hui » affiche les **€ économisés** (prix 0,2516 €/kWh par défaut — à rendre configurable) ; **apexcharts en production seule** (ne plante plus sur le capteur conso absent).

## 0.8.7 — 2026-06-19 (dashboard énergie natif full HA — sections + button-card + apexcharts)

- **Bloc `energie.yaml` en vue `sections`** (corrige le scramble masonry) : jauges natives production/consommation, détail par panneau, courbe 24 h, compteur.
- **Détail par panneau** (`panel_detail.py`) regroupé **par installation** (SolarMan/IzyPower) ; chaque panneau = **`custom:button-card` qui se remplit** (dégradé vert/ambre selon la prod, template JS).
- **Courbe 24 h** : `custom:apexcharts-card` production + consommation superposées.
- **Cartes Lovelace embarquées** dans l'add-on (`button-card`, `apexcharts-card`) → déposées dans `/config/www/moli-cards` par le `run` + chargées via **`frontend: extra_module_url`** (patché par l'agent) — **sans HACS manuel**, télé-géré.
- `dashboard_builder._inject_dynamic_cards` gère désormais l'injection du marqueur dans une vue **sections** (et toujours masonry).

## 0.8.6 — 2026-06-19 (fix gate self-update)

- **Fix `agent_self_update`** : la décision « une MAJ est-elle dispo ? » se base désormais sur la **vue fraîche du superviseur** (`addons/self/info` → `update_available`), pas sur l'attribut `latest_version` de l'entité `update.*` de HA Core — qui peut **traîner ~1 jour** et faisait conclure « already latest » à tort (constaté en validation 0.8.5). L'entité ne sert plus qu'à fournir l'`entity_id` à `update.install` ; le superviseur installe SA dernière version (fraîche). Petit retry après `store_reload` (asynchrone).

## 0.8.5 — 2026-06-19 (release de validation : self-update à distance)

- Bump de version (sans code) pour valider que `agent_self_update` (via `update.install` de HA Core) met bien à jour la box pilote **0.8.4 → 0.8.5 sans aucune action manuelle**.

## 0.8.4 — 2026-06-19 (fix MAJ à distance : update.install via HA Core)

- **Fix `agent_self_update`** : le superviseur **interdit à un add-on de s'updater en direct** (`POST /addons/self/update` → 403 « can't update itself », constaté en validation 0.8.3). On déclenche désormais la MAJ via le service HA Core **`update.install`** sur l'entité `update.*` de l'add-on (retrouvée par son `title`) — HA Core est l'acteur, donc autorisé. C'est le mécanisme de la 0.5.1, automatisé.
- **`HAClient.call_service`** ajouté (POST `/api/services/<domain>/<service>`, best-effort).
- `store_reload` (validé OK avec le rôle `manager`) reste appelé d'abord pour rendre la nouvelle version visible.

## 0.8.3 — 2026-06-19 (release de validation : MAJ à distance)

- Bump de version (sans changement de code) pour **valider de bout en bout le self-update à distance** (`agent_self_update` : `store_reload` → `addon_update` sur soi) sur la box pilote, sans aucune action manuelle sur la box.

## 0.8.2 — 2026-06-19 (MAJ de l'agent à distance, sans toucher la box)

- **`store_reload`** (`POST /store/reload`) ajouté au `supervisor_client` : rafraîchit le catalogue du store → rend visible une version fraîchement poussée. C'est la brique qui manquait pour mettre à jour sans « Vérifier les MAJ » manuel.
- Commande **`agent_self_update`** : `store_reload` → `addons/self/info` → `addon_update` sur soi si une MAJ existe. MAJ du plugin Moli **100 % à distance** (le superviseur stoppe+update l'add-on ; le résultat de commande peut remonter en échec — la **vraie** confirmation est le heartbeat suivant qui annonce la nouvelle version).
- Commande **`enable_auto_update`** : pose `auto_update: true` sur l'add-on (MAJ posées par le superviseur sans même une commande).
- `stack_update` rafraîchit désormais le store avant de chercher les MAJ.
- Requiert `hassio_role: manager` (déjà en place) ; basculer en `admin` si `/store/reload` refuse le rôle manager.

## 0.8.1 — 2026-06-19 (redesign écran énergie : jauges + panneaux remplis)

- **Jauges demi-cercle** pour la production et la consommation (la conso s'affiche « non suivie » tant que le capteur Linky TIC standard n'existe pas).
- **Panneaux dessinés** : chaque string est un module PV qui se remplit (vert, ambre si très faible) proportionnellement à sa production.
- **Regroupement par installation** : strings regroupés par marque (SolarMan via `inverter*`, IzyPower via `izypower*`) au lieu d'un groupe par onduleur — 2 installations claires plutôt que 4.
- **Courbe 24 h** : production ET consommation superposées (légende ; pas de courbe conso inventée si le capteur n'existe pas sur la box).
- Allègement : titres de section retirés (contenu induit), stat unique « Produit aujourd'hui ».

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
