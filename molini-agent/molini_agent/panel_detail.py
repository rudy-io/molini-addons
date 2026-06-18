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
