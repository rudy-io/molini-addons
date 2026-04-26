"""Liste les services tournant à côté de l'agent.

Sous HAOS : on interroge le superviseur pour la liste des add-ons (chacun
correspond à un service que l'utilisateur voit dans Settings → Add-ons).
On retourne le même schéma simplifié que ``docker_status.collect_services``
côté Debian autonome, pour que le central n'ait pas à différencier.
"""
import logging
from typing import Any

from . import supervisor_client
from .runtime import is_haos

log = logging.getLogger("molini_agent.service_status")


async def collect_services() -> list[dict[str, Any]]:
    if not is_haos():
        # En hors-HAOS, on n'a pas de docker socket monté dans l'add-on, et
        # le central appellera de toute façon le mode `debian` via l'autre
        # version du package (dossier ``agent/``).
        return []

    try:
        addons = await supervisor_client.addons_list()
    except Exception as e:  # pragma: no cover
        log.warning("supervisor addons list failed: %s", e)
        return []

    services: list[dict[str, Any]] = []
    for a in addons:
        slug = a.get("slug") or "?"
        services.append(
            {
                "name": a.get("name") or slug,
                "slug": slug,
                "image": a.get("logo") or "",
                "state": a.get("state", "unknown"),  # 'started' / 'stopped' / 'error'
                "status": a.get("version", ""),
                "update_available": a.get("update_available", False),
            }
        )

    services.sort(key=lambda s: (s["state"] != "started", s["name"]))
    return services
