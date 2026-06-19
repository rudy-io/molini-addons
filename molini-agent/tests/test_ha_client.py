# molini-agent/tests/test_ha_client.py
"""Tests unitaires pour HAClient — en particulier sensor_max_over."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─── sensor_max_over ──────────────────────────────────────────────────────────

def _make_history_payload() -> list:
    """Payload d'historique factice au format API HA (liste de listes de points)."""
    return [
        [
            {"entity_id": "sensor.inverter_pv1_power", "state": "unknown", "last_changed": "..."},
            {"entity_id": "sensor.inverter_pv1_power", "state": "350", "last_changed": "..."},
            {"entity_id": "sensor.inverter_pv1_power", "state": "420", "last_changed": "..."},
            {"entity_id": "sensor.inverter_pv1_power", "state": "unavailable", "last_changed": "..."},
        ],
        [
            {"entity_id": "sensor.inverter_pv2_power", "state": "200"},
            {"entity_id": "sensor.inverter_pv2_power", "state": "210"},
        ],
        [],  # série vide → skip
        [
            {},  # pas d'entity_id → skip
        ],
    ]


@pytest.mark.asyncio
async def test_sensor_max_over_parses_history():
    """sensor_max_over extrait le max par entité en ignorant 'unknown'/'unavailable'."""
    from molini_agent.ha_client import HAClient

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = _make_history_payload()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=fake_response)
        mock_client_cls.return_value = mock_client
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        ha = HAClient("http://supervisor/core", "fake_token")
        # On remplace directement le client interne
        ha._client = mock_client

        result = await ha.sensor_max_over(
            ["sensor.inverter_pv1_power", "sensor.inverter_pv2_power"],
            days=14,
        )

    assert result["sensor.inverter_pv1_power"] == 420.0
    assert result["sensor.inverter_pv2_power"] == 210.0


@pytest.mark.asyncio
async def test_sensor_max_over_empty_list():
    """Appel sans entity_ids → retourne {} sans requête réseau."""
    from molini_agent.ha_client import HAClient

    ha = HAClient("http://supervisor/core", "fake_token")
    result = await ha.sensor_max_over([])
    assert result == {}


@pytest.mark.asyncio
async def test_sensor_max_over_non_200_returns_empty():
    """En cas de réponse non-200, renvoie {} sans lever."""
    from molini_agent.ha_client import HAClient

    fake_response = MagicMock()
    fake_response.status_code = 500

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=fake_response)
        mock_client_cls.return_value = mock_client

        ha = HAClient("http://supervisor/core", "fake_token")
        ha._client = mock_client

        result = await ha.sensor_max_over(["sensor.foo"], days=14)

    assert result == {}
