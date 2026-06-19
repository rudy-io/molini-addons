"""Tests for ``molini_agent.yaml_patch``.

Coverage targets:
- Idempotence: same patch applied twice = no file change
- Deep merge: nested mappings merge correctly
- List merge: set-union semantics on ``trusted_proxies``
- Comments preserved: ruamel round-trip
- White-list enforcement: forbidden keys raise ``YamlPatchError``
- Atomic write: temp file + rename
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from molini_agent.yaml_patch import (
    PATCHABLE_TOP_KEYS,
    YamlPatchError,
    apply_patch_to_file,
    compute_patch,
    remove_top_keys_in_file,
)


# ─── compute_patch (pure function) ────────────────────────────────────────────


def test_compute_patch_on_empty_returns_new_content():
    new_text, changed, report = compute_patch(
        "", {"http": {"use_x_forwarded_for": True}}
    )
    assert changed is True
    assert report["changed"] is True
    assert "http:" in new_text
    assert "use_x_forwarded_for" in new_text
    assert report["applied_keys"] == ["http"]


def test_compute_patch_is_idempotent():
    initial = ""
    patch = {
        "http": {
            "use_x_forwarded_for": True,
            "trusted_proxies": ["172.30.0.0/16"],
        },
        "recorder": {"purge_keep_days": 14},
    }
    after_1, changed_1, _ = compute_patch(initial, patch)
    assert changed_1 is True
    after_2, changed_2, report_2 = compute_patch(after_1, patch)
    assert changed_2 is False
    assert report_2["changed"] is False
    # Same content
    assert after_1 == after_2


def test_compute_patch_preserves_existing_keys():
    initial = (
        "default_config:\n"
        "frontend:\n"
        "  themes: !include_dir_merge_named themes\n"
        "http:\n"
        "  ssl_certificate: /ssl/fullchain.pem\n"
    )
    new_text, changed, _ = compute_patch(
        initial,
        {"http": {"use_x_forwarded_for": True}},
    )
    assert changed is True
    assert "ssl_certificate" in new_text
    assert "use_x_forwarded_for" in new_text
    assert "default_config" in new_text
    assert "themes" in new_text


def test_compute_patch_preserves_comments():
    initial = (
        "# Top-level HA configuration\n"
        "default_config:\n"
        "\n"
        "# HTTP layer\n"
        "http:\n"
        "  # SSL certificate paths\n"
        "  ssl_certificate: /ssl/fullchain.pem\n"
    )
    new_text, changed, _ = compute_patch(
        initial,
        {"http": {"use_x_forwarded_for": True}},
    )
    assert changed is True
    assert "# Top-level HA configuration" in new_text
    assert "# HTTP layer" in new_text
    assert "# SSL certificate paths" in new_text


def test_list_merge_is_set_union():
    initial = (
        "http:\n"
        "  trusted_proxies:\n"
        "    - 10.0.0.0/8\n"
    )
    new_text, changed, _ = compute_patch(
        initial,
        {"http": {"trusted_proxies": ["172.30.0.0/16", "10.0.0.0/8"]}},
    )
    assert changed is True
    # Both items present, original first
    assert "10.0.0.0/8" in new_text
    assert "172.30.0.0/16" in new_text
    # No duplicate
    assert new_text.count("10.0.0.0/8") == 1


def test_list_merge_idempotent_when_already_present():
    initial = (
        "http:\n"
        "  trusted_proxies:\n"
        "    - 172.30.0.0/16\n"
    )
    _, changed, _ = compute_patch(
        initial,
        {"http": {"trusted_proxies": ["172.30.0.0/16"]}},
    )
    assert changed is False


def test_scalar_overwrite_when_different():
    initial = "recorder:\n  purge_keep_days: 7\n"
    new_text, changed, _ = compute_patch(
        initial, {"recorder": {"purge_keep_days": 14}}
    )
    assert changed is True
    assert "purge_keep_days: 14" in new_text
    assert "purge_keep_days: 7" not in new_text


def test_scalar_same_value_is_idempotent():
    initial = "recorder:\n  purge_keep_days: 14\n"
    _, changed, _ = compute_patch(
        initial, {"recorder": {"purge_keep_days": 14}}
    )
    assert changed is False


# ─── White-list enforcement ───────────────────────────────────────────────────


def test_forbidden_top_level_key_raises():
    # ``python_script`` is the classical RCE surface
    with pytest.raises(YamlPatchError, match="forbidden_key"):
        compute_patch("", {"python_script": {}})


def test_forbidden_shell_command_raises():
    with pytest.raises(YamlPatchError, match="forbidden_key"):
        compute_patch("", {"shell_command": {"backdoor": "rm -rf /"}})


def test_forbidden_automation_raises():
    with pytest.raises(YamlPatchError, match="forbidden_key"):
        compute_patch("", {"automation": []})


def test_forbidden_homeassistant_raises():
    # ``homeassistant`` (root config) is *not* in the whitelist either —
    # ``allowlist_external_dirs``, ``allowlist_external_urls`` can be abused
    with pytest.raises(YamlPatchError, match="forbidden_key"):
        compute_patch("", {"homeassistant": {"allowlist_external_urls": ["http://attacker.com"]}})


def test_whitelist_contains_expected_keys():
    """Sanity: the white-list should at least contain the Moli defaults."""
    assert "http" in PATCHABLE_TOP_KEYS
    assert "recorder" in PATCHABLE_TOP_KEYS
    assert "frontend" in PATCHABLE_TOP_KEYS


def test_whitelist_contains_panel_custom():
    """Le panel front Moli s'enregistre via panel_custom (JS client, pas RCE)."""
    assert "panel_custom" in PATCHABLE_TOP_KEYS


