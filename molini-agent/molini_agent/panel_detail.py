# molini-agent/molini_agent/panel_detail.py
"""Génère le bloc « détail par panneau » de la page Énergie à partir des
capteurs PV détectés côté HA.

Regroupe les strings par INSTALLATION (marque) — SolarMan (`inverter*`),
IzyPower (`izypower*`) — et rend chaque panneau comme une `custom:button-card`
qui se **remplit** (dégradé vert/ambre) proportionnellement à sa production.
Spécifique au client (généré, pas statique) → référence les entity_id réels."""
from __future__ import annotations

import re
from typing import Any

# Capteur de puissance d'un string : finit par _pvN (IzyPower) ou _pvN_power
# (SolarMan). Exclut le reste (ex inverter_2_power = total AC).
_PV_RE = re.compile(r"^(?P<prefix>.+?)_pv(?P<n>\d+)(?:_power)?$")
# Onduleur string SolarMan : sensor.inverter, sensor.inverter_2, …
_SOLARMAN_RE = re.compile(r"(?:^|\.)inverter(?:_\d+)?$")

PANEL_FLOOR_W = 450   # plancher du plafond de remplissage d'un string
PANEL_HEADROOM = 1.1  # marge au-dessus du pic observé


def detect_panels(entity_ids: set[str]) -> dict[str, list[str]]:
    """Groupe les capteurs PV par préfixe d'onduleur. Retourne {prefix: [eids triés]}."""
    groups: dict[str, list[str]] = {}
    for eid in entity_ids:
        if not eid.startswith("sensor."):
            continue
        m = _PV_RE.match(eid)
        if not m:
            continue
        groups.setdefault(m.group("prefix"), []).append(eid)
    for prefix in groups:
        groups[prefix].sort(key=lambda e: int(_PV_RE.match(e).group("n")))
    return groups


def _is_micro(prefix: str) -> bool:
    p = prefix.lower()
    return "izypower" in p or "micro" in p


def inverter_label(prefix: str, index: int) -> str:
    """Libellé d'un onduleur de marque inconnue (fallback)."""
    return f"{'Micro-onduleur' if _is_micro(prefix) else 'Onduleur'} {index + 1}"


def _brand_of(prefix: str) -> str | None:
    p = prefix.lower()
    if "izypower" in p:
        return "izypower"
    if _SOLARMAN_RE.search(p):
        return "solarman"
    return None


_BRAND_LABEL = {"solarman": "Onduleur SolarMan", "izypower": "Micro-onduleurs IzyPower"}


def group_panels(entity_ids: set[str]) -> list[dict[str, Any]]:
    """Regroupe les strings par installation. [{key, label, panels:[{name,eid}]}]."""
    by_prefix = detect_panels(entity_ids)
    groups: dict[str, dict[str, Any]] = {}
    unknown = 0
    for prefix in sorted(by_prefix):
        brand = _brand_of(prefix)
        key = brand or f"other:{prefix}"
        if key not in groups:
            if brand:
                label = _BRAND_LABEL[brand]
            else:
                label = inverter_label(prefix, unknown)
                unknown += 1
            groups[key] = {"label": label, "eids": []}
        groups[key]["eids"].extend(by_prefix[prefix])

    rank = {"solarman": 0, "izypower": 1}
    ordered = sorted(groups.items(), key=lambda kv: (rank.get(kv[0], 2), kv[0]))
    return [
        {
            "key": key,
            "label": g["label"],
            "panels": [{"name": f"P{i + 1}", "eid": eid} for i, eid in enumerate(g["eids"])],
        }
        for key, g in ordered
    ]


def _panel_bg(ceiling_w: int) -> str:
    # fond qui se remplit par le bas selon la prod (vert, ambre si < 20 %).
    return (
        "[[[ const w = Number(entity.state) || 0; "
        "const pct = Math.min(100, Math.round(w / " + str(ceiling_w) + " * 100)); "
        "const c = pct < 20 ? '186,117,23' : '29,158,117'; "
        "return `linear-gradient(to top, rgba(${c},0.85) ${pct}%, #0e1b2a ${pct}%)`; ]]]"
    )


def _panel_card(name: str, eid: str, ceiling_w: int) -> dict[str, Any]:
    return {
        "type": "custom:button-card",
        "entity": eid,
        "name": name,
        "show_icon": True,
        "icon": "mdi:solar-panel",
        "show_name": True,
        "show_state": True,
        "tap_action": {"action": "more-info"},
        "styles": {
            "card": [
                {"height": "84px"},
                {"border": "1px solid #2a3340"},
                {"border-radius": "10px"},
                {"padding": "8px 6px 6px"},
                {"background": _panel_bg(ceiling_w)},
                {"box-shadow": "inset 0 1px 0 rgba(255,255,255,0.06)"},
            ],
            "icon": [{"width": "24px"}, {"color": "rgba(255,255,255,0.92)"}],
            "name": [{"font-size": "11px"}, {"color": "#e6e9ef"}, {"margin-top": "2px"}],
            "state": [{"font-size": "16px"}, {"font-weight": "600"}, {"color": "#ffffff"}],
        },
    }


def panel_entity_ids(available: set[str]) -> list[str]:
    """Liste plate des entity_id de strings PV que build_panel_cards utilisera."""
    groups = group_panels(available)
    return [p["eid"] for g in groups for p in g["panels"]]


def build_panel_cards(
    entity_ids: set[str],
    sensor_maxes: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Cartes du détail par panneau : par installation, une grille de panneaux
    qui se remplissent. [] si aucun PV détecté."""
    groups = group_panels(entity_ids)
    if not groups:
        return []
    cards: list[dict[str, Any]] = []
    for g in groups:
        cards.append({"type": "heading", "heading": g["label"], "heading_style": "subtitle"})
        panel_cards = []
        for p in g["panels"]:
            eid = p["eid"]
            ceiling = max(
                int(round((sensor_maxes or {}).get(eid, 0) * PANEL_HEADROOM)),
                PANEL_FLOOR_W,
            )
            panel_cards.append(_panel_card(p["name"], eid, ceiling))
        cards.append({
            "type": "grid",
            "columns": 3,
            "square": False,
            "cards": panel_cards,
        })
    return cards
