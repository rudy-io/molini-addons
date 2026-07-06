# molini-agent/tests/test_ha_discovery.py
"""Tests unitaires pour ha_discovery — détection des entités + génération YAML."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from molini_agent.ha_discovery import (
    PATTERNS,
    discover_entities,
    generate_yaml,
)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _state(entity_id: str, state: str = "42") -> dict:
    return {"entity_id": entity_id, "state": state}


def _live_states(*eids: str) -> list[dict]:
    return [_state(eid) for eid in eids]


# ─── PATTERNS — rôle linky_power ──────────────────────────────────────────────

def test_linky_power_patterns_contains_zlinky_puissance():
    """Le pattern zlinky_puissance doit être présent dans linky_power."""
    import re
    patterns = PATTERNS["linky_power"]
    target = "sensor.lixee_zlinky_tic_puissance"
    matched = any(re.match(p, target, re.IGNORECASE) for p in patterns)
    assert matched, f"Aucun pattern linky_power ne matche {target!r}"


def test_linky_power_zlinky_puissance_is_first():
    """Le pattern zlinky_puissance doit être le PREMIER dans la liste (priorité)."""
    import re
    first_pattern = PATTERNS["linky_power"][0]
    target = "sensor.lixee_zlinky_tic_puissance"
    assert re.match(first_pattern, target, re.IGNORECASE), (
        f"Le premier pattern {first_pattern!r} ne matche pas {target!r}"
    )


def test_conso_power_role_absent():
    """Le rôle conso_power ne doit plus exister dans PATTERNS."""
    assert "conso_power" not in PATTERNS, (
        "Le rôle conso_power doit avoir été supprimé de PATTERNS"
    )


# ─── discover_entities — zlinky → linky_power ─────────────────────────────────

@pytest.mark.asyncio
async def test_discover_entities_maps_zlinky_to_linky_power():
    """sensor.lixee_zlinky_tic_puissance doit mapper au rôle linky_power."""
    from molini_agent.ha_client import HAClient

    fake_states = _live_states("sensor.lixee_zlinky_tic_puissance")

    ha = HAClient("http://supervisor/core", "fake_token")
    with patch.object(ha, "states", new=AsyncMock(return_value=fake_states)):
        detected = await discover_entities(ha)

    assert detected.get("linky_power") == "sensor.lixee_zlinky_tic_puissance"


@pytest.mark.asyncio
async def test_discover_entities_maps_zlinky_consommation_to_soutire_total():
    """consommation (EAST cumulatif) -> linky_soutire_total (compteur réseau jour)."""
    from molini_agent.ha_client import HAClient

    fake_states = _live_states(
        "sensor.lixee_zlinky_tic_puissance",
        "sensor.lixee_zlinky_tic_consommation",
    )

    ha = HAClient("http://supervisor/core", "fake_token")
    with patch.object(ha, "states", new=AsyncMock(return_value=fake_states)):
        detected = await discover_entities(ha)

    assert detected.get("linky_power") == "sensor.lixee_zlinky_tic_puissance"
    assert detected.get("linky_soutire_total") == "sensor.lixee_zlinky_tic_consommation"
    assert "molini_soutire_total" in generate_yaml(detected)


@pytest.mark.asyncio
async def test_discover_entities_no_conso_power():
    """discover_entities ne doit jamais émettre un rôle conso_power."""
    from molini_agent.ha_client import HAClient

    # États qui matchaient l'ancien conso_power (sinsts + puissance_soutiree)
    fake_states = _live_states(
        "sensor.zlinky_tic_sinsts",
        "sensor.linky_puissance_soutiree",
        "sensor.shelly_em_power",
    )

    ha = HAClient("http://supervisor/core", "fake_token")
    with patch.object(ha, "states", new=AsyncMock(return_value=fake_states)):
        detected = await discover_entities(ha)

    assert "conso_power" not in detected


# ─── generate_yaml — rôle linky_power → unique_id molini_puissance_soutiree ───

def test_generate_yaml_linky_power_uid():
    """generate_yaml doit émettre unique_id: molini_puissance_soutiree pour linky_power."""
    detected = {"linky_power": "sensor.lixee_zlinky_tic_puissance"}
    yaml_str = generate_yaml(detected)
    assert "molini_puissance_soutiree" in yaml_str


def test_generate_yaml_no_conso_power_sensor():
    """generate_yaml ne doit PAS émettre molini_conso_power_w (rôle supprimé)."""
    # Même si on injectait conso_power dans detected, generate_yaml l'ignore
    detected = {
        "conso_power": "sensor.linky_sinsts",   # rôle inconnu → ignoré
        "linky_power": "sensor.lixee_zlinky_tic_puissance",
    }
    yaml_str = generate_yaml(detected)
    assert "molini_conso_power_w" not in yaml_str
    assert "MOLINI Consommation maison" not in yaml_str  # pas dans le YAML généré


def test_generate_yaml_linky_power_name():
    """generate_yaml doit émettre 'MOLINI Puissance soutirée' pour linky_power."""
    detected = {"linky_power": "sensor.lixee_zlinky_tic_puissance"}
    yaml_str = generate_yaml(detected)
    assert "MOLINI Puissance soutirée" in yaml_str


def test_generate_yaml_empty_detected():
    """generate_yaml sur un dict vide → header seul, aucune section template/switch
    (une liste `template: - sensor:` vide serait invalide côté HA)."""
    yaml_str = generate_yaml({})
    assert "# MOLINI" in yaml_str
    assert "template:" not in yaml_str
    assert "switch:" not in yaml_str
    assert "molini_puissance_soutiree" not in yaml_str


def test_generate_yaml_availability_uses_entity():
    """L'availability du sensor généré référence l'entité détectée."""
    detected = {"linky_power": "sensor.lixee_zlinky_tic_puissance"}
    yaml_str = generate_yaml(detected)
    assert "sensor.lixee_zlinky_tic_puissance" in yaml_str


# ─── Consolidation nommage solaire (FR canonique) ────────────────────────────

def test_solar_power_uid_is_canonical_fr():
    """solar_power → molini_solaire_production (plus de molini_solar_power_w)."""
    detected = {"solar_power": ["sensor.inverter_pv_power", "sensor.izypower_x_puissance_pv"]}
    y = generate_yaml(detected)
    assert "molini_solaire_production" in y
    assert "molini_solar_power_w" not in y
    # somme des onduleurs conservée
    assert "sensor.inverter_pv_power" in y and "sensor.izypower_x_puissance_pv" in y


def test_solar_energy_uids_canonical_fr():
    detected = {
        "solar_energy_today": ["sensor.inverter_today_production"],
        "solar_energy_total": ["sensor.inverter_total_production"],
    }
    y = generate_yaml(detected)
    assert "molini_solaire_production_aujourd_hui" in y
    assert "molini_solaire_production_totale" in y
    assert "molini_solar_energy" not in y


# ─── Pince arrivée générale (Shelly Pro 3EM) — réseau signé ──────────────────

@pytest.mark.asyncio
async def test_discover_grid_power_3em_total_only():
    """Le TOTAL 3EM est mappé grid_power ; les per-phase ne le sont PAS."""
    from molini_agent.ha_client import HAClient
    fake_states = _live_states(
        "sensor.shellypro3em_2805a5c9a094_puissance",
        "sensor.shellypro3em_2805a5c9a094_phase_c_puissance",
        "sensor.shellypro3em_2805a5c9a094_energie",
        "sensor.shellypro3em_2805a5c9a094_energie_restituee",
    )
    ha = HAClient("http://supervisor/core", "fake_token")
    with patch.object(ha, "states", new=AsyncMock(return_value=fake_states)):
        detected = await discover_entities(ha)
    assert detected.get("grid_power") == "sensor.shellypro3em_2805a5c9a094_puissance"
    assert detected.get("grid_import_total") == "sensor.shellypro3em_2805a5c9a094_energie"
    assert detected.get("grid_export_total") == "sensor.shellypro3em_2805a5c9a094_energie_restituee"


def test_generate_yaml_grid_signed_passthrough():
    """molini_reseau (uid==slug) = valeur signée brute du 3EM (pas de max/abs)."""
    detected = {"grid_power": "sensor.shellypro3em_x_puissance"}
    y = generate_yaml(detected)
    assert "unique_id: molini_reseau" in y
    assert "sensor.shellypro3em_x_puissance" in y
    assert "max" not in y and "abs" not in y  # signé, pas tronqué


# ─── Chauffe-eau (Shelly Pro 4PM) — switch alias + capteur puissance ─────────

def _state_attr(entity_id: str, state: str, friendly: str) -> dict:
    return {"entity_id": entity_id, "state": state,
            "attributes": {"friendly_name": friendly}}


@pytest.mark.asyncio
async def test_discover_water_heater_by_friendly_name():
    """Un switch renommé « Chauffe-eau » est détecté même si l'entity_id est générique."""
    from molini_agent.ha_client import HAClient
    fake_states = [
        _state_attr("switch.shellypro4pm_8c4f009059e8_output_0", "on", "Chauffe-eau"),
        _state_attr("switch.shellypro4pm_8c4f009059e8_output_1", "off", "Output 1"),
    ]
    ha = HAClient("http://supervisor/core", "fake_token")
    with patch.object(ha, "states", new=AsyncMock(return_value=fake_states)):
        detected = await discover_entities(ha)
    assert detected.get("water_heater") == "switch.shellypro4pm_8c4f009059e8_output_0"


