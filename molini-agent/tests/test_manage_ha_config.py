"""Option ``manage_ha_config`` : un HA configuré par son propriétaire reste intact.

Le patch de démarrage écrase des valeurs existantes (``recorder``,
``frontend.themes``), d'où cette option pour les installations qu'on n'a pas
montées nous-mêmes. Le parc existant doit garder son comportement par défaut.
"""
from __future__ import annotations

import pytest

from molini_agent import commands, main
from molini_agent.config import Config


def _env(monkeypatch: pytest.MonkeyPatch, **extra: str) -> None:
    monkeypatch.setenv("CENTRAL_URL", "https://central.test")
    monkeypatch.setenv("CLIENT_TOKEN", "token")
    monkeypatch.setenv("HA_URL", "http://ha.test")
    monkeypatch.setenv("HA_TOKEN", "ha-token")
    monkeypatch.delenv("MANAGE_HA_CONFIG", raising=False)
    for name, value in extra.items():
        monkeypatch.setenv(name, value)


def _cfg(monkeypatch: pytest.MonkeyPatch, manage: str) -> Config:
    _env(monkeypatch, MANAGE_HA_CONFIG=manage)
    return Config.from_env()


def test_absent_option_keeps_fleet_behaviour(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch)
    assert Config.from_env().manage_ha_config is True


@pytest.mark.parametrize(
    ("value", "expected"),
    [("true", True), ("null", True), ("", True), ("false", False), ("FALSE", False)],
)
def test_only_explicit_false_disables(
    monkeypatch: pytest.MonkeyPatch, value: str, expected: bool
) -> None:
    assert _cfg(monkeypatch, value).manage_ha_config is expected


def _spy_boot_patches(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []

    def fake_ensure() -> dict:
        calls.append("ensure_moli_ha_config")
        return {"changed": False}

    def fake_patch(_patch: dict) -> dict:
        calls.append("patch_ha_config")
        return {"changed": False}

    monkeypatch.setattr(main, "is_haos", lambda: True)
    monkeypatch.setattr(main, "ensure_moli_ha_config", fake_ensure)
    monkeypatch.setattr("molini_agent.bootstrap.patch_ha_config", fake_patch)
    return calls


def test_boot_leaves_config_alone_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _spy_boot_patches(monkeypatch)
    main.apply_moli_ha_config(_cfg(monkeypatch, "false"))
    assert calls == []


def test_boot_still_patches_managed_box(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _spy_boot_patches(monkeypatch)
    main.apply_moli_ha_config(_cfg(monkeypatch, "true"))
    assert calls == ["ensure_moli_ha_config", "patch_ha_config"]


def _spy_commands(monkeypatch: pytest.MonkeyPatch, cmd_type: str) -> tuple[list, list]:
    executed: list[str] = []
    reports: list[tuple] = []

    async def fake_handler(_cfg, _payload) -> dict:
        executed.append(cmd_type)
        return {"ok": True}

    async def fake_report(_cfg, cmd_id, status, **kwargs) -> None:
        reports.append((cmd_id, status, kwargs))

    monkeypatch.setitem(commands.HANDLERS, cmd_type, fake_handler)
    monkeypatch.setattr(commands, "report_result", fake_report)
    return executed, reports


@pytest.mark.asyncio
@pytest.mark.parametrize("cmd_type", ["bootstrap_stack", "ensure_moli_config"])
async def test_mass_config_commands_refused_when_disabled(
    monkeypatch: pytest.MonkeyPatch, cmd_type: str
) -> None:
    executed, reports = _spy_commands(monkeypatch, cmd_type)
    await commands.execute_one(
        _cfg(monkeypatch, "false"), {"id": "c1", "type": cmd_type, "payload": None}
    )
    assert executed == []
    assert reports[0][1] == "failed"
    assert "manage_ha_config" in reports[0][2]["error"]


@pytest.mark.asyncio
@pytest.mark.parametrize("cmd_type", ["patch_ha_config", "tunnel_install", "backup_now"])
async def test_explicit_commands_still_run_when_disabled(
    monkeypatch: pytest.MonkeyPatch, cmd_type: str
) -> None:
    executed, reports = _spy_commands(monkeypatch, cmd_type)
    await commands.execute_one(
        _cfg(monkeypatch, "false"), {"id": "c2", "type": cmd_type, "payload": None}
    )
    assert executed == [cmd_type]
    assert reports[-1][1] == "done"


@pytest.mark.asyncio
async def test_mass_config_command_still_runs_on_managed_box(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed, reports = _spy_commands(monkeypatch, "bootstrap_stack")
    await commands.execute_one(
        _cfg(monkeypatch, "true"), {"id": "c3", "type": "bootstrap_stack", "payload": None}
    )
    assert executed == ["bootstrap_stack"]
    assert reports[-1][1] == "done"
