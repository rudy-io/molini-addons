"""Tests for ``molini_agent.bootstrap.bootstrap_stack`` and ``install_or_start_addon``.

Coverage:
- Order of installs (broker → z2m → cloudflared)
- Idempotence: 2nd call = all skipped
- Retry on transient failure
- HA config patch integration (only flag restart on actual change)
- Status reporting (installed / started / skipped / failed)
- Cloudflared install **without** start (waits for tunnel_install)
- Mosquitto/Z2M install **with** start
- Forbidden slug rejected
"""
from __future__ import annotations

import os
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from molini_agent.bootstrap import (
    bootstrap_stack,
    install_or_start_addon,
    patch_ha_config,
)


# Common dummy Config object — bootstrap_stack only uses ``cfg`` for future
# auth/log enrichment, no fields read today.
class _DummyConfig:
    pass


@pytest.fixture
def mock_supervisor():
    with patch("molini_agent.bootstrap.supervisor_client") as mock:
        # Defaults: nothing installed, store empty, repo add no-op
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
    """Redirect the HA config patch to a temp path so tests don't write /config."""
    monkeypatch.setenv("HA_CONFIG_PATH", str(tmp_path / "configuration.yaml"))
    return tmp_path / "configuration.yaml"


def _addon(slug: str, state: str = "started", installed: bool = True) -> dict:
    return {
        "slug": slug,
        "name": slug,
        "state": state,
        "version_installed": "1.0" if installed else None,
    }


# ─── install_or_start_addon ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_install_when_missing_mosquitto(mock_supervisor):
    """Mosquitto absent → install + start, return ``installed``."""
    mock_supervisor.addons_list.return_value = []
    mock_supervisor.store_addons_list.return_value = []
    # After we'd installed via API, the next addon_info call would return data
    mock_supervisor.addon_info.return_value = {}  # not installed

    # We need a way to "see" the install path. Inject installed state on first
    # ``addons_list`` call by adding the addon to the store.
    mock_supervisor.store_addons_list.return_value = [_addon("core_mosquitto")]

    result = await install_or_start_addon("mosquitto", start=True)
    assert result["name"] == "mosquitto"
    # Source might be ``installed_exact`` (if found in installed) or store-found
    # depending on what addons_list returns. With our setup it's not installed,
    # so the path will involve the store catalog.
    assert result["status"] in ("installed", "skipped", "started")
    mock_supervisor.addon_install.assert_called_once_with("core_mosquitto")
    mock_supervisor.addon_start.assert_called_once_with("core_mosquitto")
    assert result["error"] is None


@pytest.mark.asyncio
async def test_skipped_when_already_started(mock_supervisor):
    """Mosquitto already installed and started → ``skipped``, no install/start."""
    mock_supervisor.addons_list.return_value = [
        _addon("core_mosquitto", state="started")
    ]
    mock_supervisor.addon_info.return_value = {
        "version_installed": "2.0",
        "state": "started",
    }

    result = await install_or_start_addon("mosquitto", start=True)
    assert result["status"] == "skipped"
    mock_supervisor.addon_install.assert_not_called()
    mock_supervisor.addon_start.assert_not_called()


@pytest.mark.asyncio
async def test_started_when_installed_but_stopped(mock_supervisor):
    """Installed but stopped → ``started``."""
    mock_supervisor.addons_list.return_value = [
        _addon("core_mosquitto", state="stopped")
    ]
    mock_supervisor.addon_info.return_value = {
        "version_installed": "2.0",
        "state": "stopped",
    }

    result = await install_or_start_addon("mosquitto", start=True)
    assert result["status"] == "started"
    mock_supervisor.addon_install.assert_not_called()
    mock_supervisor.addon_start.assert_called_once_with("core_mosquitto")


@pytest.mark.asyncio
async def test_install_failure_returns_failed(mock_supervisor):
    """When ``addon_install`` raises, status should be ``failed``."""
    mock_supervisor.addons_list.return_value = []
    mock_supervisor.store_addons_list.return_value = [_addon("core_mosquitto")]
    mock_supervisor.addon_info.return_value = {}
    mock_supervisor.addon_install.side_effect = RuntimeError("disk full")

    result = await install_or_start_addon("mosquitto", start=True)
    assert result["status"] == "failed"
    assert "install_failed" in result["error"]


