"""Détection automatique des entités HA + écriture d'un molini_discovered.yaml.

Sous HAOS, le path d'écriture est ``/config/packages/molini_discovered.yaml``
(``/config`` est mappé sur le dossier de configuration HA via ``map: config:rw``
dans ``config.yaml``). Le reload se fait via l'API HA Core (templates +
core config), accessible au travers du proxy supervisor avec
``SUPERVISOR_TOKEN``.

Certains rôles (production solaire) sont **multi-sources** : une installation
peut mélanger plusieurs marques d'onduleurs (SolarMan ``inverter*``, IzyPower
``*puissance_pv``, Enphase, Huawei…) sur des groupes de panneaux distincts. Pour
ces rôles, le sensor ``molini_*`` est la **somme** de toutes les entités
détectées. On privilégie la puissance DC (``pv_power``) pour rester homogène
entre marques (l'AC n'est pas exposé par tous les clouds, ex. IzyPower).
"""
import logging
import os
import re
from typing import Any, Optional, Union

import httpx

from .ha_client import HAClient

log = logging.getLogger("molini_agent.ha_discovery")


# ─── Patterns par rôle MOLINI ────────────────────────────────────
PATTERNS: dict[str, list[str]] = {
    # Puissance soutirée réseau (Linky) — puissance active (W) en priorité,
    # puis sinsts (TIC standard), puis papp/puissance_apparente (TIC historique).
    "linky_power": [
        r"^sensor\.(?:lixee_)?zlinky[\w_]*_puissance$",
        r"^sensor\.(?:linky|sonde_linky|zlinky)[\w_]*sinsts$",
        r"^sensor\.(?:linky|sonde_linky|zlinky)[\w_]*(?:papp|puissance_apparente)$",
    ],
    # Énergie soutirée totale (EAST, cumulatif kWh) — pour le compteur journalier
    # « tiré du réseau » (= payant EDF). C'est la seule mesure conso fiable côté
    # Linky : le solaire autoconsommé lui est invisible (conso totale → pince dédiée).
    "linky_soutire_total": [
        r"^sensor\.(?:lixee_)?zlinky[\w_]*_consommation$",
    ],
    "linky_hc": [
        r"^sensor\.(?:linky|sonde_linky|zlinky)[\w_]*(?:hchc|index_hchc)$",
        r"^sensor\.(?:lixee_)?zlinky[\w_]*consommation_partie_1$",
        r"^sensor\.(?:linky|zlinky)[\w_]*easf01$",
    ],
    "linky_hp": [
        r"^sensor\.(?:linky|sonde_linky|zlinky)[\w_]*(?:hchp|index_hchp)$",
        r"^sensor\.(?:lixee_)?zlinky[\w_]*consommation_partie_2$",
        r"^sensor\.(?:linky|zlinky)[\w_]*easf02$",
    ],
    "tempo_today": [
        r"^sensor\.rte_tempo_couleur_(?:actuelle|du_jour)$",
        r"^sensor\.tempo_today$",
    ],
    "tempo_tomorrow": [
        r"^sensor\.rte_tempo_(?:prochaine_couleur|couleur_demain)$",
        r"^sensor\.tempo_tomorrow$",
    ],
    # Production solaire instantanée — DC, sommée sur TOUS les onduleurs détectés.
    "solar_power": [
        r"^sensor\.inverter(?:_\d+)?_pv_power$",
        r"^sensor\.izypower[\w_]*_puissance_pv$",
        r"^sensor\.envoy[\w_]*current[\w_]*power[\w_]*production[\w_]*$",
        r"^sensor\.envoy_production$",
        r"^sensor\.huawei_solar[\w_]*input_power$",
        r"^sensor\.solaredge[\w_]*dc_power$",
        r"^sensor\.solarman[\w_]*pv[\w_]*power$",
    ],
    "solar_energy_today": [
        r"^sensor\.inverter(?:_\d+)?_today_production$",
        r"^sensor\.izypower[\w_]*_production_jour$",
        r"^sensor\.envoy[\w_]*today[\w_]*production[\w_]*$",
        r"^sensor\.envoy_energy_today$",
        r"^sensor\.huawei_solar[\w_]*daily_yield$",
        r"^sensor\.solaredge[\w_]*energy_today$",
        r"^sensor\.solarman[\w_]*daily_production$",
    ],
    "solar_energy_total": [
        r"^sensor\.inverter(?:_\d+)?_total_production$",
        r"^sensor\.envoy[\w_]*lifetime[\w_]*production[\w_]*$",
        r"^sensor\.huawei_solar[\w_]*total_yield$",
        r"^sensor\.solaredge[\w_]*lifetime_energy$",
        r"^sensor\.solarman[\w_]*total_production$",
    ],
    # ─── Pince de mesure sur l'arrivée générale (Shelly Pro 3EM / EM) ──────
    # Puissance réseau SIGNÉE : > 0 = soutiré (on TIRE du réseau), < 0 = injecté
    # (surplus PV renvoyé). Le tore étant sur l'arrivée générale, on a
    # réseau = conso − production → conso = production + réseau. C'est ce qui
    # débloque la conso totale + l'autoconsommation (invisibles au Linky seul).
    "grid_power": [
        r"^sensor\.shellypro3em_[0-9a-f]+_puissance$",
        r"^sensor\.shellyem_[0-9a-f]+_power$",
        r"^sensor\.shelly_?em[0-9a-f_]*_power$",
    ],
    # Énergie cumulée soutirée / injectée mesurée par la pince (kWh, précis).
    "grid_import_total": [
        r"^sensor\.shellypro3em_[0-9a-f]+_energie$",
        r"^sensor\.shellyem_[0-9a-f]+_energy$",
    ],
    "grid_export_total": [
        r"^sensor\.shellypro3em_[0-9a-f]+_energie_restituee$",
        r"^sensor\.shellyem_[0-9a-f]+_returned_energy$",
    ],
}

