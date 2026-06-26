"""Entité de conversation Moli AI — proxy Assist → cerveau central."""
from __future__ import annotations

import aiohttp
from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    cfg = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MoliConversationAgent(entry, cfg)])


class MoliConversationAgent(conversation.ConversationEntity):
    """Agent de conversation qui transmet le message au central Moli AI."""

    _attr_has_entity_name = True
    _attr_name = "Moli AI"

    def __init__(self, entry: ConfigEntry, cfg: dict) -> None:
        self._url = str(cfg["central_url"]).rstrip("/") + "/api/agent/converse"
        self._token = cfg["token"]
        self._attr_unique_id = entry.entry_id

    @property
    def supported_languages(self) -> list[str]:
        return ["fr", "en"]

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        text = "Je n'arrive pas à joindre Moli pour l'instant."
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._url,
                    headers={"Authorization": f"Bearer {self._token}"},
                    json={"message": user_input.text},
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    data = await resp.json()
                    text = data.get("response") or "Désolé, je n'ai pas pu répondre."
        except Exception:  # noqa: BLE001 — dégrade proprement côté Assist
            pass

        response = intent.IntentResponse(language=user_input.language)
        response.async_set_speech(text)
        return conversation.ConversationResult(
            response=response, conversation_id=user_input.conversation_id
        )
