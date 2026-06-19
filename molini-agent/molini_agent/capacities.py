# molini-agent/molini_agent/capacities.py
"""High-water-mark des capacités (W) par capteur PV, persisté sur disque pour
auto-calibrer les jauges/panneaux du dashboard.

Pourquoi un store maison plutôt que l'historique HA : le recorder de la box ne
garde en pratique qu'une fenêtre très courte (~2 j observés chez Carole — au-delà
l'API ``/history/period`` renvoie vide). Une fenêtre aussi courte sous-estime la
capacité dès qu'il fait gris. On mémorise donc nous-mêmes le **pic max-ever** par
capteur :

- alimenté **en continu** par le heartbeat (``collect_metrics`` lit déjà tous les
  états toutes les 5 min → aucun appel HA supplémentaire) ;
- éventuellement **seedé** au rebuild par un max historique court (``update_from_maxes``).

Le fichier vit dans ``/config`` (mappé ``rw``). Toutes les écritures sont atomiques
et best-effort : une erreur d'I/O ne casse jamais ni le heartbeat ni le rebuild.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

log = logging.getLogger("molini_agent.capacities")

CAPACITIES_PATH = os.environ.get(
    "MOLINI_CAPACITIES_PATH", "/config/.moli_capacities.json"
)

# Capteurs suivis : la production totale + chaque string PV (même motif que
# panel_detail : finit par _pvN ou _pvN_power ; exclut voltage/current/agrégats).
_PROD_EID = "sensor.molini_solaire_production"
_PV_RE = re.compile(r"^sensor\..+_pv\d+(?:_power)?$")


def _tracked(entity_id: str) -> bool:
    return entity_id == _PROD_EID or bool(_PV_RE.match(entity_id))


def load_capacities(path: str | None = None) -> dict[str, float]:
    """Charge le store {entity_id: max_w}. Renvoie {} si absent/illisible."""
    p = path or CAPACITIES_PATH
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, float] = {}
    for k, v in data.items():
        try:
            out[k] = float(v)
        except (TypeError, ValueError):
            continue
    return out


def _persist(merged: dict[str, float], path: str) -> None:
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(merged, f)
        os.replace(tmp, path)
    except OSError as exc:  # disque plein, FS read-only, etc. — non fatal
        log.warning("capacities: écriture impossible (%s): %s", path, exc)


def _merge(new: dict[str, float], path: str) -> dict[str, float]:
    """Fusionne `new` dans le store en gardant le max par clé. Persiste si changé."""
    merged = load_capacities(path)
    changed = False
    for eid, val in new.items():
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        if v > merged.get(eid, 0.0):
            merged[eid] = v
            changed = True
    if changed:
        _persist(merged, path)
    return merged


def update_from_states(
    states: list[dict[str, Any]] | None, path: str | None = None
) -> dict[str, float]:
    """MAJ le high-water-mark depuis les états HA courants (appelé au heartbeat).

    `states` = sortie de ``GET /api/states``. Best-effort, renvoie le store fusionné.
    """
    p = path or CAPACITIES_PATH
    observed: dict[str, float] = {}
    for s in states or []:
        eid = s.get("entity_id") or ""
        if not _tracked(eid):
            continue
        try:
            observed[eid] = float(s.get("state"))
        except (TypeError, ValueError):
            continue
    return _merge(observed, p)


def update_from_maxes(
    observed: dict[str, float] | None, path: str | None = None
) -> dict[str, float]:
    """Fusionne des maxes observés (ex. seed historique au rebuild) dans le store."""
    p = path or CAPACITIES_PATH
    return _merge(observed or {}, p)