@pytest.mark.asyncio
async def test_start_failure_after_install_returns_failed(mock_supervisor):
    """Install succeeds but start fails → ``failed`` with proper marker."""
    mock_supervisor.addons_list.return_value = []
    mock_supervisor.store_addons_list.return_value = [_addon("core_mosquitto")]
    mock_supervisor.addon_info.return_value = {}
    mock_supervisor.addon_start.side_effect = RuntimeError("timeout")

    result = await install_or_start_addon("mosquitto", start=True)
    assert result["status"] == "failed"
    assert "start_after_install_failed" in result["error"]


@pytest.mark.asyncio
async def test_forbidden_addon_rejected(mock_supervisor):
    """Unknown name → ``failed`` with ``forbidden_addon`` source."""
    result = await install_or_start_addon("evil_addon", start=True)
    assert result["status"] == "failed"
    assert result["source"] == "forbidden_slug"
    assert "forbidden_addon" in result["error"]
    mock_supervisor.addons_list.assert_not_called()


@pytest.mark.asyncio
async def test_install_with_options(mock_supervisor):
    """When options are passed, ``addon_options`` must be called."""
    mock_supervisor.addons_list.return_value = []
    mock_supervisor.store_addons_list.return_value = [_addon("core_mosquitto")]
    mock_supervisor.addon_info.return_value = {}

    result = await install_or_start_addon(
        "mosquitto", options={"logins": [{"user": "x"}]}, start=True
    )
    assert result["status"] == "installed"
    assert result["options_applied"] is True
    mock_supervisor.addon_options.assert_called_once_with(
        "core_mosquitto", {"logins": [{"user": "x"}]}
    )


@pytest.mark.asyncio
async def test_install_options_failure_does_not_block_start(mock_supervisor):
    """If ``addon_options`` fails, we still try to start (best-effort)."""
    mock_supervisor.addons_list.return_value = []
    mock_supervisor.store_addons_list.return_value = [_addon("core_mosquitto")]
    mock_supervisor.addon_info.return_value = {}
    mock_supervisor.addon_options.side_effect = RuntimeError("schema mismatch")

    result = await install_or_start_addon(
        "mosquitto", options={"x": 1}, start=True
    )
    assert result["status"] == "installed"
    assert result["options_applied"] is False
    mock_supervisor.addon_start.assert_called_once()


@pytest.mark.asyncio
async def test_install_without_start(mock_supervisor):
    """When ``start=False``, the addon is installed but never started."""
    mock_supervisor.addons_list.return_value = []
    mock_supervisor.store_addons_list.return_value = [
        _addon("a0d7b954_cloudflared")
    ]
    mock_supervisor.addon_info.return_value = {}

    result = await install_or_start_addon("cloudflared", start=False)
    assert result["status"] == "installed"
    mock_supervisor.addon_install.assert_called_once()
    mock_supervisor.addon_start.assert_not_called()


# ─── bootstrap_stack ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bootstrap_stack_full_install(mock_supervisor, mock_yaml_patch):
    """Nothing installed → installs mosquitto + z2m + cloudflared + patches HA."""
    # First pass: nothing installed
    mock_supervisor.addons_list.return_value = []
    mock_supervisor.store_addons_list.return_value = [
        _addon("core_mosquitto"),
        _addon("45df7312_zigbee2mqtt"),
        _addon("a0d7b954_cloudflared"),
    ]
    mock_supervisor.addon_info.return_value = {}

    result = await bootstrap_stack(_DummyConfig())
    assert result["ok"] is True
    assert result["errors"] == []
    assert len(result["actions"]) == 3
    # Ordering: mosquitto first, z2m second, cloudflared last
    names = [a["name"] for a in result["actions"]]
    assert names == ["mosquitto", "zigbee2mqtt", "cloudflared"]
    # Cloudflared installed but not started (waits for token)
    cf_action = next(a for a in result["actions"] if a["name"] == "cloudflared")
    assert cf_action["status"] == "installed"
    # HA config patch applied
    assert result["ha_config_patch"]["ok"] is True
    assert result["ha_config_patch"]["changed"] is True
    assert result["ha_restart_pending"] is True
    # ``summary`` is human-friendly
    assert "installed" in result["summary"]


