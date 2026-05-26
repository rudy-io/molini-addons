"""Client HTTP vers le superviseur Home Assistant.

Disponible uniquement en runtime ``haos`` — utilisé par ``commands.py`` pour
les actions qui touchent à la stack (restart Core, update add-ons,
install/start/stop d'autres add-ons type cloudflared).

Doc API : https://developers.home-assistant.io/docs/api/supervisor/endpoints
"""
from typing import Any, Optional

import httpx

from .runtime import supervisor_token, supervisor_url


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=supervisor_url(),
        headers={"Authorization": f"Bearer {supervisor_token()}"},
        timeout=60.0,
    )


async def _post(path: str, json: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    async with _client() as c:
        r = await c.post(path, json=json or {})
        if r.status_code >= 400:
            raise RuntimeError(
                f"supervisor POST {path} → {r.status_code}: {r.text[:200]}"
            )
        try:
            return r.json()
        except ValueError:
            return {"raw": r.text[:200]}


async def _get(path: str) -> dict[str, Any]:
    async with _client() as c:
        r = await c.get(path)
        if r.status_code >= 400:
            raise RuntimeError(
                f"supervisor GET {path} → {r.status_code}: {r.text[:200]}"
            )
        return r.json()


# ─── Endpoints helpers ────────────────────────────────────────────────────────

async def core_restart() -> dict[str, Any]:
    """Redémarre Home Assistant Core (équivalent de notre ancien ha_restart)."""
    return await _post("/core/restart")


async def addons_list() -> list[dict[str, Any]]:
    """Liste les add-ons installés (utilisé pour heartbeat services + stack_update)."""
    data = await _get("/addons")
    return (data.get("data") or {}).get("addons") or []


async def addon_info(slug: str) -> dict[str, Any]:
    return (await _get(f"/addons/{slug}/info")).get("data") or {}


async def addon_install(slug: str) -> dict[str, Any]:
    return await _post(f"/addons/{slug}/install")


async def addon_uninstall(slug: str) -> dict[str, Any]:
    return await _post(f"/addons/{slug}/uninstall")


async def addon_start(slug: str) -> dict[str, Any]:
    return await _post(f"/addons/{slug}/start")


async def addon_stop(slug: str) -> dict[str, Any]:
    return await _post(f"/addons/{slug}/stop")


async def addon_restart(slug: str) -> dict[str, Any]:
    return await _post(f"/addons/{slug}/restart")


async def addon_update(slug: str) -> dict[str, Any]:
    return await _post(f"/addons/{slug}/update")


async def addon_options(slug: str, options: dict[str, Any]) -> dict[str, Any]:
    """Pose la config d'un add-on (équivalent du formulaire UI Configuration)."""
    return await _post(f"/addons/{slug}/options", json={"options": options})


async def store_repositories_add(url: str) -> dict[str, Any]:
    """Ajoute un repo add-on dans le store HA."""
    return await _post("/store/repositories", json={"repository": url})


async def store_addons_list() -> list[dict[str, Any]]:
    """Liste les add-ons exposés par le store (catalogue, pas installés).

    Utilisé pour résoudre dynamiquement le slug d'un add-on présent dans un
    repo communautaire (ex. cloudflared de brenner-tobias) après ajout du
    repo via ``store_repositories_add``.
    """
    data = await _get("/store/addons")
    return (data.get("data") or {}).get("addons") or []


async def store_info() -> dict[str, Any]:
    """Renvoie le contenu complet du store (addons + repositories)."""
    return (await _get("/store")).get("data") or {}
