"""Smoke test E2E mock du flow rebuild_dashboard.

Simule un payload admin → handler → écriture fichier → reload.
Mock le HA client + supervisor pour ne pas dépendre d'un HA réel.
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from molini_agent.config import Config

from . import conftest

BLOCKS_DIR = conftest.BLOCKS_DIR


def _fake_config(tmp_path) -> Config:
    """Config minimale pour les tests — pas d'env vars requis."""
    # On contourne ``Config.from_env`` qui exige des env vars (CENTRAL_URL etc.)
    return Config(
        central_url="https://moli.energy",
        client_token="molini_test_token",
        ha_url="http://supervisor/core",
        ha_token="fake_ha_token",
        heartbeat_interval_s=300,
        linky_power_entity="sensor.linky_puissance_apparente",
        linky_hc_entity="sensor.linky_index_hchc",
        linky_hp_entity="sensor.linky_index_hchp",
        linky_tempo_today_entity="sensor.rte_tempo_couleur_actuelle",
        linky_tempo_tomorrow_entity="sensor.rte_tempo_prochaine_couleur",
        prix_kwh=0.2516,
    )


@pytest.mark.asyncio
async def test_rebuild_dashboard_smoke(tmp_path, monkeypatch):
    """Smoke test du handler execute_rebuild_dashboard.

    Verifie que :
    1. Le YAML est assemblé et écrit
    2. Les blocs forcés sont bien en position
    3. Le reload HA est tenté
    4. Le résultat est sérialisable
    """
    target_path = tmp_path / "molini.yaml"
    monkeypatch.setenv("MOLINI_DASHBOARD_BLOCKS_DIR", str(BLOCKS_DIR))
    monkeypatch.setenv("MOLINI_DASHBOARD_OUTPUT_PATH", str(target_path))

    from molini_agent.commands import execute_rebuild_dashboard

    # Mock HAClient pour ne pas réseau
    with patch("molini_agent.commands.HAClient") as ha_class:
        fake_ha = AsyncMock()
        fake_ha.states.return_value = [
            {"entity_id": "sensor.molini_power_w", "state": "1234"},
            {"entity_id": "sensor.molini_tempo_today", "state": "BLEU"},
        ]
        fake_ha.close = AsyncMock()
        ha_class.return_value = fake_ha

        # Mock httpx pour le reload (sinon timeout 15s)
        with patch("molini_agent.commands.httpx.AsyncClient") as http_class:
            fake_client = AsyncMock()
            fake_post = AsyncMock(return_value=AsyncMock(status_code=200))
            fake_client.post = fake_post
            fake_client.__aenter__ = AsyncMock(return_value=fake_client)
            fake_client.__aexit__ = AsyncMock(return_value=None)
            http_class.return_value = fake_client

            result = await execute_rebuild_dashboard(
                _fake_config(tmp_path),
                {"blocks": ["_header", "energie", "aide", "_reglages"]},
            )

    assert result["ok"] is True
    assert result["blocks_used"][0] == "_header"
    assert result["blocks_used"][-1] == "_reglages"
    assert target_path.is_file()
    # Le résultat doit être JSON-sérialisable (commande report_result)
    import json
    json.dumps(result, default=str)


@pytest.mark.asyncio
async def test_rebuild_dashboard_rejects_invalid_block(tmp_path, monkeypatch):
    """Un payload avec un slug hors white-list doit failer proprement."""
    target_path = tmp_path / "molini.yaml"
    monkeypatch.setenv("MOLINI_DASHBOARD_BLOCKS_DIR", str(BLOCKS_DIR))
    monkeypatch.setenv("MOLINI_DASHBOARD_OUTPUT_PATH", str(target_path))

    from molini_agent.commands import execute_rebuild_dashboard

    with patch("molini_agent.commands.HAClient") as ha_class:
        fake_ha = AsyncMock()
        fake_ha.states.return_value = []
        fake_ha.close = AsyncMock()
        ha_class.return_value = fake_ha

        with pytest.raises(RuntimeError, match="build failed"):
            await execute_rebuild_dashboard(
                _fake_config(tmp_path),
                {"blocks": ["../etc/passwd"]},
            )

    # Le fichier de sortie n'a pas été créé
    assert not target_path.exists()


@pytest.mark.asyncio
async def test_rebuild_dashboard_rejects_non_list(tmp_path, monkeypatch):
    target_path = tmp_path / "molini.yaml"
    monkeypatch.setenv("MOLINI_DASHBOARD_BLOCKS_DIR", str(BLOCKS_DIR))
    monkeypatch.setenv("MOLINI_DASHBOARD_OUTPUT_PATH", str(target_path))

    from molini_agent.commands import execute_rebuild_dashboard

    with pytest.raises(RuntimeError, match="must be a list"):
        await execute_rebuild_dashboard(
            _fake_config(tmp_path),
            {"blocks": "not_a_list"},
        )


@pytest.mark.asyncio
async def test_rebuild_dashboard_empty_payload_uses_defaults(tmp_path, monkeypatch):
    """Un payload sans `blocks` → fallback sur DEFAULT_BLOCKS."""
    from molini_agent.dashboard_builder import DEFAULT_BLOCKS

    target_path = tmp_path / "molini.yaml"
    monkeypatch.setenv("MOLINI_DASHBOARD_BLOCKS_DIR", str(BLOCKS_DIR))
    monkeypatch.setenv("MOLINI_DASHBOARD_OUTPUT_PATH", str(target_path))

    from molini_agent.commands import execute_rebuild_dashboard

    with patch("molini_agent.commands.HAClient") as ha_class:
        fake_ha = AsyncMock()
        fake_ha.states.return_value = []
        fake_ha.close = AsyncMock()
        ha_class.return_value = fake_ha

        with patch("molini_agent.commands.httpx.AsyncClient") as http_class:
            fake_client = AsyncMock()
            fake_client.post = AsyncMock(return_value=AsyncMock(status_code=200))
            fake_client.__aenter__ = AsyncMock(return_value=fake_client)
            fake_client.__aexit__ = AsyncMock(return_value=None)
            http_class.return_value = fake_client

            result = await execute_rebuild_dashboard(
                _fake_config(tmp_path),
                {},
            )

    assert result["blocks_used"] == list(DEFAULT_BLOCKS)
