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
    # Puissance réseau TOTALE (magnitude du flux net) — sert à déduire
    # l'injection : quand le soutiré (SINSTS) est ~0, c'est qu'on injecte, et
    # injecté = puissance_totale. (ZLinky standard : ElectricalMeasurement
    # total_active_power ; le compteur de Carole ne sort PAS le SINSTI standard.)
    "linky_net_power": [
        r"^sensor\.(?:lixee_)?zlinky[\w_]*_puissance_totale$",
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
    return found


def _yaml_quote(s: str) -> str:
    return s.replace("'", "''")


def _states(eid: str) -> str:
    return "states('" + eid + "')"


def generate_yaml(detected: dict[str, Union[str, list[str]]]) -> str:
    role_specs: dict[str, tuple[str, str, Optional[str], Optional[str], Optional[str]]] = {
        "linky_power": ("MOLINI Puissance soutirée", "molini_puissance_soutiree", "W", "power", "measurement"),
        "linky_net_power": ("MOLINI Puissance totale", "molini_puissance_totale", "W", "power", "measurement"),
        "linky_hc": ("MOLINI Index HC", "molini_index_hc", "kWh", "energy", "total_increasing"),
        "linky_hp": ("MOLINI Index HP", "molini_index_hp", "kWh", "energy", "total_increasing"),
        "tempo_today": ("MOLINI Tempo aujourd'hui", "molini_tempo_today", None, None, None),
        "tempo_tomorrow": ("MOLINI Tempo demain", "molini_tempo_tomorrow", None, None, None),
        "solar_power": ("MOLINI Solaire production", "molini_solar_power_w", "W", "power", "measurement"),
        "solar_energy_today": ("MOLINI Solaire production aujourd'hui", "molini_solar_energy_today", "kWh", "energy", "total_increasing"),
        "solar_energy_total": ("MOLINI Solaire production totale", "molini_solar_energy_total", "kWh", "energy", "total_increasing"),
    }

    out: list[str] = [
        "# MOLINI — molini_discovered.yaml",
        "# Auto-généré par l'agent (commande ha_provision). NE PAS ÉDITER.",
        "# Surcharge les sensors molini_* des packages avec les entity_id détectés.",
        "",
        "template:",
        "  - sensor:",
    ]

    for role, eid in detected.items():
        spec = role_specs.get(role)
        if not spec:
            continue
        name, uid, unit, dc, sc = spec
        eids = eid if isinstance(eid, list) else [eid]
        if not eids:
            continue

        out.append("      - name: '" + _yaml_quote(name) + "'")
        out.append("        unique_id: " + uid)
        if unit:
            out.append('        unit_of_measurement: "' + unit + '"')
        if dc:
            out.append("        device_class: " + dc)
        if sc:
            out.append("        state_class: " + sc)

        if role in MULTI_SUM_ROLES:
            terms = " + ".join("(" + _states(e) + " | float(0))" for e in eids)
            out.append('        state: "{{ ' + terms + ' }}"')
        elif role in ("linky_hc", "linky_hp"):
            e = eids[0]
            out.append(
                "        state: >\n"
                "          {% set v = " + _states(e) + " | float(0) %}\n"
                "          {{ (v / 1000) if v > " + str(WH_TO_KWH_THRESHOLD) + " else v }}"
            )
        elif role in ("tempo_today", "tempo_tomorrow"):
            e = eids[0]
            out.append("        state: >\n          {{ " + _states(e) + " | upper }}")
        else:
            e = eids[0]
            out.append('        state: "{{ ' + _states(e) + ' }}"')

        av = " or ".join(
            _states(e) + " not in ['unknown', 'unavailable', 'none']" for e in eids
        )
        out.append('        availability: "{{ ' + av + ' }}"')
        out.append("")

    return "\n".join(out) + "\n"


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