def test_generate_yaml_water_heater_switch_and_power():
    """Chauffe-eau détecté → switch alias molini_chauffe_eau (format MODERNE,
    rechargeable par template.reload) + capteur puissance dérivé."""
    detected = {"water_heater": "switch.shellypro4pm_8c4f009059e8_output_0"}
    y = generate_yaml(detected)
    # interrupteur template MODERNE (template: - switch:), pas de legacy platform
    assert "  - switch:" in y
    assert "platform: template" not in y
    assert "unique_id: molini_chauffe_eau" in y
    assert "is_state('switch.shellypro4pm_8c4f009059e8_output_0', 'on')" in y
    assert "switch.turn_on" in y and "switch.turn_off" in y
    # capteur puissance dérivé de la sortie Shelly (uid == slug(name))
    assert "sensor.shellypro4pm_8c4f009059e8_output_0_puissance" in y
    assert "name: 'MOLINI Chauffe-eau'" in y  # → switch.molini_chauffe_eau


@pytest.mark.asyncio
async def test_water_heater_only_shelly_outputs(monkeypatch):
    """SÛRETÉ : un switch NON-Shelly (même nommé « chauffe-eau ») n'est jamais
    détecté comme chauffe-eau pilotable — on ne pilote que des sorties Shelly."""
    from molini_agent.ha_client import HAClient
    fake_states = [
        _state_attr("switch.tuya_prise_salon", "on", "Chauffe-eau du salon"),
        _state_attr("light.ballon_deco", "on", "Ballon décoratif"),
    ]
    ha = HAClient("http://supervisor/core", "fake_token")
    with patch.object(ha, "states", new=AsyncMock(return_value=fake_states)):
        detected = await discover_entities(ha)
    assert "water_heater" not in detected


