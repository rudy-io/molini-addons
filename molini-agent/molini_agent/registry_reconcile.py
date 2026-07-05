"""Réconciliation du registre d'entités HA pour les entités Moli (self-heal).

Pourquoi ce module (post-mortem 0.18.0 → 0.18.2, box Carole)
------------------------------------------------------------
HA dérive l'``entity_id`` d'une entité template de son **name** slugifié, PAS
de son ``unique_id`` — et le registre est PERSISTANT. Conséquences observées
en prod :

- une entité d'une ancienne version (uid legacy, ex. ``molini_solar_power_w``)
  **squatte** l'entity_id canonique → la nouvelle entité naît en ``_2`` ;
- un delete registre suivi d'un ``template.reload`` est **racé** (l'entité se
  recrée en ``_2`` avant le restart) — la primitive fiable est le **rename
  direct** (``config/entity_registry/update`` + ``new_entity_id``) ;
- des entrées ``disabled_by: user`` héritées d'anciennes versions empêchent
  l'instanciation (entité enregistrée mais sans état) → réactiver + restart.

Ce module AUTOMATISE la récupération faite à la main chez Carole : après
chaque ``ha_provision``, l'agent réconcilie le registre pour que
``entity_id == <domaine>.<unique_id>`` pour toutes les entités Moli attendues.

Design
------
- ``plan_reconcile()`` est **pur** (liste registre → liste d'actions) : testé
  unitairement sans WebSocket.
- ``apply_reconcile()`` exécute le plan via l'API WebSocket HA (le registre
  n'est PAS exposé en REST) — ``ws://supervisor/core/websocket`` avec le
  SUPERVISOR_TOKEN.
- Prudence : on ne touche QUE la plateforme ``template`` avec un uid
  ``molini_*``. Les suppressions sont limitées à une liste **explicite**
  d'uids legacy (jamais « tout uid inconnu » — un rôle temporairement non
  détecté ne doit pas faire supprimer son entité).
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

log = logging.getLogger("molini_agent.registry_reconcile")

# uids d'anciennes versions de l'add-on, sûrs à supprimer (remplacés par le
# nommage canonique consolidé en 0.18.x). Liste EXPLICITE — ne jamais déduire.
LEGACY_UIDS: frozenset[str] = frozenset(
    {
        "molini_solar_power_w",
        "molini_solar_energy_today",
        "molini_solar_energy_total",
        "molini_reseau_w",
        "molini_chauffe_eau_w",
        "molini_taux_autoconso",
        "molini_puissance_totale",  # rôle linky_net_power retiré en 0.15.0
    }
)

# Plateformes que la réconciliation a le droit de toucher.
_PLATFORMS: frozenset[str] = frozenset({"template"})


@dataclass
class Action:
    kind: str  # "remove" | "rename" | "enable"
    entity_id: str
    new_entity_id: Optional[str] = None
    reason: str = ""


@dataclass
class ReconcileReport:
    removed: list[str] = field(default_factory=list)
    renamed: list[str] = field(default_factory=list)
    enabled: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    restart_pending: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "removed": self.removed,
            "renamed": self.renamed,
            "enabled": self.enabled,
            "conflicts": self.conflicts,
            "errors": self.errors,
            "restart_pending": self.restart_pending,
        }

    @property
    def changed(self) -> bool:
        return bool(self.removed or self.renamed or self.enabled)


def plan_reconcile(
    entries: list[dict[str, Any]],
    expected_uids: set[str],
) -> tuple[list[Action], ReconcileReport]:
    """Calcule le plan d'actions (pur, sans I/O).

    Args:
        entries: sortie de ``config/entity_registry/list``.
        expected_uids: uids Moli attendus (émis par generate_yaml + package
            statique). Seules ces entités sont renommées/réactivées.
    """
    actions: list[Action] = []
    report = ReconcileReport()

    by_entity_id: dict[str, dict[str, Any]] = {
        e.get("entity_id", ""): e for e in entries
    }
    # entity_ids déjà « réservés » par le plan (cible d'un rename ou libéré
    # par un remove) — évite deux renames vers la même cible.
    claimed: set[str] = set()
    freed: set[str] = set()

    moli = [
        e
        for e in entries
        if str(e.get("unique_id", "")).startswith("molini_")
        and e.get("platform") in _PLATFORMS
    ]

    # 1. Purge des uids legacy (toujours, même non bloquants — dette morte).
    for e in moli:
        uid = str(e.get("unique_id", ""))
        if uid in LEGACY_UIDS:
            eid = e["entity_id"]
            actions.append(Action("remove", eid, reason=f"legacy_uid:{uid}"))
            freed.add(eid)

    # 2. Renommage canonique + réactivation des entités attendues.
    for e in moli:
        uid = str(e.get("unique_id", ""))
        if uid in LEGACY_UIDS or uid not in expected_uids:
            continue
        eid = str(e.get("entity_id", ""))
        domain = eid.split(".", 1)[0]
        canon = f"{domain}.{uid}"

        if eid != canon:
            occupant = by_entity_id.get(canon)
            if occupant is not None and canon not in freed:
                occ_uid = str(occupant.get("unique_id", ""))
                # Le squatteur est-il déjà purgé (legacy) ? Sinon → conflit.
                report.conflicts.append(
                    f"{canon} occupé par uid={occ_uid} — rename de {eid} impossible"
                )
                continue
            if canon in claimed:
                report.conflicts.append(f"{canon} déjà réclamé — {eid} laissé tel quel")
                continue
            actions.append(Action("rename", eid, new_entity_id=canon))
            claimed.add(canon)

        if e.get("disabled_by") == "user":
            # Entrée désactivée héritée (ex. retrait 0.15.0) : réactiver.
            # HA n'instancie une entité disabled→enabled qu'au restart.
            actions.append(Action("enable", canon if eid != canon else eid))

    return actions, report


# ─── Exécution WebSocket ─────────────────────────────────────────────────────

async def _ws_registry_session(ws_url: str, token: str):
    """Ouvre une session WS HA authentifiée. Import paresseux de websockets
    (dépendance runtime uniquement — les tests unitaires n'en ont pas besoin)."""
    import websockets  # noqa: PLC0415

    ws = await websockets.connect(ws_url, open_timeout=15, close_timeout=5)
    msg = json.loads(await ws.recv())
    if msg.get("type") != "auth_required":
        await ws.close()
        raise RuntimeError(f"unexpected first message: {msg.get('type')}")
    await ws.send(json.dumps({"type": "auth", "access_token": token}))
    msg = json.loads(await ws.recv())
    if msg.get("type") != "auth_ok":
        await ws.close()
        raise RuntimeError("ws_auth_failed")
    return ws


async def _ws_cmd(ws, msg_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    await ws.send(json.dumps({"id": msg_id, **payload}))
    # Les events éventuels sont ignorés — on attend le result de NOTRE id.
    while True:
        msg = json.loads(await ws.recv())
        if msg.get("type") == "result" and msg.get("id") == msg_id:
            return msg


async def apply_reconcile(
    ws_url: str,
    token: str,
    expected_uids: set[str],
) -> dict[str, Any]:
    """Liste le registre, calcule le plan, l'exécute. Best-effort par action.

    Retourne le rapport sérialisable. Lève seulement si la session WS
    elle-même est impossible (auth/connexion) — l'appelant décide quoi faire.
    """
    ws = await _ws_registry_session(ws_url, token)
    report: ReconcileReport
    try:
        res = await _ws_cmd(ws, 1, {"type": "config/entity_registry/list"})
        entries = res.get("result") or []
        actions, report = plan_reconcile(entries, expected_uids)

        msg_id = 2
        for a in actions:
            try:
                if a.kind == "remove":
                    r = await _ws_cmd(
                        ws, msg_id,
                        {"type": "config/entity_registry/remove", "entity_id": a.entity_id},
                    )
                    if r.get("success"):
                        report.removed.append(f"{a.entity_id} ({a.reason})")
                    else:
                        report.errors.append(f"remove {a.entity_id}: {r.get('error')}")
                elif a.kind == "rename":
                    r = await _ws_cmd(
                        ws, msg_id,
                        {
                            "type": "config/entity_registry/update",
                            "entity_id": a.entity_id,
                            "new_entity_id": a.new_entity_id,
                        },
                    )
                    if r.get("success"):
                        report.renamed.append(f"{a.entity_id} -> {a.new_entity_id}")
                    else:
                        report.errors.append(f"rename {a.entity_id}: {r.get('error')}")
                elif a.kind == "enable":
                    r = await _ws_cmd(
                        ws, msg_id,
                        {
                            "type": "config/entity_registry/update",
                            "entity_id": a.entity_id,
                            "disabled_by": None,
                        },
                    )
                    if r.get("success"):
                        report.enabled.append(a.entity_id)
                        report.restart_pending = True
                    else:
                        report.errors.append(f"enable {a.entity_id}: {r.get('error')}")
            except Exception as e:  # noqa: BLE001 — best-effort par action
                report.errors.append(f"{a.kind} {a.entity_id}: {e}")
            msg_id += 1
    finally:
        try:
            await ws.close()
        except Exception:  # noqa: BLE001
            pass

    if report.changed or report.conflicts or report.errors:
        log.info("registry_reconcile: %s", report.as_dict())
    return report.as_dict()


def ws_url_from_ha_url(ha_url: str) -> str:
    """http://supervisor/core → ws://supervisor/core/websocket."""
    base = ha_url.rstrip("/")
    if base.startswith("https://"):
        return "wss://" + base[len("https://"):] + "/websocket"
    if base.startswith("http://"):
        return "ws://" + base[len("http://"):] + "/websocket"
    return base + "/websocket"
