"""Détection du stack Zigbee de la box (ZHA vs Zigbee2MQTT).

Garde-fou flotte : installer Z2M sur une box déjà en ZHA crée un conflit de
coordinateur (deux stacks qui se disputent le dongle). Cas réel : Carole est
en ZHA (dongle ZBT-2) — un ``bootstrap_stack`` complet lui aurait installé Z2M.

Détection best-effort, ne lève jamais :
- ZHA   → config entries HA Core (``GET /api/config/config_entries/entry``)
- Z2M   → add-ons installés côté superviseur (slug ``*_zigbee2mqtt``)

Politique du garde-fou (voulue) :
- ``zha`` / ``both``  → Z2M est BLOQUÉ (sauf ``force_z2m`` explicite) ;
- ``unknown``         → fail-open (on n'empêche pas une install saine parce
  qu'une sonde a raté) — le blocage ne vise que le conflit AVÉRÉ ;
- ``z2m`` / ``none``  → rien à signaler.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

from . import supervisor_client
from .ha_client import HAClient

log = logging.getLogger("molini_agent.zigbee")

Z2M_SLUG_RX = re.compile(r".*_zigbee2mqtt$", re.IGNORECASE)

ZigbeeStack = str  # "zha" | "z2m" | "both" | "none" | "unknown"


def combine_zigbee(zha: Optional[bool], z2m: Optional[bool]) -> ZigbeeStack:
    """Combine les deux sondes (None = sonde indisponible)."""
    if zha is True and z2m is True:
        return "both"
    if zha is True:
        return "zha"
    if z2m is True:
        return "z2m"
    if zha is False and z2m is False:
        return "none"
    return "unknown"


async def _probe_zha(ha: HAClient | None) -> Optional[bool]:
    if ha is None:
        return None
    entries = await ha.config_entries()
    if entries is None:
        return None
    return any(e.get("domain") == "zha" for e in entries)


async def _probe_z2m() -> Optional[bool]:
    try:
        addons = await supervisor_client.addons_list()
    except Exception as e:  # noqa: BLE001 — best-effort
        log.warning("detect_zigbee_stack: addons_list failed: %s", e)
        return None
    return any(Z2M_SLUG_RX.match(a.get("slug") or "") for a in addons)


async def detect_zigbee_stack(ha: HAClient | None) -> ZigbeeStack:
    """Retourne ``zha`` / ``z2m`` / ``both`` / ``none`` / ``unknown``."""
    zha = await _probe_zha(ha)
    z2m = await _probe_z2m()
    stack = combine_zigbee(zha, z2m)
    log.info("detect_zigbee_stack: zha=%s z2m=%s -> %s", zha, z2m, stack)
    return stack


def zigbee_stack_from_states(
    zha: Optional[bool], z2m_addon_state: str
) -> ZigbeeStack:
    """Variante pour ``collect_bootstrap_state`` qui a déjà l'état de l'add-on
    Z2M sous la main (évite un 2e appel superviseur à chaque heartbeat)."""
    z2m: Optional[bool]
    if z2m_addon_state == "unknown":
        z2m = None
    else:
        z2m = z2m_addon_state != "not_installed"
    return combine_zigbee(zha, z2m)


def guard_payload(stack: ZigbeeStack) -> dict[str, Any]:
    """Bloc standard à remonter au central quand Z2M est skippé/bloqué."""
    return {
        "name": "zigbee2mqtt",
        "status": "skipped",
        "reason": "zha_detected" if stack in ("zha", "both") else "zigbee_guard",
        "zigbee_stack": stack,
        "hint": "Box en ZHA — installer Z2M créerait un conflit de coordinateur. "
        "Passer {\"force_z2m\": true} pour outrepasser (migration assumée).",
    }