def test_generate_yaml_water_heater_modern_switch_section():
    """generate_yaml émet le switch sous `template: - switch:` (jamais un
    scaffold `- sensor:` vide si aucun capteur)."""
    detected = {"water_heater": "switch.shellypro1pm_abc_output_0"}
    y = generate_yaml(detected)
    assert "template:" in y
    assert "  - switch:" in y
    assert "unique_id: molini_chauffe_eau" in y


# ─── GARDE-FOU : slug(name) == unique_id (HA dérive l'entity_id du NAME) ──────
# Régression 0.18.0 : des capteurs avaient name "MOLINI Réseau" (→ entity_id
# molini_reseau) mais unique_id molini_reseau_w, et les packages/dashboards
# référençaient sensor.molini_reseau_w → entités introuvables. Ce test verrouille
# l'invariant : pour tout capteur/switch émis, slug(name) DOIT == unique_id.
import re as _re
import unicodedata as _ud
from ruamel.yaml import YAML as _YAML
from pathlib import Path as _Path


def _ha_slugify(name: str) -> str:
    s = _ud.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = s.lower()
    s = _re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s


def _iter_named_entities(doc):
    """(name, unique_id) de tous les template sensor/switch d'un doc HA."""
    for item in doc.get("template", []) or []:
        for kind in ("sensor", "switch"):
            for ent in item.get(kind, []) or []:
                if "name" in ent and "unique_id" in ent:
                    yield ent["name"], ent["unique_id"]


