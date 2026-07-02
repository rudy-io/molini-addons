"""Client HTTP vers Home Assistant Core.

Sous HAOS, on tape ``http://supervisor/core/api/*`` avec ``SUPERVISOR_TOKEN``.
Sous Debian autonome, on tape ``http://localhost:8123/api/*`` avec un
Long-Lived Access Token. Les deux modes utilisent la même interface — c'est
``run.sh`` qui pose la bonne valeur dans ``HA_URL`` / ``HA_TOKEN``.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

log = logging.getLogger("molini_agent.ha_client")


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

    async def config_entries(self) -> list[dict[str, Any]] | None:
        """Config entries HA Core (``GET /api/config/config_entries/entry``).

        Sert au garde-fou Zigbee (détection ZHA). ``None`` si l'API est
        indisponible — best-effort, ne lève jamais.
        """
        try:
            r = await self._client.get("/api/config/config_entries/entry")
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, list) else None
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

    async def sensor_max_over(
        self, entity_ids: list[str], days: int = 14
    ) -> dict[str, float]:
        """Max observé (W) par capteur sur les `days` derniers jours (best-effort).
        Recorder = 14 j chez Moli, donc fenêtre <= 14 j utile. Renvoie {} sur erreur."""
        if not entity_ids:
            return {}
        start = datetime.now(timezone.utc) - timedelta(days=days)
        url = (
            "/api/history/period/"
            + start.isoformat()
            + "?filter_entity_id="
            + ",".join(entity_ids)
            + "&minimal_response&significant_changes_only"
        )
        try:
            r = await self._client.get(url)
            if r.status_code != 200:
                log.warning(
                    "sensor_max_over: HA history returned %s", r.status_code
                )
                return {}
            payload = r.json()
        except Exception as exc:  # noqa: BLE001
            log.warning("sensor_max_over: request failed: %s", exc)
            return {}
        result: dict[str, float] = {}
        for series in payload:
            if not isinstance(series, list) or not series:
                continue
            pts = series
            eid = pts[0].get("entity_id")
            if not eid:
                continue
            values: list[float] = []
            for p in pts:
                try:
                    values.append(float(p["state"]))
                except (KeyError, TypeError, ValueError):
                    pass
            if values:
                result[eid] = max(values)
        return result
