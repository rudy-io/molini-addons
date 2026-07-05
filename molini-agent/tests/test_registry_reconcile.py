# molini-agent/tests/test_registry_reconcile.py
"""Tests du self-heal registre (plan pur, sans WebSocket) + overrides de rôles.

Rejoue les cas RÉELS du post-mortem 0.18.x chez Carole :
- squatteur legacy (molini_solar_power_w) sur l'entity_id canonique → _2
- collision d'uid capteur/switch → _2 en cascade
- entrées disabled_by:user héritées du retrait 0.15.0
"""
from __future__ import annotations

import pytest

from molini_agent.ha_discovery import (
    PACKAGE_TEMPLATE_UIDS,
    apply_role_overrides,
    expected_uids_for,
    generate_yaml,
)
from molini_agent.registry_reconcile import (
    LEGACY_UIDS,
    plan_reconcile,
    ws_url_from_ha_url,
)


def _entry(entity_id, unique_id, platform="template", disabled_by=None):
    return {
        "entity_id": entity_id,
        "unique_id": unique_id,
        "platform": platform,
        "disabled_by": disabled_by,
    }


# ─── plan_reconcile — cas réels ──────────────────────────────────────────────

def test_plan_squatter_legacy_then_rename():
    """Cas Carole : l'ancien uid solar_power_w squatte l'entity_id canonique,
    la nouvelle entité vit en _2 → purge du legacy + rename du _2."""
    entries = [
        _entry("sensor.molini_solaire_production", "molini_solar_power_w"),
        _entry("sensor.molini_solaire_production_2", "molini_solaire_production"),
    ]
    actions, report = plan_reconcile(entries, {"molini_solaire_production"})
    kinds = [(a.kind, a.entity_id, a.new_entity_id) for a in actions]
    assert ("remove", "sensor.molini_solaire_production", None) in kinds
    assert (
        "rename",
        "sensor.molini_solaire_production_2",
        "sensor.molini_solaire_production",
    ) in kinds
    assert not report.conflicts


def test_plan_enable_disabled_user():
    """Entrées disabled_by:user héritées (retrait 0.15.0) → enable."""
    entries = [
        _entry(
            "sensor.molini_consommation_maison",
            "molini_consommation_maison",
            disabled_by="user",
        ),
    ]
    actions, _ = plan_reconcile(entries, {"molini_consommation_maison"})
    assert [(a.kind, a.entity_id) for a in actions] == [
        ("enable", "sensor.molini_consommation_maison")
    ]


def test_plan_rename_2_to_canonical():
    entries = [_entry("sensor.molini_reseau_2", "molini_reseau")]
    actions, _ = plan_reconcile(entries, {"molini_reseau"})
    assert actions[0].kind == "rename"
    assert actions[0].new_entity_id == "sensor.molini_reseau"


def test_plan_noop_on_clean_registry():
    """Box propre → aucun plan (idempotence du self-heal)."""
    entries = [
        _entry("sensor.molini_reseau", "molini_reseau"),
        _entry("switch.molini_chauffe_eau", "molini_chauffe_eau"),
    ]
    actions, report = plan_reconcile(
        entries, {"molini_reseau", "molini_chauffe_eau"}
    )
    assert actions == [] and not report.conflicts


def test_plan_never_removes_unknown_uid():
    """SÛRETÉ : un uid molini_ inconnu (rôle non détecté ce run) n'est JAMAIS
    supprimé — seule la liste explicite LEGACY_UIDS est purgeable."""
    entries = [
        _entry("sensor.molini_puissance_soutiree", "molini_puissance_soutiree"),
    ]
    # expected VIDE (linky pas détecté ce run) → aucune action destructive
    actions, _ = plan_reconcile(entries, set())
    assert actions == []


def test_plan_conflict_reported_not_forced():
    """Canonique occupé par un uid NON-legacy inconnu → conflit reporté, pas
    d'action destructive."""
    entries = [
        _entry("sensor.molini_reseau", "molini_custom_du_client"),
        _entry("sensor.molini_reseau_2", "molini_reseau"),
    ]
    actions, report = plan_reconcile(entries, {"molini_reseau"})
    assert all(a.kind != "remove" for a in actions)
    assert any("molini_reseau" in c for c in report.conflicts)


def test_plan_ignores_non_template_platforms():
    """On ne touche jamais aux plateformes hors template (utility_meter…)."""
    entries = [
        _entry("sensor.molini_soutire_jour_2", "molini_soutire_jour", platform="utility_meter"),
    ]
    actions, _ = plan_reconcile(entries, {"molini_soutire_jour"})
    assert actions == []


