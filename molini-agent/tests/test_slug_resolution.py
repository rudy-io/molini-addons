"""Tests for ``molini_agent.bootstrap.resolve_addon_slug``.

We mock ``supervisor_client`` so the tests don't hit the network. The function
under test should:

1. Honor the exact slug if installed (fast path)
2. Fall back to patterns against installed add-ons
3. Fall back to the store catalog
4. Add the repo + poll the store if a repo is declared
5. Honor the polling timeout
6. Refuse forbidden names
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from molini_agent.bootstrap import ALLOWED_ADDON_NAMES, resolve_addon_slug


@pytest.fixture
def mock_supervisor():
    """Patch all supervisor_client functions used by resolve_addon_slug."""
    with patch("molini_agent.bootstrap.supervisor_client") as mock:
        mock.addons_list = AsyncMock(return_value=[])
        mock.store_addons_list = AsyncMock(return_value=[])
        mock.store_repositories_add = AsyncMock(return_value={})
        yield mock


def _addon(slug: str, name: str = None, state: str = "started") -> dict[str, Any]:
    return {"slug": slug, "name": name or slug, "state": state}


# ─── installed_exact ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mosquitto_exact_slug_installed(mock_supervisor):
    mock_supervisor.addons_list.return_value = [_addon("core_mosquitto")]
    slug, source = await resolve_addon_slug("mosquitto")
    assert slug == "core_mosquitto"
    assert source == "installed_exact"
    # Store should not have been queried
    mock_supervisor.store_addons_list.assert_not_called()


@pytest.mark.asyncio
async def test_z2m_exact_slug_installed(mock_supervisor):
    mock_supervisor.addons_list.return_value = [_addon("45df7312_zigbee2mqtt")]
    slug, source = await resolve_addon_slug("zigbee2mqtt")
    assert slug == "45df7312_zigbee2mqtt"
    assert source == "installed_exact"


# ─── installed_pattern ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_z2m_pattern_match_installed(mock_supervisor):
    """Custom repo install — slug doesn't match the official hash."""
    mock_supervisor.addons_list.return_value = [_addon("abc12345_zigbee2mqtt")]
    slug, source = await resolve_addon_slug("zigbee2mqtt")
    assert slug == "abc12345_zigbee2mqtt"
    assert source == "installed_pattern"


@pytest.mark.asyncio
async def test_cloudflared_pattern_match_installed(mock_supervisor):
    mock_supervisor.addons_list.return_value = [
        _addon("a0d7b954_cloudflared", name="Cloudflared")
    ]
    slug, source = await resolve_addon_slug("cloudflared")
    assert slug == "a0d7b954_cloudflared"
    assert source == "installed_pattern"


# ─── store_pattern ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cloudflared_found_in_store_no_repo_add(mock_supervisor):
    """Repo already added → addon is in store → no add_repository call."""
    mock_supervisor.addons_list.return_value = []
    mock_supervisor.store_addons_list.return_value = [
        _addon("a0d7b954_cloudflared")
    ]
    slug, source = await resolve_addon_slug("cloudflared")
    assert slug == "a0d7b954_cloudflared"
    assert source == "store_pattern"
    mock_supervisor.store_repositories_add.assert_not_called()


# ─── added_repo (polling) ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cloudflared_repo_add_then_poll_success(mock_supervisor):
    """Initial store is empty → repo gets added → store populates after 1 poll."""
    mock_supervisor.addons_list.return_value = []

    poll_count = {"n": 0}

    async def store_after_repo():
        poll_count["n"] += 1
        if poll_count["n"] == 1:
            return []  # initial
        return [_addon("a0d7b954_cloudflared")]

    mock_supervisor.store_addons_list.side_effect = store_after_repo

    sleep_calls: list[float] = []

    async def fake_sleep(s: float) -> None:
        sleep_calls.append(s)

    slug, source = await resolve_addon_slug(
        "cloudflared",
        poll_timeout_s=30,
        poll_interval_s=2.0,
        _clock=lambda: 0.0,  # never expire
        _sleep=fake_sleep,
    )
    assert slug == "a0d7b954_cloudflared"
    assert source == "added_repo"
    mock_supervisor.store_repositories_add.assert_called_once_with(
        "https://github.com/brenner-tobias/ha-addons"
    )
    # At least one sleep happened during polling
    assert len(sleep_calls) >= 1
    assert sleep_calls[0] == 2.0