@pytest.mark.asyncio
async def test_bootstrap_stack_idempotent(mock_supervisor, mock_yaml_patch):
    """All add-ons already installed + started + HA config OK → all skipped, no restart pending."""
    mock_supervisor.addons_list.return_value = [
        _addon("core_mosquitto", state="started"),
        _addon("45df7312_zigbee2mqtt", state="started"),
        _addon("a0d7b954_cloudflared", state="stopped"),  # cloudflared not started
    ]
    mock_supervisor.addon_info.side_effect = lambda slug: {
        "version_installed": "2.0",
        "state": (
            "stopped" if "cloudflared" in slug else "started"
        ),
    }
    # Pre-create configuration.yaml with the patches already applied.
    # Le bloc patché est GÉNÉRÉ depuis MOLI_HA_CONFIG_PATCH (source de vérité)
    # pour que ce test d'idempotence ne dérive plus à chaque évolution du
    # thème/patch (leçon 0.19.0 : fixture figée = faux négatif).
    import io as _io
    from ruamel.yaml import YAML as _YAML
    from molini_agent.bootstrap import MOLI_HA_CONFIG_PATCH
    _buf = _io.StringIO()
    _y = _YAML()
    _y.default_flow_style = False
    _y.dump(MOLI_HA_CONFIG_PATCH, _buf)
    mock_yaml_patch.write_text(
        "default_config:\n"
        + _buf.getvalue()
        # Blocs Moli (v0.8 / 0.17.0) — une box idempotente les a déjà
        + "homeassistant:\n"
        "  packages: !include_dir_named packages\n"
        "lovelace:\n"
        "  dashboards:\n"
        "    moli-energie:\n"
        "      mode: yaml\n"
        "      filename: dashboards/molini.yaml\n",
        encoding="utf-8",
    )

    result = await bootstrap_stack(_DummyConfig())
    assert result["ok"] is True
    assert result["errors"] == []
    # Mosquitto + Z2M skipped (started), cloudflared also skipped since start=False
    mosquitto = next(a for a in result["actions"] if a["name"] == "mosquitto")
    z2m = next(a for a in result["actions"] if a["name"] == "zigbee2mqtt")
    cf = next(a for a in result["actions"] if a["name"] == "cloudflared")
    assert mosquitto["status"] == "skipped"
    assert z2m["status"] == "skipped"
    assert cf["status"] == "skipped"  # not started (start_now=False) and already installed
    # HA config no change → no restart pending
    assert result["ha_config_patch"]["changed"] is False
    assert result["ha_restart_pending"] is False
    # No install/start calls
    mock_supervisor.addon_install.assert_not_called()
    mock_supervisor.addon_start.assert_not_called()


@pytest.mark.asyncio
async def test_bootstrap_stack_partial_failure_reports_errors(
    mock_supervisor, mock_yaml_patch
):
    """If mosquitto install fails, z2m and cloudflared should still be attempted."""
    mock_supervisor.addons_list.return_value = []
    mock_supervisor.store_addons_list.return_value = [
        _addon("core_mosquitto"),
        _addon("45df7312_zigbee2mqtt"),
        _addon("a0d7b954_cloudflared"),
    ]
    mock_supervisor.addon_info.return_value = {}

    install_calls: list[str] = []

    async def fake_install(slug: str) -> dict:
        install_calls.append(slug)
        if slug == "core_mosquitto":
            raise RuntimeError("supervisor 500")
        return {}

    mock_supervisor.addon_install.side_effect = fake_install

    result = await bootstrap_stack(_DummyConfig())
    assert result["ok"] is False
    assert len(result["errors"]) == 1
    assert "mosquitto" in result["errors"][0]
    # All 3 add-ons were attempted
    assert install_calls == [
        "core_mosquitto",
        "45df7312_zigbee2mqtt",
        "a0d7b954_cloudflared",
    ]