def test_panel_custom_patch_is_idempotent():
    """Re-provisionner le panel ne doit PAS empiler un doublon (merge union)."""
    patch = {
        "panel_custom": [
            {
                "name": "moli-panel",
                "sidebar_title": "Moli",
                "url_path": "moli",
                "module_url": "/local/moli/moli-panel.js",
            }
        ]
    }
    after_1, changed_1, _ = compute_patch("", patch)
    assert changed_1 is True
    assert "moli-panel" in after_1
    after_2, changed_2, _ = compute_patch(after_1, patch)
    assert changed_2 is False
    assert after_1 == after_2
    assert after_2.count("module_url") == 1


def test_whitelist_excludes_dangerous_keys():
    """Regression: the dangerous keys must NEVER end up in the white-list."""
    for forbidden in (
        "python_script",
        "shell_command",
        "command_line",
        "rest_command",
        "automation",
        "homeassistant",
    ):
        assert forbidden not in PATCHABLE_TOP_KEYS, (
            f"{forbidden!r} must not be patchable — RCE surface"
        )


def test_yaml_parse_error_is_wrapped():
    """Garbage YAML input should raise ``YamlPatchError`` not bubble up."""
    with pytest.raises(YamlPatchError, match="yaml_parse_error"):
        compute_patch("http: {\n  trusted_proxies: [", {"http": {}})


def test_yaml_root_not_mapping_raises():
    """A YAML root that is a list or scalar is not patchable."""
    with pytest.raises(YamlPatchError, match="yaml_root_not_mapping"):
        compute_patch("- just_a_list\n- of_items\n", {"http": {}})


# ─── apply_patch_to_file (filesystem) ────────────────────────────────────────


def test_apply_patch_to_file_idempotent(tmp_path: Path):
    target = tmp_path / "configuration.yaml"
    target.write_text("default_config:\n", encoding="utf-8")
    patch = {"http": {"use_x_forwarded_for": True}}

    r1 = apply_patch_to_file(str(target), patch)
    assert r1["changed"] is True
    content_after_1 = target.read_text(encoding="utf-8")

    r2 = apply_patch_to_file(str(target), patch)
    assert r2["changed"] is False
    content_after_2 = target.read_text(encoding="utf-8")

    assert content_after_1 == content_after_2


def test_apply_patch_to_file_creates_backup(tmp_path: Path):
    target = tmp_path / "configuration.yaml"
    target.write_text("default_config:\n", encoding="utf-8")
    patch = {"http": {"use_x_forwarded_for": True}}

    r = apply_patch_to_file(str(target), patch)
    assert r["changed"] is True
    assert "backup" in r
    assert os.path.exists(r["backup"])


def test_apply_patch_to_file_no_backup_when_no_change(tmp_path: Path):
    target = tmp_path / "configuration.yaml"
    target.write_text(
        "http:\n  use_x_forwarded_for: true\n", encoding="utf-8"
    )
    patch = {"http": {"use_x_forwarded_for": True}}

    r = apply_patch_to_file(str(target), patch)
    assert r["changed"] is False
    # No backup created since no change
    assert "backup" not in r


def test_apply_patch_to_file_creates_dir(tmp_path: Path):
    target = tmp_path / "subdir" / "configuration.yaml"
    patch = {"http": {"use_x_forwarded_for": True}}

    r = apply_patch_to_file(str(target), patch)
    assert r["changed"] is True
    assert target.exists()


def test_apply_patch_to_file_rejects_relative_path():
    with pytest.raises(YamlPatchError, match="path_not_absolute"):
        apply_patch_to_file("relative/path.yaml", {"http": {}})