# Rôles dont la valeur est la SOMME de toutes les entités détectées (multi-onduleurs).
MULTI_SUM_ROLES: frozenset[str] = frozenset(
    {"solar_power", "solar_energy_today", "solar_energy_total"}
)

# Au-delà de ce seuil, un index est considéré exprimé en Wh → converti en kWh.
# Un index résidentiel en kWh ne dépasse jamais ~1e6 (= 1 GWh) ; en Wh il
# l'atteint vite. Évite de diviser à tort un index Zlinky déjà en kWh (ex 33450).
WH_TO_KWH_THRESHOLD = 1_000_000

_DEAD_STATES = ("unknown", "unavailable", "none", None, "")


def _is_live(state: Any) -> bool:
    return state not in _DEAD_STATES


def _find_entity(
    states: list[dict[str, Any]], patterns: list[str]
) -> Optional[str]:
    for pat in patterns:
        rx = re.compile(pat, re.IGNORECASE)
        for s in states:
            if not _is_live(s.get("state")):
                continue
            if rx.match(s.get("entity_id", "")):
                return s["entity_id"]
    return None


def _find_all_entities(
    states: list[dict[str, Any]], patterns: list[str]
) -> list[str]:
    """Toutes les entités vivantes matchant un pattern (dédupliquées, ordre stable)."""
    found: list[str] = []
    seen: set[str] = set()
    for pat in patterns:
        rx = re.compile(pat, re.IGNORECASE)
        for s in states:
            eid = s.get("entity_id", "")
            if eid in seen or not _is_live(s.get("state")):
                continue
            if rx.match(eid):
                seen.add(eid)
                found.append(eid)
    return found