@pytest.mark.asyncio
async def test_bootstrap_stack_can_limit_addons(mock_supervisor, mock_yaml_patch):
    """Payload ``{addons: ['mosquitto']}`` → only mosquitto is touched."""
    mock_supervisor.addons_list.return_value = []
    mock_supervisor.store_addons_list.return_value = [_addon("core_mosquitto")]
    mock_supervisor.addon_info.return_value = {}

    result = await bootstrap_stack(
        _DummyConfig(), payload={"addons": ["mosquitto"]}
    )
    assert len(result["actions"]) == 1
    assert result["actions"][0]["name"] == "mosquitto"


@pytest.mark.asyncio
async def test_bootstrap_stack_filters_forbidden_addons(
    mock_supervisor, mock_yaml_patch
):
    """Payload with ``evil_addon`` → silently filtered out."""
    mock_supervisor.addons_list.return_value = []
    mock_supervisor.store_addons_list.return_value = [_addon("core_mosquitto")]
    mock_supervisor.addon_info.return_value = {}

    result = await bootstrap_stack(
        _DummyConfig(), payload={"addons": ["evil_addon", "mosquitto"]}
    )
    assert len(result["actions"]) == 1
    assert result["actions"][0]["name"] == "mosquitto"


@pytest.mark.asyncio
async def test_bootstrap_stack_skip_ha_config(mock_supervisor, mock_yaml_patch):
    """``skip_ha_config: True`` skips the YAML patch entirely."""
    mock_supervisor.addons_list.return_value = [
        _addon("core_mosquitto", state="started"),
        _addon("45df7312_zigbee2mqtt", state="started"),
        _addon("a0d7b954_cloudflared", state="stopped"),
    ]
    mock_supervisor.addon_info.return_value = {
        "version_installed": "2.0",
        "state": "started",
    }

    result = await bootstrap_stack(
        _DummyConfig(), payload={"skip_ha_config": True}
    )
    assert result["ha_config_patch"]["skipped"] is True
    assert result["ha_restart_pending"] is False
    assert not mock_yaml_patch.exists()


@pytest.mark.asyncio
async def test_bootstrap_stack_extra_patch_filters_forbidden_keys(
    mock_supervisor, mock_yaml_patch
):
    """``ha_config_extra`` with a forbidden key (e.g. ``python_script``) fails."""
    mock_supervisor.addons_list.return_value = [
        _addon("core_mosquitto", state="started"),
        _addon("45df7312_zigbee2mqtt", state="started"),
        _addon("a0d7b954_cloudflared", state="stopped"),
    ]
    mock_supervisor.addon_info.return_value = {
        "version_installed": "2.0",
        "state": "started",
    }

    result = await bootstrap_stack(
        _DummyConfig(),
        payload={"ha_config_extra": {"python_script": {}}},
    )
    # Bootstrap should have reported the YAML error in errors[]
    assert result["ok"] is False
    assert any("ha_config" in e for e in result["errors"])
    assert result["ha_config_patch"]["ok"] is False
    assert "forbidden_key" in result["ha_config_patch"]["error"]


# ─── patch_ha_config (direct) ────────────────────────────────────────────────


def test_patch_ha_config_creates_file(tmp_path):
    target = tmp_path / "configuration.yaml"
    result = patch_ha_config(
        {"http": {"use_x_forwarded_for": True}}, config_path=str(target)
    )
    assert result["ok"] is True
    assert result["changed"] is True
    assert target.exists()


def test_patch_ha_config_forbidden_key_returns_error(tmp_path):
    target = tmp_path / "configuration.yaml"
    result = patch_ha_config(
        {"shell_command": {"x": "y"}}, config_path=str(target)
    )
    assert result["ok"] is False
    assert "forbidden_key" in result["error"]
    # File must not have been created
    assert not target.exists()


def test_patch_ha_config_idempotent_via_top_level(tmp_path):
    target = tmp_path / "configuration.yaml"
    patch = {
        "http": {"use_x_forwarded_for": True, "trusted_proxies": ["172.30.0.0/16"]},
        "recorder": {"purge_keep_days": 14},
    }
    r1 = patch_ha_config(patch, config_path=str(target))
    r2 = patch_ha_config(patch, config_path=str(target))
    assert r1["changed"] is True
    assert r2["changed"] is False
