"""Tests de la MAJ à distance de l'agent Moli.

Le superviseur interdit à un add-on de s'updater en direct → on passe par le
service HA Core ``update.install``. On mocke ``supervisor_client`` (store_reload,
self_info) et ``HAClient`` (states, call_service).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from molini_agent import commands


def _patch(monkeypatch, name, mock):
    monkeypatch.setattr(commands.supervisor_client, name, mock, raising=False)


def _cfg():
    return SimpleNamespace(ha_url="http://supervisor/core", ha_token="tok")


def _fake_ha(monkeypatch, states, call_service):
    fake = SimpleNamespace(
        states=AsyncMock(return_value=states),
        call_service=call_service,
        close=AsyncMock(),
    )
    monkeypatch.setattr(commands, "HAClient", lambda *a, **k: fake)
    return fake


@pytest.mark.asyncio
async def test_self_update_calls_update_install_when_available(monkeypatch):
    # La décision se base sur la vue FRAÎCHE du superviseur (self_info), pas sur
    # l'attribut latest_version de l'entité update.* (qui peut traîner).
    _patch(monkeypatch, "store_reload", AsyncMock(return_value={}))
    _patch(
        monkeypatch,
        "self_info",
        AsyncMock(
            return_value={
                "name": "Moli Agent",
                "version": "0.8.4",
                "version_latest": "0.8.5",
                "update_available": True,
            }
        ),
    )
    call = AsyncMock(return_value=True)
    states = [
        {"entity_id": "update.autre_chose", "attributes": {"title": "Autre"}},
        {"entity_id": "update.moli_agent_update", "attributes": {"title": "Moli Agent"}},
    ]
    _fake_ha(monkeypatch, states, call)

    res = await commands.execute_agent_self_update(_cfg())

    commands.supervisor_client.store_reload.assert_awaited()
    call.assert_awaited_once_with("update", "install", {"entity_id": "update.moli_agent_update"})
    assert res["updating"] is True
    assert res["from"] == "0.8.4"
    assert res["to"] == "0.8.5"


@pytest.mark.asyncio
async def test_self_update_skips_when_supervisor_says_latest(monkeypatch):
    monkeypatch.setattr(commands.asyncio, "sleep", AsyncMock())  # pas d'attente réelle
    _patch(monkeypatch, "store_reload", AsyncMock(return_value={}))
    _patch(
        monkeypatch,
        "self_info",
        AsyncMock(return_value={"name": "Moli Agent", "version": "0.8.5", "update_available": False}),
    )
    call = AsyncMock()
    _fake_ha(monkeypatch, [], call)

    res = await commands.execute_agent_self_update(_cfg())

    call.assert_not_called()
    assert res["updated"] is False
    assert res["version"] == "0.8.5"


@pytest.mark.asyncio
async def test_enable_auto_update_sets_flag_on_self(monkeypatch):
    _patch(monkeypatch, "self_info", AsyncMock(return_value={"slug": "y_molini_agent"}))
    setau = AsyncMock(return_value={})
    _patch(monkeypatch, "addon_set_auto_update", setau)

    res = await commands.execute_enable_auto_update()

    setau.assert_awaited_once_with("y_molini_agent", True)
    assert res["auto_update"] is True


def test_self_update_commands_registered():
    assert "agent_self_update" in commands.HANDLERS
    assert "enable_auto_update" in commands.HANDLERS