# Détection du chauffe-eau (charge pilotée) : une SORTIE DE RELAIS SHELLY
# (…_output_N) dont l'entity_id ou le nom convivial contient un mot-clé fort.
# L'installateur renomme la sortie pilotée en « Chauffe-eau » (référentiel Moli)
# → on l'expose via l'alias stable switch.molini_chauffe_eau.
#
# SÛRETÉ (maison occupée) : on ne considère QUE des sorties Shelly (`_output_N`,
# power dérivable) — jamais un switch quelconque de la maison — et on exige un
# mot-clé FORT (pas de `ecs`/`ballon` nu qui matcherait un éclairage « Ballon »).
_WATER_HEATER_RE = re.compile(
    r"(chauffe[\s_-]?eau|cumulus|water[\s_-]?heater|"
    r"ballon[\s_-]?(?:eau|ecs|d['\s_-]?eau)|\becs\b|chauffe_eau)",
    re.IGNORECASE,
)


def _find_water_heater_switch(states: list[dict[str, Any]]) -> Optional[str]:
    """Sortie de relais Shelly (`_output_N`) vivante dont l'entity_id ou le
    friendly_name matche un mot-clé chauffe-eau. Renvoie None si aucune — on
    n'expose jamais un switch non-Shelly (sûreté)."""
    for s in states:
        eid = s.get("entity_id", "")
        if not eid.startswith("switch.") or not _is_live(s.get("state")):
            continue
        # Sûreté : uniquement des sorties Shelly (power dérivable) → jamais un
        # switch maison arbitraire qu'un toggle pourrait couper par erreur.
        if _shelly_output_power_eid(eid) is None:
            continue
        fname = str((s.get("attributes") or {}).get("friendly_name", "") or "")
        if _WATER_HEATER_RE.search(eid) or _WATER_HEATER_RE.search(fname):
            return eid
    return None


def _shelly_output_power_eid(switch_eid: str) -> Optional[str]:
    """Dérive le sensor de puissance d'une sortie Shelly (Pro 4PM / 1PM).

    ``switch.shellypro4pm_xxx_output_0`` → ``sensor.shellypro4pm_xxx_output_0_puissance``.
    Retourne None si l'entity_id ne suit pas le schéma d'une sortie Shelly.
    """
    m = re.match(r"^switch\.(.+_output_\d+)$", switch_eid)
    if m:
        return "sensor." + m.group(1) + "_puissance"
    return None


async def discover_entities(ha: HAClient) -> dict[str, Union[str, list[str]]]:
    states = await ha.states()
    if not states:
        log.warning("ha_discovery: /api/states vide")
        return {}
    found: dict[str, Union[str, list[str]]] = {}
    for role, patterns in PATTERNS.items():
        if role in MULTI_SUM_ROLES:
            eids = _find_all_entities(states, patterns)
            if eids:
                found[role] = eids
                log.info("ha_discovery: %s → %s (somme de %d)", role, ", ".join(eids), len(eids))
        else:
            eid = _find_entity(states, patterns)
            if eid:
                found[role] = eid
                log.info("ha_discovery: %s → %s", role, eid)
    wh = _find_water_heater_switch(states)
    if wh:
        found["water_heater"] = wh
        log.info("ha_discovery: water_heater → %s", wh)
    return found


def _yaml_quote(s: str) -> str:
    return s.replace("'", "''")


def _states(eid: str) -> str:
    return "states('" + eid + "')"