def test_ws_url_from_ha_url():
    assert ws_url_from_ha_url("http://supervisor/core") == "ws://supervisor/core/websocket"
    assert ws_url_from_ha_url("https://x.moli.energy") == "wss://x.moli.energy/websocket"


# ─── expected_uids_for / PACKAGE_TEMPLATE_UIDS ───────────────────────────────

def test_expected_uids_match_package():
    """GARDE-FOU : PACKAGE_TEMPLATE_UIDS doit rester le miroir exact des
    capteurs template du package statique molini_energy.yaml."""
    from pathlib import Path
    from ruamel.yaml import YAML

    pkg = (
        Path(__file__).resolve().parents[1]
        / "rootfs/usr/share/molini/packages/molini_energy.yaml"
    )
    doc = YAML(typ="safe").load(pkg.read_text(encoding="utf-8"))
    uids = {
        s["unique_id"]
        for item in doc.get("template", [])
        for s in item.get("sensor", [])
    }
    assert uids == set(PACKAGE_TEMPLATE_UIDS)


def test_expected_uids_for_water_heater():
    uids = expected_uids_for({"water_heater": "switch.x_output_0"})
    assert "molini_chauffe_eau" in uids
    assert "molini_chauffe_eau_puissance" in uids


def test_legacy_uids_disjoint_from_expected():
    """Un uid ne peut pas être à la fois legacy (purgeable) et attendu."""
    all_expected = expected_uids_for(
        {r: "x" for r in (
            "linky_power", "linky_soutire_total", "linky_hc", "linky_hp",
            "tempo_today", "tempo_tomorrow", "solar_power",
            "solar_energy_today", "solar_energy_total", "grid_power",
            "grid_import_total", "grid_export_total", "water_heater",
        )}
    )
    assert not (LEGACY_UIDS & all_expected)


# ─── apply_role_overrides — systématisation multi-marques ────────────────────

LIVE = {
    "sensor.eastron_sdm120_power",
    "sensor.tuya_clamp_puissance",
    "switch.legrand_contacteur_ecs",
    "sensor.legrand_contacteur_ecs_power",
}


def test_override_grid_power_any_brand():
    """Une marque hors patterns (Eastron, Tuya…) se câble par override."""
    detected, ignored = apply_role_overrides(
        {}, {"grid_power": "sensor.eastron_sdm120_power"}, LIVE
    )
    assert detected["grid_power"] == "sensor.eastron_sdm120_power"
    assert ignored == []
    assert "molini_reseau" in generate_yaml(detected)


def test_override_beats_pattern_detection():
    detected, _ = apply_role_overrides(
        {"grid_power": "sensor.shellypro3em_x_puissance"},
        {"grid_power": "sensor.tuya_clamp_puissance"},
        LIVE,
    )
    assert detected["grid_power"] == "sensor.tuya_clamp_puissance"


def test_override_water_heater_non_shelly_with_power():
    """Charge pilotée non-Shelly : switch + capteur puissance via overrides."""
    detected, ignored = apply_role_overrides(
        {},
        {
            "water_heater": "switch.legrand_contacteur_ecs",
            "water_heater_power": "sensor.legrand_contacteur_ecs_power",
        },
        LIVE,
    )
    assert ignored == []
    y = generate_yaml(detected)
    assert "switch.legrand_contacteur_ecs" in y            # switch piloté
    assert "sensor.legrand_contacteur_ecs_power" in y      # puissance override
    assert "unique_id: molini_chauffe_eau" in y
    assert "molini_chauffe_eau_puissance" in y


def test_override_rejects_wrong_domain_and_dead_entity():
    detected, ignored = apply_role_overrides(
        {},
        {
            "water_heater": "sensor.pas_un_switch",     # mauvais domaine
            "grid_power": "sensor.inexistant",          # entité absente
            "role_bidon": "sensor.eastron_sdm120_power",  # rôle inconnu
        },
        LIVE,
    )
    assert detected == {}
    assert len(ignored) == 3


def test_override_null_removes_role():
    """Override null = désactivation explicite d'un rôle détecté."""
    detected, ignored = apply_role_overrides(
        {"solar_power": ["sensor.inverter_pv_power"]},
        {"solar_power": None},
        LIVE,
    )
    assert "solar_power" not in detected
    assert ignored == []


def test_override_multi_sum_role_wrapped_in_list():
    detected, _ = apply_role_overrides(
        {}, {"solar_power": "sensor.tuya_clamp_puissance"}, LIVE
    )
    assert detected["solar_power"] == ["sensor.tuya_clamp_puissance"]