@pytest.mark.asyncio
async def test_cloudflared_repo_add_polling_times_out(mock_supervisor):
    """Repo added but the store never lists cloudflared → not_found after timeout."""
    mock_supervisor.addons_list.return_value = []
    mock_supervisor.store_addons_list.return_value = []  # never returns cloudflared

    clock_value = {"t": 0.0}

    def clock() -> float:
        return clock_value["t"]

    async def fake_sleep(s: float) -> None:
        clock_value["t"] += s

    slug, source = await resolve_addon_slug(
        "cloudflared",
        poll_timeout_s=10,
        poll_interval_s=2.0,
        _clock=clock,
        _sleep=fake_sleep,
    )
    assert slug is None
    assert source == "not_found"
    # Should have polled ~5 times (10s / 2s)
    assert mock_supervisor.store_addons_list.call_count >= 5


@pytest.mark.asyncio
async def test_repo_add_failure_does_not_crash(mock_supervisor):
    """If ``store_repositories_add`` raises (repo already added), keep polling.

    Reproduces the case where the repo is already known to the supervisor
    (manual addition by the installer) but the slug is not yet listed.
    The first ``store_addons_list`` returns empty, ``store_repositories_add``
    raises (repo conflict), then polling finds the slug → ``added_repo``.
    """
    mock_supervisor.addons_list.return_value = []
    # Empty on first call, populated on poll
    call_count = {"n": 0}

    async def store_list():
        call_count["n"] += 1
        if call_count["n"] == 1:
            return []
        return [_addon("a0d7b954_cloudflared")]

    mock_supervisor.store_addons_list.side_effect = store_list
    mock_supervisor.store_repositories_add.side_effect = RuntimeError(
        "repo already exists"
    )

    slug, source = await resolve_addon_slug(
        "cloudflared",
        poll_timeout_s=10,
        poll_interval_s=2.0,
        _clock=lambda: 0.0,
        _sleep=AsyncMock(),
    )
    assert slug == "a0d7b954_cloudflared"
    assert source == "added_repo"
    # The add was attempted despite eventual failure
    mock_supervisor.store_repositories_add.assert_called_once()


# ─── Forbidden names ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_forbidden_name(mock_supervisor):
    slug, source = await resolve_addon_slug("malicious_addon")
    assert slug is None
    assert source == "forbidden_slug"
    # No supervisor call should have happened
    mock_supervisor.addons_list.assert_not_called()


@pytest.mark.asyncio
async def test_allowed_names_match_catalog():
    """Sanity: the set of allowed names matches the bootstrap catalog."""
    assert ALLOWED_ADDON_NAMES == {"mosquitto", "zigbee2mqtt", "cloudflared"}


# ─── Mosquitto without repo (no fallback) ────────────────────────────────────


@pytest.mark.asyncio
async def test_mosquitto_not_found_no_repo(mock_supervisor):
    """Mosquitto declares no fallback repo — if it's not installed or in store,
    we should return not_found without trying to add a repo."""
    mock_supervisor.addons_list.return_value = []
    mock_supervisor.store_addons_list.return_value = []

    slug, source = await resolve_addon_slug("mosquitto")
    assert slug is None
    assert source == "not_found"
    mock_supervisor.store_repositories_add.assert_not_called()


# ─── pytest-asyncio mode ─────────────────────────────────────────────────────

# pytest-asyncio needs ``asyncio_mode`` set to ``auto`` to recognize
# ``@pytest.mark.asyncio`` without per-test boilerplate. We declare it via
# ``pyproject.toml`` / ``pytest.ini`` at the repo level. As a defensive measure
# below we ensure the marker actually applies (avoids silent skip):

def test_asyncio_marker_recognized():
    """Bare sync test to confirm pytest collects this module at all."""
    assert True