def test_apply_patch_to_file_preserves_existing_complex_yaml(tmp_path: Path):
    """End-to-end smoke: realistic HA configuration.yaml stays valid."""
    target = tmp_path / "configuration.yaml"
    initial = (
        "# Loads default set of integrations. Do not remove.\n"
        "default_config:\n"
        "\n"
        "# Load frontend themes from the themes folder\n"
        "frontend:\n"
        "  themes: !include_dir_merge_named themes\n"
        "\n"
        "automation: !include automations.yaml\n"
        "script: !include scripts.yaml\n"
        "scene: !include scenes.yaml\n"
        "\n"
        "http:\n"
        "  ssl_certificate: /ssl/fullchain.pem\n"
        "  ssl_key: /ssl/privkey.pem\n"
    )
    target.write_text(initial, encoding="utf-8")
    patch = {
        "http": {
            "use_x_forwarded_for": True,
            "trusted_proxies": ["172.30.0.0/16"],
        },
        "recorder": {"purge_keep_days": 14},
    }
    r = apply_patch_to_file(str(target), patch)
    assert r["changed"] is True
    out = target.read_text(encoding="utf-8")
    # Original keys preserved
    assert "default_config" in out
    assert "themes: !include_dir_merge_named themes" in out
    assert "ssl_certificate: /ssl/fullchain.pem" in out
    assert "automation: !include automations.yaml" in out
    # Patches applied
    assert "use_x_forwarded_for: true" in out.lower()
    assert "172.30.0.0/16" in out
    assert "purge_keep_days: 14" in out
    # Comments preserved
    assert "# Loads default set of integrations" in out


# ─── Edge cases ──────────────────────────────────────────────────────────────


def test_empty_patch_is_noop():
    _, changed, _ = compute_patch("default_config:\n", {})
    assert changed is False


def test_patch_with_only_already_present_value():
    initial = (
        "http:\n"
        "  use_x_forwarded_for: true\n"
        "  trusted_proxies:\n"
        "    - 172.30.0.0/16\n"
    )
    _, changed, report = compute_patch(
        initial,
        {
            "http": {
                "use_x_forwarded_for": True,
                "trusted_proxies": ["172.30.0.0/16"],
            }
        },
    )
    assert changed is False
    assert report["changed"] is False


def test_partial_change_only_lists_keys_actually_modified():
    """``applied_keys`` reflects which top-level keys were in the patch."""
    initial = "http:\n  use_x_forwarded_for: true\n"
    _, changed, report = compute_patch(
        initial,
        {"http": {"use_x_forwarded_for": True}, "recorder": {"purge_keep_days": 14}},
    )
    assert changed is True
    # Both keys were in the patch — both reported, regardless of which actually mutated
    assert "http" in report["applied_keys"]
    assert "recorder" in report["applied_keys"]


# ─── remove_top_keys_in_file ──────────────────────────────────────────────────


def test_remove_panel_custom_is_in_patchable_keys():
    """Prerequisite: panel_custom must be removable (in PATCHABLE_TOP_KEYS)."""
    assert "panel_custom" in PATCHABLE_TOP_KEYS


def test_remove_present_key_changed_true(tmp_path):
    """Removing a present patchable key: changed=True, key listed in removed."""
    target = tmp_path / "configuration.yaml"
    target.write_text(
        "http:\n  use_x_forwarded_for: true\n"
        "panel_custom:\n  - name: moli-panel\n",
        encoding="utf-8",
    )
    report = remove_top_keys_in_file(str(target), ["panel_custom"])
    assert report["ok"] is True
    assert report["changed"] is True
    assert "panel_custom" in report["removed"]

    remaining = target.read_text(encoding="utf-8")
    assert "panel_custom" not in remaining
    assert "use_x_forwarded_for" in remaining  # other keys preserved


def test_remove_absent_key_is_noop(tmp_path):
    """Removing a key that doesn't exist: changed=False, removed is empty."""
    target = tmp_path / "configuration.yaml"
    target.write_text("http:\n  use_x_forwarded_for: true\n", encoding="utf-8")
    original_text = target.read_text(encoding="utf-8")

    report = remove_top_keys_in_file(str(target), ["panel_custom"])
    assert report["ok"] is True
    assert report["changed"] is False
    assert report["removed"] == []
    # File must be unchanged (no write performed on no-op)
    assert target.read_text(encoding="utf-8") == original_text


def test_remove_non_patchable_key_raises(tmp_path):
    """Keys outside PATCHABLE_TOP_KEYS must raise ValueError with forbidden_key."""
    target = tmp_path / "configuration.yaml"
    target.write_text("http:\n  use_x_forwarded_for: true\n", encoding="utf-8")
    with pytest.raises(ValueError, match="forbidden_key"):
        remove_top_keys_in_file(str(target), ["shell_command"])


def test_remove_multiple_keys(tmp_path):
    """Removing multiple keys: present ones removed, absent silently ignored."""
    target = tmp_path / "configuration.yaml"
    target.write_text(
        "http:\n  use_x_forwarded_for: true\n"
        "panel_custom:\n  - name: moli-panel\n"
        "recorder:\n  purge_keep_days: 14\n",
        encoding="utf-8",
    )
    report = remove_top_keys_in_file(
        str(target), ["panel_custom", "recorder", "frontend"]
    )
    assert set(report["removed"]) == {"panel_custom", "recorder"}
    assert report["changed"] is True
    remaining = target.read_text(encoding="utf-8")
    assert "panel_custom" not in remaining
    assert "recorder" not in remaining
    assert "http" in remaining
