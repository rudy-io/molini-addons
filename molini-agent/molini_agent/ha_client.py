"""Client HTTP vers Home Assistant Core.

Sous HAOS, on tape ``http://supervisor/core/api/*`` avec ``SUPERVISOR_TOKEN``.
Sous Debian autonome, on tape ``http://localhost:8123/api/*`` avec un
Long-Lived Access Token. Les deux modes utilisent la même interface — c'est
``run.sh`` qui pose la bonne valeur dans ``HA_URL`` / ``HA_TOKEN``.
"""
from typing import Any, Optional

import httpx


class HAClient:
    def __init__(self, base_url: str, token: str):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def config(self) -> dict[str, Any] | None:
        try:
            r = await self._client.get("/api/config")
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError:
            return None

    async def states(self) -> list[dict[str, Any]]:
        try:
            r = await self._client.get("/api/states")
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError:
            return []

    async def get_state(self, entity_id: str) -> Optional[dict[str, Any]]:
        try:
            r = await self._client.get(f"/api/states/{entity_id}")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError:
            return None

    async def call_service(self, domain: str, service: str, data: dict[str, Any]) -> bool:
        """Appelle un service HA Core (POST /api/services/<domain>/<service>).

        Best-effort : True si 2xx, False sinon — ne lève jamais. Utilisé entre
        autres pour ``update.install`` (MAJ de l'add-on déclenchée par HA Core,
        seul acteur autorisé à updater un add-on — l'add-on ne peut pas le faire
        lui-même côté superviseur).
        """
        try:
            r = await self._client.post(f"/api/services/{domain}/{service}", json=data)
            r.raise_for_status()
            return True
        except httpx.HTTPError:
            return False
