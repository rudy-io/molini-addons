"""Tests de la MAJ à distance de l'agent Moli (store_reload + self-update).

Le but : pouvoir mettre à jour le plugin depuis le central, sans toucher la box.
On mocke ``supervisor_client`` — la logique testée est dans ``commands``.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from molini_agent import commands


def _patch(monkeypatch, name, mock):
    monkeypatch.setattr(commands.supervisor_client, name, mock, raising=False)


@pytest.mark.asyncio
async def test_self_update_reloads_store_then_updates_when_available(monkeypatch):
    reload = AsyncMock(return_value={})
    info = AsyncMock(
        return_value={
            "slug": "abc1234_molini_agent",
            "version": "0.8.2",
            "version_latest": "0.8.3",
            "update_available": True,
        }
    )
    update = AsyncMock(return_value={})
    _patch(monkeypatch, "store_reload", reload)
    _patch(monkeypatch, "self_info", info)
    _patch(monkeypatch, "addon_update", update)

    res = await commands.execute_agent_self_update()

    # le store est rafraîchi AVANT de regarder la version (sinon on rate la MAJ)
    reload.assert_awaited_once()
    update.assert_awaited_once_with("abc1234_molini_agent")
    assert res["updating"] is True
    assert res["from"] == "0.8.2"
    assert res["to"] == "0.8.3"


@pytest.mark.asyncio
async def test_self_update_skips_when_already_latest(monkeypatch):
    _patch(monkeypatch, "store_reload", AsyncMock(return_value={}))
    _patch(
        monkeypatch,
        "self_info",
        AsyncMock(
            return_value={
                "slug": "x_molini_agent",
                "version": "0.8.3",
                "version_latest": "0.8.3",
                "update_available": False,
            }
        ),
    )
    update = AsyncMock()
    _patch(monkeypatch, "addon_update", update)

    res = await commands.execute_agent_self_update()

    update.assert_not_called()
    assert res["updated"] is False
    assert res["version"] == "0.8.3"


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