def generate_yaml(detected: dict[str, Union[str, list[str]]]) -> str:
    role_specs: dict[str, tuple[str, str, Optional[str], Optional[str], Optional[str]]] = {
        "linky_power": ("MOLINI Puissance soutirée", "molini_puissance_soutiree", "W", "power", "measurement"),
        "linky_soutire_total": ("MOLINI Soutiré total", "molini_soutire_total", "kWh", "energy", "total_increasing"),
        "linky_hc": ("MOLINI Index HC", "molini_index_hc", "kWh", "energy", "total_increasing"),
        "linky_hp": ("MOLINI Index HP", "molini_index_hp", "kWh", "energy", "total_increasing"),
        "tempo_today": ("MOLINI Tempo aujourd'hui", "molini_tempo_today", None, None, None),
        "tempo_tomorrow": ("MOLINI Tempo demain", "molini_tempo_tomorrow", None, None, None),
        # Nommage FR canonique — aligné sur le dashboard, capacities.py,
        # commands.py, le panel JS et le rapport central. (Consolidation des
        # sources de vérité éclatées : plus de molini_solar_power_w.)
        "solar_power": ("MOLINI Solaire production", "molini_solaire_production", "W", "power", "measurement"),
        "solar_energy_today": ("MOLINI Solaire production aujourd'hui", "molini_solaire_production_aujourd_hui", "kWh", "energy", "total_increasing"),
        "solar_energy_total": ("MOLINI Solaire production totale", "molini_solaire_production_totale", "kWh", "energy", "total_increasing"),
        # Pince arrivée générale (Shelly 3EM/EM) — réseau signé + énergies cumulées.
        # ⚠️ unique_id DOIT == slug(name) : HA dérive l'entity_id du NAME, et les
        # packages/dashboard référencent sensor.<slug(name)>. Voir test garde-fou
        # test_role_spec_uid_matches_name_slug.
        "grid_power": ("MOLINI Réseau", "molini_reseau", "W", "power", "measurement"),
        "grid_import_total": ("MOLINI Réseau soutiré total", "molini_reseau_soutire_total", "kWh", "energy", "total_increasing"),
        "grid_export_total": ("MOLINI Réseau injecté total", "molini_reseau_injecte_total", "kWh", "energy", "total_increasing"),
    }

    header: list[str] = [
        "# MOLINI — molini_discovered.yaml",
        "# Auto-généré par l'agent (commande ha_provision). NE PAS ÉDITER.",
        "# Surcharge les sensors molini_* des packages avec les entity_id détectés.",
        "",
    ]

    sensor_lines: list[str] = []

    def _emit_sensor(
        name: str, uid: str, unit: Optional[str], dc: Optional[str],
        sc: Optional[str], state: str, avail: str,
    ) -> None:
        sensor_lines.append("      - name: '" + _yaml_quote(name) + "'")
        sensor_lines.append("        unique_id: " + uid)
        if unit:
            sensor_lines.append('        unit_of_measurement: "' + unit + '"')
        if dc:
            sensor_lines.append("        device_class: " + dc)
        if sc:
            sensor_lines.append("        state_class: " + sc)
        sensor_lines.append(state)
        sensor_lines.append('        availability: "{{ ' + avail + ' }}"')
        sensor_lines.append("")

    for role, eid in detected.items():
        spec = role_specs.get(role)
        if not spec:
            continue
        name, uid, unit, dc, sc = spec
        eids = eid if isinstance(eid, list) else [eid]
        if not eids:
            continue

        if role in MULTI_SUM_ROLES:
            terms = " + ".join("(" + _states(e) + " | float(0))" for e in eids)
            state = '        state: "{{ ' + terms + ' }}"'
        elif role in ("linky_hc", "linky_hp"):
            e = eids[0]
            state = (
                "        state: >\n"
                "          {% set v = " + _states(e) + " | float(0) %}\n"
                "          {{ (v / 1000) if v > " + str(WH_TO_KWH_THRESHOLD) + " else v }}"
            )
        elif role in ("tempo_today", "tempo_tomorrow"):
            e = eids[0]
            state = "        state: >\n          {{ " + _states(e) + " | upper }}"
        else:
            e = eids[0]
            state = '        state: "{{ ' + _states(e) + ' }}"'

        av = " or ".join(
            _states(e) + " not in ['unknown', 'unavailable', 'none']" for e in eids
        )
        _emit_sensor(name, uid, unit, dc, sc, state, av)

    # ─── Chauffe-eau : capteur de puissance (Shelly) + interrupteur alias ──
    # Format MODERNE `template: - switch:` (et non le legacy `switch: platform:
    # template`) → rechargé par template.reload lors du ha_provision, sans
    # nécessiter un redémarrage HA complet.
    switch_lines: list[str] = []
    wh = detected.get("water_heater")
    if isinstance(wh, str) and wh:
        power_eid = _shelly_output_power_eid(wh)
        if power_eid:
            # ⚠️ uid DISTINCT du switch (même plateforme `template`) : le switch
            # utilise molini_chauffe_eau, le capteur DOIT être différent sinon
            # collision d'unique_id → entités _2 en cascade. Voir garde-fou
            # test_no_duplicate_unique_ids. name "MOLINI Chauffe-eau puissance"
            # → sensor.molini_chauffe_eau_puissance.
            _emit_sensor(
                "MOLINI Chauffe-eau puissance", "molini_chauffe_eau_puissance",
                "W", "power", "measurement",
                '        state: "{{ ' + _states(power_eid) + ' | float(0) }}"',
                _states(power_eid) + " not in ['unknown', 'unavailable', 'none']",
            )
        # Le switch template : name "MOLINI Chauffe-eau" → switch.molini_chauffe_eau
        # (domaine différent du sensor homonyme, pas de collision).
        switch_lines = [
            "      - name: 'MOLINI Chauffe-eau'",
            "        unique_id: molini_chauffe_eau",
            "        state: \"{{ is_state('" + wh + "', 'on') }}\"",
            "        availability: \"{{ " + _states(wh)
            + " not in ['unknown', 'unavailable', 'none'] }}\"",
            "        turn_on:",
            "          - service: switch.turn_on",
            "            target:",
            "              entity_id: " + wh,
            "        turn_off:",
            "          - service: switch.turn_off",
            "            target:",
            "              entity_id: " + wh,
            "",
        ]

    parts: list[str] = list(header)
    if sensor_lines or switch_lines:
        parts.append("template:")
    if sensor_lines:
        parts.append("  - sensor:")
        parts.extend(sensor_lines)
    if switch_lines:
        parts.append("  - switch:")
        parts.extend(switch_lines)

    return "\n".join(parts) + "\n"


