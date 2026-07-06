"""Vues HTTP internes — proxy authentifié navigateur HA → cerveau central.

La carte chat (``moli-chat-card.js``) tourne dans le navigateur de l'occupant.
On NE veut PAS exposer l'``agent_token`` au navigateur (quiconque a accès au
dashboard le lirait). Ces vues, protégées par l'auth de SESSION HA
(``requires_auth = True``), relaient vers le central en gardant le token côté
serveur. Le navigateur parle à HA (déjà authentifié) ; HA parle au central.
"""
from __future__ import annotations

import logging

import aiohttp
from homeassistant.components.http import HomeAssistantView

log = logging.getLogger("moli_ai.http")

_TIMEOUT = aiohttp.ClientTimeout(total=60)


class _MoliProxyBase(HomeAssistantView):
    """Base : relaie une requête vers le central avec le Bearer agent_token."""

    requires_auth = True

    def __init__(self, central_url: str, token: str) -> None:
        self._central = str(central_url).rstrip("/")
        self._token = token

    async def _proxy(self, method: str, path: str, payload: dict | None = None):
        url = f"{self._central}{path}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    headers={"Authorization": f"Bearer {self._token}"},
                    json=payload,
                    timeout=_TIMEOUT,
                ) as resp:
                    data = await resp.json()
                    return self.json(data, status_code=resp.status)
        except Exception as e:  # noqa: BLE001 — dégrade proprement côté carte
            log.warning("proxy %s %s: %s", method, path, e)
            return self.json({"error": "central_injoignable"}, status_code=502)


class MoliConverseView(_MoliProxyBase):
    url = "/api/moli_ai/converse"
    name = "api:moli_ai:converse"

    async def post(self, request):
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            body = {}
        return await self._proxy(
            "POST", "/api/agent/converse", {"message": str(body.get("message", ""))}
        )


class MoliActionView(_MoliProxyBase):
    url = "/api/moli_ai/action/{action_id}"
    name = "api:moli_ai:action"

    async def post(self, request, action_id):
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            body = {}
        return await self._proxy(
            "POST", f"/api/agent/action/{action_id}", {"op": str(body.get("op", ""))}
        )


class MoliActionsView(_MoliProxyBase):
    url = "/api/moli_ai/actions"
    name = "api:moli_ai:actions"

    async def get(self, request):
        return await self._proxy("GET", "/api/agent/actions")


def register_views(hass, central_url: str, token: str) -> None:
    """Enregistre les 3 vues proxy (idempotent via un flag dans hass.data)."""
    from . import DOMAIN

    store = hass.data.setdefault(DOMAIN, {})
    if store.get("_views_registered"):
        return
    hass.http.register_view(MoliConverseView(central_url, token))
    hass.http.register_view(MoliActionView(central_url, token))
    hass.http.register_view(MoliActionsView(central_url, token))
    store["_views_registered"] = True
    log.info("Vues proxy Moli AI enregistrées (central=%s)", central_url)