def test_generated_discovered_slug_matches_unique_id():
    """Tout capteur/switch de molini_discovered.yaml : slug(name) == unique_id."""
    # ⚠️ fixture EXHAUSTIVE : tous les rôles émis — un rôle absent d'ici
    # échappe au garde-fou (leçon 0.20.0 : linky_ptec/tempo avaient dérivé).
    detected = {
        "linky_power": "sensor.zlinky_puissance",
        "linky_soutire_total": "sensor.zlinky_consommation",
        "linky_hc": "sensor.zlinky_hchc",
        "linky_hp": "sensor.zlinky_hchp",
        "linky_ptec": "sensor.zlinky_ptec",
        "tempo_today": "sensor.rte_tempo_couleur_actuelle",
        "tempo_tomorrow": "sensor.rte_tempo_prochaine_couleur",
        "solar_power": ["sensor.inverter_pv_power"],
        "solar_energy_today": ["sensor.inverter_today_production"],
        "solar_energy_total": ["sensor.inverter_total_production"],
        "grid_power": "sensor.shellypro3em_x_puissance",
        "grid_import_total": "sensor.shellypro3em_x_energie",
        "grid_export_total": "sensor.shellypro3em_x_energie_restituee",
        "water_heater": "switch.shellypro4pm_x_output_0",
    }
    doc = _YAML(typ="safe").load(generate_yaml(detected))
    pairs = list(_iter_named_entities(doc))
    assert pairs, "aucune entité générée"
    assert len(pairs) >= 15, f"fixture incomplète ? {len(pairs)} entités"
    for name, uid in pairs:
        assert _ha_slugify(name) == uid, (
            f"slug({name!r})={_ha_slugify(name)!r} != unique_id {uid!r} "
            f"→ entity_id ne matchera pas les références packages/dashboard"
        )


def test_package_molini_energy_slug_matches_unique_id():
    """Idem pour les capteurs template du package de base molini_energy.yaml."""
    pkg = (
        _Path(__file__).resolve().parents[1]
        / "rootfs/usr/share/molini/packages/molini_energy.yaml"
    )
    doc = _YAML(typ="safe").load(pkg.read_text(encoding="utf-8"))
    for name, uid in _iter_named_entities(doc):
        assert _ha_slugify(name) == uid, (
            f"molini_energy.yaml : slug({name!r})={_ha_slugify(name)!r} != {uid!r}"
        )


def _all_unique_ids(doc):
    ids = []
    for item in doc.get("template", []) or []:
        for kind in ("sensor", "switch"):
            for ent in item.get(kind, []) or []:
                if "unique_id" in ent:
                    ids.append(ent["unique_id"])
    return ids


def test_no_duplicate_unique_ids_discovered_and_package():
    """GARDE-FOU : aucun unique_id dupliqué à travers discovered + package.
    Régression 0.18.1 : le capteur puissance chauffe-eau ET le switch avaient
    tous deux uid molini_chauffe_eau (même plateforme template) → collision →
    entités _2 en cascade."""
    detected = {
        "linky_power": "sensor.zlinky_puissance",
        "linky_soutire_total": "sensor.zlinky_consommation",
        "solar_power": ["sensor.inverter_pv_power"],
        "grid_power": "sensor.shellypro3em_x_puissance",
        "grid_import_total": "sensor.shellypro3em_x_energie",
        "grid_export_total": "sensor.shellypro3em_x_energie_restituee",
        "water_heater": "switch.shellypro4pm_x_output_0",
    }
    disc = _YAML(typ="safe").load(generate_yaml(detected))
    pkg = _YAML(typ="safe").load(
        (_Path(__file__).resolve().parents[1]
         / "rootfs/usr/share/molini/packages/molini_energy.yaml").read_text(encoding="utf-8")
    )
    ids = _all_unique_ids(disc) + _all_unique_ids(pkg)
    dups = {u for u in ids if ids.count(u) > 1}
    assert not dups, f"unique_id dupliqués (collision registre HA) : {dups}"


@pytest.mark.asyncio
async def test_multi_sum_keeps_sleeping_inverters():
    """Post-mortem 2026-07-06 : une provision NOCTURNE ne doit pas perdre les
    onduleurs endormis (unavailable) sur les rôles sommés — sinon la prod du
    référentiel est divisée jusqu'à la provision de jour suivante."""
    from molini_agent.ha_client import HAClient
    fake_states = [
        _state("sensor.inverter_pv_power", "unavailable"),
        _state("sensor.inverter_2_pv_power", "unavailable"),
        _state("sensor.izypower_x_puissance_pv", "0"),
        _state("sensor.lixee_zlinky_tic_puissance", "300"),
    ]
    ha = HAClient("http://supervisor/core", "fake_token")
    with patch.object(ha, "states", new=AsyncMock(return_value=fake_states)):
        detected = await discover_entities(ha)
    assert set(detected["solar_power"]) == {
        "sensor.inverter_pv_power", "sensor.inverter_2_pv_power",
        "sensor.izypower_x_puissance_pv",
    }
    # les rôles NON sommés gardent l'exigence « vivant »
    assert detected.get("linky_power") == "sensor.lixee_zlinky_tic_puissance"
