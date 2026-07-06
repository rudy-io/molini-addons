"""Moli AI — agent de conversation HA qui proxifie Assist vers le cerveau central.

L'occupant tape dans Assist → cette intégration POST le message à
`<central_url>/api/agent/converse` (Bearer agent_token) → Moli AI répond.

Auto-config : l'add-on Moli dépose `moli_config.json` (central_url + token) à côté
de ce fichier et un marqueur `moli_ai:` dans configuration.yaml. À l'init, on crée
l'entrée via un import flow → zéro manip. Fallback : ajout manuel via l'UI.
"""
from __future__ import annotations

import json
import os

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

DOMAIN = "moli_ai"
PLATFORMS = [Platform.CONVERSATION]
_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "moli_config.json")


def _read_config_file() -> dict:
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    # Si déjà configuré, rien à faire.
    if hass.config_entries.async_entries(DOMAIN):
        return True
    data = await hass.async_add_executor_job(_read_config_file)
    if data.get("token") and data.get("central_url"):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=data
            )
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    cfg = dict(entry.data)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = cfg
    # Vues proxy pour le panneau chat (token gardé côté serveur, cf. http.py).
    from .http import register_views

    register_views(hass, cfg.get("central_url", ""), cfg.get("token", ""))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return ok
