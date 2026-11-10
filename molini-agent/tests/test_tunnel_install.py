"""``tunnel_install`` sur une box où l'add-on cloudflared n'est pas prêt.

Deux échecs vus sur la première installation hors famille : l'add-on absent
n'était jamais trouvé, et le jeton était refusé par le Supervisor (schéma
incomplet) sans que la commande échoue. L'add-on démarrait alors sans
configuration et s'arrêtait aussitôt.
"""
from __future__ import annotations

from typing import Any

import pytest

from molini_agent import commands, supervisor_client

SLUG = "9074a9fa_cloudflared"
TOKEN = "jeton-de-tunnel-suffisamment-long"
PAYLOAD = {"token": TOKEN, "subdomain": "abc"}
DEFAULT_OPTIONS = {"external_hostname": "", "additional_hosts": []}


class FakeSupervisor:
    """Le Supervisor vu de l'agent, avec la validation de schéma du vrai."""

    def __init__(self, installed: bool, state: str = "stopped", repo_added: bool = False):
        self.installed = installed
        self.state = state
        self.repo_added = repo_added
        self.options: dict[str, Any] = dict(DEFAULT_OPTIONS)
        self.refuse_options = False
        self.events: list[str] = []

    async def addons_list(self) -> list[dict[str, Any]]:
        return [{"slug": SLUG, "name": "Cloudflared", "state": self.state}] if self.installed else []

    async def store_addons_list(self) -> list[dict[str, Any]]:
        return [{"slug": SLUG, "name": "Cloudflared"}] if self.repo_added else []

    async def store_repositories_add(self, _url: str) -> dict[str, Any]:
        self.repo_added = True
        return {}

    async def addon_info(self, _slug: str) -> dict[str, Any]:
        if not self.installed:
            return {}
        return {"version": "7.0.21", "state": self.state, "options": dict(self.options)}

    async def addon_install(self, _slug: str) -> dict[str, Any]:
        self.installed = True
        self.events.append("install")
        return {}

    async def addon_options(self, _slug: str, options: dict[str, Any]) -> dict[str, Any]:
        if self.refuse_options or "additional_hosts" not in options:
            raise RuntimeError("Missing option 'additional_hosts'")
        self.options = options
        self.events.append("options")
        return {}

    async def addon_start(self, _slug: str) -> dict[str, Any]:
        self.state = "started"
        self.events.append("start")
        return {}

    async def addon_restart(self, _slug: str) -> dict[str, Any]:
        self.events.append("restart")
        return {}


def _install(monkeypatch: pytest.MonkeyPatch, fake: FakeSupervisor) -> FakeSupervisor:
    for name in (
        "addons_list",
        "store_addons_list",
        "store_repositories_add",
        "addon_info",
        "addon_install",
        "addon_options",
        "addon_start",
        "addon_restart",
    ):
        monkeypatch.setattr(supervisor_client, name, getattr(fake, name))
    return fake


@pytest.mark.asyncio
async def test_absent_addon_is_installed_configured_then_started(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _install(monkeypatch, FakeSupervisor(installed=False))

    result = await commands.execute_tunnel_install(PAYLOAD)

    assert fake.events == ["install", "options", "start"]
    assert fake.options["tunnel_token"] == TOKEN
    assert result["slug"] == SLUG


@pytest.mark.asyncio
async def test_token_is_accepted_by_the_addon_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _install(monkeypatch, FakeSupervisor(installed=True))

    await commands.execute_tunnel_install(PAYLOAD)

    assert fake.options["tunnel_token"] == TOKEN
    assert fake.events == ["options", "start"]


@pytest.mark.asyncio
async def test_existing_options_are_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeSupervisor(installed=True)
    fake.options = {"external_hostname": "", "additional_hosts": [{"hostname": "a", "service": "b"}]}
    _install(monkeypatch, fake)

    await commands.execute_tunnel_install(PAYLOAD)

    assert fake.options["additional_hosts"] == [{"hostname": "a", "service": "b"}]
    assert fake.options["tunnel_token"] == TOKEN


@pytest.mark.asyncio
async def test_refused_token_fails_the_command_without_starting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeSupervisor(installed=True)
    fake.refuse_options = True
    _install(monkeypatch, fake)

    with pytest.raises(RuntimeError, match="additional_hosts"):
        await commands.execute_tunnel_install(PAYLOAD)

    assert "start" not in fake.events


@pytest.mark.asyncio
async def test_running_addon_is_restarted_to_load_the_new_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _install(monkeypatch, FakeSupervisor(installed=True, state="started"))

    await commands.execute_tunnel_install(PAYLOAD)

    assert fake.events == ["options", "restart"]
