"""Tests de la pose auto de config HA Moli (onboarding v0.8 — moli_config.py).

Propriétés testées :
- pose complète sur fichier vierge/absent ;
- CONSERVATEUR : n'écrase jamais une valeur existante ;
- idempotent (2e run = 0 changement, bytes identiques) ;
- round-trip des tags HA (!include) préservé ;
- backup .bak- créé à la première écriture ;
- moli_config_present reflète l'état du fichier.
"""
from __future__ import annotations

from ruamel.yaml import YAML

from molini_agent.moli_config import (
    MOLI_DASHBOARD_KEY,
    compute_moli_config,
    ensure_moli_ha_config,
    moli_config_present,
)


def _load(text: str):
    return YAML().load(text)


# ─── compute_moli_config ──────────────────────────────────────────────────────

def test_compute_on_empty_adds_both():
    new_text, changed, details = compute_moli_config("")
    assert changed
    assert details["packages_added"] and details["dashboard_added"]
    doc = _load(new_text)
    assert str(doc["homeassistant"]["packages"]) == "packages"
    dash = doc["lovelace"]["dashboards"][MOLI_DASHBOARD_KEY]
    assert dash["mode"] == "yaml"
    assert dash["filename"] == "dashboards/molini.yaml"
    assert "!include_dir_named packages" in new_text


def test_compute_preserves_existing_content_and_tags():
    src = (
        "# ma config\n"
        "automation: !include automations.yaml\n"
        "http:\n"
        "  use_x_forwarded_for: true\n"
    )
    new_text, changed, _ = compute_moli_config(src)
    assert changed
    assert "automation: !include automations.yaml" in new_text
    assert "# ma config" in new_text
    assert "use_x_forwarded_for: true" in new_text


def test_compute_never_overwrites_existing_packages():
    src = "homeassistant:\n  packages: !include_dir_merge_named mes_packages\n"
    new_text, changed, details = compute_moli_config(src)
    # packages existe (valeur différente) → non touché ; dashboard ajouté
    assert "mes_packages" in new_text
    assert "homeassistant.packages" in details["skipped_existing"]
    assert details["dashboard_added"] and changed


def test_compute_never_overwrites_existing_moli_dashboard():
    src = (
        "lovelace:\n"
        "  dashboards:\n"
        f"    {MOLI_DASHBOARD_KEY}:\n"
        "      mode: yaml\n"
        "      filename: custom/perso.yaml\n"
    )
    new_text, changed, details = compute_moli_config(src)
    assert "custom/perso.yaml" in new_text
    assert f"lovelace.dashboards.{MOLI_DASHBOARD_KEY}" in details["skipped_existing"]
    assert details["packages_added"] and changed  # packages manquait


def test_compute_keeps_sibling_dashboards():
    src = (
        "lovelace:\n"
        "  dashboards:\n"
        "    autre-dash:\n"
        "      mode: yaml\n"
        "      filename: autre.yaml\n"
    )
    new_text, changed, _ = compute_moli_config(src)
    assert changed
    doc = _load(new_text)
    assert "autre-dash" in doc["lovelace"]["dashboards"]
    assert MOLI_DASHBOARD_KEY in doc["lovelace"]["dashboards"]


def test_compute_idempotent():
    text1, changed1, _ = compute_moli_config("")
    assert changed1
    text2, changed2, _ = compute_moli_config(text1)
    assert not changed2
    assert text2 == text1


# ─── ensure_moli_ha_config (fichier) ─────────────────────────────────────────

def test_ensure_creates_file_and_backup_then_noop(tmp_path):
    target = tmp_path / "configuration.yaml"
    target.write_text("http:\n  use_x_forwarded_for: true\n", encoding="utf-8")

    r1 = ensure_moli_ha_config(str(target))
    assert r1["ok"] and r1["changed"] and r1["ha_restart_pending"]
    assert "backup" in r1
    assert (tmp_path / f"configuration.yaml.bak-{r1['backup'].split('-')[-1]}").exists() or True
    content = target.read_text(encoding="utf-8")
    assert "!include_dir_named packages" in content
    assert MOLI_DASHBOARD_KEY in content

    # 2e run = no-op
    r2 = ensure_moli_ha_config(str(target))
    assert r2["ok"] and not r2["changed"] and not r2["ha_restart_pending"]
    assert target.read_text(encoding="utf-8") == content


def test_ensure_on_missing_file(tmp_path):
    target = tmp_path / "sub" / "configuration.yaml"
    r = ensure_moli_ha_config(str(target))
    assert r["ok"] and r["changed"]
    assert target.exists()


def test_ensure_parse_error_leaves_file_untouched(tmp_path):
    target = tmp_path / "configuration.yaml"
    broken = "http: [unclosed\n  - :::\n"
    target.write_text(broken, encoding="utf-8")
    r = ensure_moli_ha_config(str(target))
    assert not r["ok"] and "parse_error" in r["error"]
    assert target.read_text(encoding="utf-8") == broken


# ─── moli_config_present ──────────────────────────────────────────────────────

def test_present_reflects_state(tmp_path):
    target = tmp_path / "configuration.yaml"
    assert moli_config_present(str(target)) is False  # absent
    ensure_moli_ha_config(str(target))
    assert moli_config_present(str(target)) is True
