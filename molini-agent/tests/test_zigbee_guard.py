"""Tests du garde-fou ZHA (0.16.1).

Politique testée :
- box en ZHA (ou both)  → ``install_addon zigbee2mqtt`` REFUSÉ,
  ``bootstrap_stack`` SKIP z2m (mais installe le reste) ;
- ``force_z2m: true``   → le garde-fou est outrepassé ;
- détection ``unknown`` → fail-open (comportement historique conservé) ;
- ``collect_bootstrap_state`` remonte ``zigbee_stack``.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from molini_agent.commands import execute_install_addon
from molini_agent.bootstrap import bootstrap_stack
from molini_agent.zigbee import combine_zigbee, detect_zigbee_stack, zigbee_stack_from_states


class _DummyConfig:
    pass


@pytest.fixture
def mock_supervisor():
    with patch("molini_agent.bootstrap.supervisor_client") as mock:
        mock.addons_list = AsyncMock(return_value=[])
        mock.addon_info = AsyncMock(return_value={})
        mock.addon_install = AsyncMock(return_value={})
        mock.addon_start = AsyncMock(return_value={})
        mock.addon_options = AsyncMock(return_value={})
        mock.store_addons_list = AsyncMock(return_value=[])
        mock.store_repositories_add = AsyncMock(return_value={})
        yield mock


@pytest.fixture
def mock_yaml_patch(tmp_path, monkeypatch):
    monkeypatch.setenv("HA_CONFIG_PATH", str(tmp_path / "configuration.yaml"))
    return tmp_path / "configuration.yaml"


# ─── combine / mapping ────────────────────────────────────────────────────────

def test_combine_zigbee_matrix():
    assert combine_zigbee(True, True) == "both"
    assert combine_zigbee(True, False) == "zha"
    assert combine_zigbee(True, None) == "zha"
    assert combine_zigbee(False, True) == "z2m"
    assert combine_zigbee(None, True) == "z2m"
    assert combine_zigbee(False, False) == "none"
    assert combine_zigbee(None, False) == "unknown"
    assert combine_zigbee(False, None) == "unknown"
    assert combine_zigbee(None, None) == "unknown"


def test_zigbee_stack_from_states():
    assert zigbee_stack_from_states(True, "started") == "both"
    assert zigbee_stack_from_states(True, "not_installed") == "zha"
    assert zigbee_stack_from_states(False, "stopped") == "z2m"
    assert zigbee_stack_from_states(False, "not_installed") == "none"
    assert zigbee_stack_from_states(None, "unknown") == "unknown"
    assert zigbee_stack_from_states(None, "not_installed") == "unknown"


# ─── detect_zigbee_stack ──────────────────────────────────────────────────────

class _FakeHA:
    def __init__(self, entries):
        self._entries = entries

    async def config_entries(self):
        return self._entries

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_detect_zha_from_config_entries():
    with patch("molini_agent.zigbee.supervisor_client") as sup:
        sup.addons_list = AsyncMock(return_value=[])
        ha = _FakeHA([{"domain": "zha", "state": "loaded"}, {"domain": "sun"}])
        assert await detect_zigbee_stack(ha) == "zha"


@pytest.mark.asyncio
async def test_detect_z2m_from_addons():
    with patch("molini_agent.zigbee.supervisor_client") as sup:
        sup.addons_list = AsyncMock(return_value=[{"slug": "45df7312_zigbee2mqtt"}])
        ha = _FakeHA([{"domain": "sun"}])
        assert await detect_zigbee_stack(ha) == "z2m"


@pytest.mark.asyncio
async def test_detect_unknown_when_probes_unavailable():
    with patch("molini_agent.zigbee.supervisor_client") as sup:
        sup.addons_list = AsyncMock(side_effect=RuntimeError("supervisor down"))
        assert await detect_zigbee_stack(None) == "unknown"


# ─── install_addon guard ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_install_z2m_blocked_on_zha_box():
    with patch(
        "molini_agent.commands.detect_zigbee_stack", AsyncMock(return_value="zha")
    ):
        with pytest.raises(RuntimeError, match="zha_detected_conflict"):
            await execute_install_addon({"name": "zigbee2mqtt", "start": True})


@pytest.mark.asyncio
async def test_install_z2m_blocked_on_both():
    with patch(
        "molini_agent.commands.detect_zigbee_stack", AsyncMock(return_value="both")
    ):
        with pytest.raises(RuntimeError, match="zha_detected_conflict"):
            await execute_install_addon({"name": "zigbee2mqtt"})


@pytest.mark.asyncio
async def test_install_z2m_force_bypasses_guard():
    with patch(
        "molini_agent.commands.detect_zigbee_stack", AsyncMock(return_value="zha")
    ) as detect, patch(
        "molini_agent.commands.install_or_start_addon",
        AsyncMock(return_value={"name": "zigbee2mqtt", "status": "installed"}),
    ) as install:
        result = await execute_install_addon(
            {"name": "zigbee2mqtt", "force_z2m": True}
        )
        assert result["status"] == "installed"
        detect.assert_not_called()
        install.assert_awaited_once()


@pytest.mark.asyncio
async def test_install_z2m_allowed_when_unknown():
    """Fail-open : une sonde KO ne bloque pas une install saine."""
    with patch(
        "molini_agent.commands.detect_zigbee_stack", AsyncMock(return_value="unknown")
    ), patch(
        "molini_agent.commands.install_or_start_addon",
        AsyncMock(return_value={"name": "zigbee2mqtt", "status": "installed"}),
    ):
        result = await execute_install_addon({"name": "zigbee2mqtt"})
        assert result["status"] == "installed"


@pytest.mark.asyncio
async def test_install_other_addons_never_probe_zigbee():
    with patch(
        "molini_agent.commands.detect_zigbee_stack", AsyncMock(return_value="zha")
    ) as detect, patch(
        "molini_agent.commands.install_or_start_addon",
        AsyncMock(return_value={"name": "mosquitto", "status": "installed"}),
    ):
        await execute_install_addon({"name": "mosquitto"})
        detect.assert_not_called()


# ─── bootstrap_stack guard ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bootstrap_skips_z2m_on_zha_box(mock_supervisor, mock_yaml_patch):
    with patch(
        "molini_agent.bootstrap.detect_zigbee_stack", AsyncMock(return_value="zha")
    ), patch(
        "molini_agent.bootstrap.install_or_start_addon",
        AsyncMock(
            side_effect=lambda name, **kw: {"name": name, "status": "installed"}
        ),
    ) as install:
        report = await bootstrap_stack(_DummyConfig(), payload={})
        installed = [c.args[0] if c.args else c.kwargs.get("name") for c in install.await_args_list]
        assert "zigbee2mqtt" not in installed
        assert "mosquitto" in installed and "cloudflared" in installed
        skipped = [a for a in report["actions"] if a.get("reason") == "zha_detected"]
        assert len(skipped) == 1 and skipped[0]["name"] == "zigbee2mqtt"


@pytest.mark.asyncio
async def test_bootstrap_installs_z2m_when_no_zha(mock_supervisor, mock_yaml_patch):
    with patch(
        "molini_agent.bootstrap.detect_zigbee_stack", AsyncMock(return_value="none")
    ), patch(
        "molini_agent.bootstrap.install_or_start_addon",
        AsyncMock(
            side_effect=lambda name, **kw: {"name": name, "status": "installed"}
        ),
    ) as install:
        await bootstrap_stack(_DummyConfig(), payload={})
        installed = [c.args[0] if c.args else c.kwargs.get("name") for c in install.await_args_list]
        assert "zigbee2mqtt" in installed


@pytest.mark.asyncio
async def test_bootstrap_force_z2m_bypasses_guard(mock_supervisor, mock_yaml_patch):
    with patch(
        "molini_agent.bootstrap.detect_zigbee_stack", AsyncMock(return_value="zha")
    ) as detect, patch(
        "molini_agent.bootstrap.install_or_start_addon",
        AsyncMock(
            side_effect=lambda name, **kw: {"name": name, "status": "installed"}
        ),
    ) as install:
        await bootstrap_stack(_DummyConfig(), payload={"force_z2m": True})
        installed = [c.args[0] if c.args else c.kwargs.get("name") for c in install.await_args_list]
        assert "zigbee2mqtt" in installed
        detect.assert_not_called()
