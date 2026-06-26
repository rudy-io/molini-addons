"""Config flow Moli AI — import auto (depuis l'add-on) ou saisie manuelle."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from . import DOMAIN


class MoliAiConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_import(self, data: dict) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Moli AI", data=data)

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Moli AI", data=user_input)
        schema = vol.Schema(
            {
                vol.Required("central_url", default="https://moli.energy"): str,
                vol.Required("token"): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)
