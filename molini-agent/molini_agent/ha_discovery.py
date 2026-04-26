"""Détection automatique des entités HA + écriture d'un molini_discovered.yaml.

Sous HAOS, le path d'écriture est ``/config/packages/molini_discovered.yaml``
(``/config`` est mappé sur le dossier de configuration HA via ``map: config:rw``
dans ``config.yaml``). Le reload se fait via l'API HA Core (templates +
core config), accessible au travers du proxy supervisor avec
``SUPERVISOR_TOKEN``.
"""
import logging
import os
import re
from typing import Any, Optional

import httpx

from .ha_client import HAClient

log = logging.getLogger("molini_agent.ha_discovery")


# ─── Patterns par rôle MOLINI ────────────────────────────────────
PATTERNS: dict[str, list[str]] = {
    "linky_power": [
        r"^sensor\.(?:linky|sonde_linky|zlinky)[\w_]*(?:papp|puissance_apparente)$",
    ],
    "linky_hc": [
        r"^sensor\.(?:linky|sonde_linky|zlinky)[\w_]*(?:hchc|index_hchc)$",
    ],
    "linky_hp": [
        r"^sensor\.(?:linky|sonde_linky|zlinky)[\w_]*(?:hchp|index_hchp)$",
    ],
    "tempo_today": [
        r"^sensor\.rte_tempo_couleur_(?:actuelle|du_jour)$",
        r"^sensor\.tempo_today$",
    ],
    "tempo_tomorrow": [
        r"^sensor\.rte_tempo_(?:prochaine_couleur|couleur_demain)$",
        r"^sensor\.tempo_tomorrow$",
    ],
    "solar_power": [
        r"^sensor\.envoy[\w_]*current[\w_]*power[\w_]*production[\w_]*$",
        r"^sensor\.envoy_production$",
        r"^sensor\.huawei_solar[\w_]*input_power$",
        r"^sensor\.solaredge[\w_]*ac_power$",
        r"^sensor\.solarman[\w_]*power[\w_]*$",
    ],
    "solar_energy_today": [
        r"^sensor\.envoy[\w_]*today[\w_]*production[\w_]*$",
        r"^sensor\.envoy_energy_today$",
        r"^sensor\.huawei_solar[\w_]*daily_yield$",
        r"^sensor\.solaredge[\w_]*energy_today$",
        r"^sensor\.solarman[\w_]*daily_production$",
    ],
}


def _find_entity(
    states: list[dict[str, Any]], patterns: list[str]
) -> Optional[str]:
    for pat in patterns:
        rx = re.compile(pat, re.IGNORECASE)
        for s in states:
            eid = s.get("entity_id", "")
            state = s.get("state", "")
            if state in ("unknown", "unavailable", "none", None, ""):
                continue
            if rx.match(eid):
                return eid
    return None


async def discover_entities(ha: HAClient) -> dict[str, str]:
    states = await ha.states()
    if not states:
        log.warning("ha_discovery: /api/states vide")
        return {}
    found: dict[str, str] = {}
    for role, patterns in PATTERNS.items():
        eid = _find_entity(states, patterns)
        if eid:
            found[role] = eid
            log.info("ha_discovery: %s → %s", role, eid)
    return found


def _yaml_quote(s: str) -> str:
    return s.replace("'", "''")


def generate_yaml(detected: dict[str, str]) -> str:
    role_specs: dict[str, tuple[str, str, Optional[str], Optional[str], Optional[str]]] = {
        "linky_power": ("MOLINI Puissance Linky", "molini_power_w", "W", "power", "measurement"),
        "linky_hc": ("MOLINI Index HC", "molini_index_hc", "kWh", "energy", "total_increasing"),
        "linky_hp": ("MOLINI Index HP", "molini_index_hp", "kWh", "energy", "total_increasing"),
        "tempo_today": ("MOLINI Tempo aujourd'hui", "molini_tempo_today", None, None, None),
        "tempo_tomorrow": ("MOLINI Tempo demain", "molini_tempo_tomorrow", None, None, None),
        "solar_power": ("MOLINI Solaire production", "molini_solar_power_w", "W", "power", "measurement"),
        "solar_energy_today": ("MOLINI Solaire production aujourd'hui", "molini_solar_energy_today", "kWh", "energy", "total_increasing"),
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
        out.append(f"      - name: '{_yaml_quote(name)}'")
        out.append(f"        unique_id: {uid}")
        if unit:
            out.append(f'        unit_of_measurement: "{unit}"')
        if dc:
            out.append(f"        device_class: {dc}")
        if sc:
            out.append(f"        state_class: {sc}")
        if role in ("linky_hc", "linky_hp"):
            out.append(
                "        state: >\n"
                f"          {{% set v = states('{eid}') | float(0) %}}\n"
                "          {{ (v / 1000) if v > 10000 else v }}"
            )
        elif role in ("tempo_today", "tempo_tomorrow"):
            out.append(
                "        state: >\n"
                f"          {{{{ states('{eid}') | upper }}}}"
            )
        else:
            out.append(f'        state: "{{{{ states(\'{eid}\') }}}}"')
        out.append(f'        availability: "{{{{ states(\'{eid}\') not in [\\"unknown\\",\\"unavailable\\",\\"none\\"] }}}}"')
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
            "ha_discovery: %s écrit (%d entités)",
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
