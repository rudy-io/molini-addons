# molini-agent/molini_agent/panel_detail.py
"""Génère le bloc « détail par panneau » de la page Énergie à partir des
capteurs PV détectés côté HA. 100% cartes natives (grid + gauge).

Spécifique au client (nombre/nom de panneaux variables) → généré, pas statique.
Référence donc les entity_id réels (pas les molini_*)."""
from __future__ import annotations

import re
from typing import Any

# Capteur de puissance d'un string/panneau : finit par _pvN (IzyPower) ou
# _pvN_power (SolarMan). On exclut tout le reste (ex inverter_2_power = total AC).
_PV_RE = re.compile(r"^(?P<prefix>.+?)_pv(?P<n>\d+)(?:_power)?$")


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
    """Vrai si le préfixe désigne un micro-onduleur (IzyPower & co)."""
    p = prefix.lower()
    return "izypower" in p or "micro" in p


def inverter_label(prefix: str, index: int) -> str:
    """Libellé lisible pour un groupe d'onduleur (index = position 0-based DANS SON TYPE)."""
    if _is_micro(prefix):
        return f"Micro-onduleur {index + 1}"
    return f"Onduleur {index + 1}"


PANEL_MAX_W = 600  # borne haute d'un panneau résidentiel (~400-500 W crête)


def build_panel_cards(entity_ids: set[str]) -> list[dict[str, Any]]:
    """Cartes Lovelace natives du détail par panneau. [] si aucun PV détecté."""
    groups = detect_panels(entity_ids)
    if not groups:
        return []
    cards: list[dict[str, Any]] = []
    counters: dict[bool, int] = {}
    for prefix, eids in sorted(groups.items()):
        micro = _is_micro(prefix)
        idx = counters.get(micro, 0)
        counters[micro] = idx + 1
        cards.append({
            "type": "heading",
            "heading": inverter_label(prefix, idx),
            "heading_style": "subtitle",
        })
        cards.append({
            "type": "grid",
            "columns": 4,
            "square": False,
            "cards": [
                {"type": "gauge", "entity": eid, "name": f"P{i + 1}",
                 "min": 0, "max": PANEL_MAX_W, "unit": "W", "needle": True}
                for i, eid in enumerate(eids)
            ],
        })
    return cards