async def _trigger_ha_reload(ha_url: str, ha_token: str) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {ha_token}"}
    results: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=15) as client:
        for service in ("template", "homeassistant"):
            endpoint = (
                f"{ha_url}/api/services/{service}/"
                + ("reload" if service == "template" else "reload_core_config")
            )
            try:
                r = await client.post(endpoint, headers=headers, json={})
                results[service] = r.status_code
            except httpx.HTTPError as e:
                results[service] = f"err: {e}"
    return results


async def execute_ha_provision(cfg) -> dict[str, Any]:
    ha = HAClient(cfg.ha_url, cfg.ha_token)
    try:
        detected = await discover_entities(ha)
        if not detected:
            return {
                "ok": True,
                "detected": {},
                "written": False,
                "reason": "no_entities_matched",
            }

        yaml_content = generate_yaml(detected)

        # Sous HAOS, run.sh pose HA_PACKAGES_DIR=/config/packages
        target_dir = os.environ.get("HA_PACKAGES_DIR")
        if not target_dir:
            molini_data = os.environ.get("MOLINI_DATA", "/config")
            target_dir = os.path.join(molini_data, "packages")
        target_path = os.path.join(target_dir, "molini_discovered.yaml")

        os.makedirs(target_dir, exist_ok=True)

        tmp_path = target_path + ".tmp"
        with open(tmp_path, "w") as f:
            f.write(yaml_content)
        os.replace(tmp_path, target_path)
        log.info(
            "ha_discovery: %s écrit (%d rôles)",
            target_path,
            len(detected),
        )

        reload_result = await _trigger_ha_reload(cfg.ha_url, cfg.ha_token)

        return {
            "ok": True,
            "detected": detected,
            "written": True,
            "path": target_path,
            "reload": reload_result,
        }
    finally:
        await ha.close()
