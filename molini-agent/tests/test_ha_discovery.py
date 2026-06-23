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
    """generate_yaml sur un dict vide doit retourner le header sans sensors."""
    yaml_str = generate_yaml({})
    assert "template:" in yaml_str
    assert "molini_puissance_soutiree" not in yaml_str


def test_generate_yaml_availability_uses_entity():
    """L'availability du sensor généré référence l'entité détectée."""
    detected = {"linky_power": "sensor.lixee_zlinky_tic_puissance"}
    yaml_str = generate_yaml(detected)
    assert "sensor.lixee_zlinky_tic_puissance" in yaml_str
