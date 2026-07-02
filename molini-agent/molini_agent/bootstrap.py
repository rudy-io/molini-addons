"""Agent-first bootstrap — installs the full Moli stack on a freshly onboarded
Home Assistant OS box.

Goal: replace the ~3h of manual friction documented during the Carole pilot
(2026-05-25) with a single ``bootstrap_stack`` command. The installer only has
to (a) power the box, (b) finish the HA onboarding, (c) install the Moli Agent
add-on with a client token. Then the agent provisions everything else.

What this module does:

1. Detects which add-ons are already installed (via supervisor ``/addons``)
2. For each required slug, takes one of the following actions:
   - ``skipped``  — already installed (and not asked to restart)
   - ``started``  — installed but stopped, started now
   - ``installed`` — newly installed (and started)
   - ``failed``   — error path, full traceback in the report
3. Patches ``/config/configuration.yaml`` with the Moli defaults:
   - ``http.trusted_proxies: [172.30.0.0/16]`` (HA supervisor internal range)
   - ``http.use_x_forwarded_for: true``
   - ``recorder.purge_keep_days: 14`` (HA Green eMMC budget)
4. Returns a structured report (``{actions, ha_restart_pending, errors}``)
   so the central admin UI can render a wizard checklist.

**Idempotent**: running ``bootstrap_stack`` twice is safe and only acts on
what is actually missing/misconfigured.

Slug resolution:
- Mosquitto is always ``core_mosquitto`` (official HA add-on).
- Z2M default slug is ``45df7312_zigbee2mqtt`` (official HA add-on repo hash),
  fallback by pattern ``*_zigbee2mqtt``.
- Cloudflared (Tobi's repo) is not in the default HA store. We add the repo,
  poll ``/store/addons`` every 2s for up to 60s, then resolve by pattern.

Security: this module never executes shell commands; it talks exclusively to
the supervisor REST API. The ``patch_ha_config`` path goes through
``yaml_patch.PATCHABLE_TOP_KEYS`` white-list — see that module for details.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from typing import Any, Optional

from . import supervisor_client
from .config import Config
from .ha_client import HAClient
from .moli_config import ensure_moli_ha_config, moli_config_present
from .yaml_patch import YamlPatchError, apply_patch_to_file
from .zigbee import detect_zigbee_stack, guard_payload, zigbee_stack_from_states

log = logging.getLogger("molini_agent.bootstrap")


# ─── Add-on catalog (whitelisted) ─────────────────────────────────────────────
# Mapping from a Moli-internal short name to:
#   - ``slug``           : exact slug to try first (None = pattern only)
#   - ``slug_patterns``  : compiled regexes to resolve when the exact slug is absent
#   - ``repo``           : optional repository URL to add to the supervisor store
#                          if no candidate is found in the current installation
#   - ``description``    : human-readable label (used in the report only)
#
# **Security**: only entries from this catalog can be passed to ``install_addon``.
# Anything else is rejected with ``forbidden_slug``.
ADDON_CATALOG: dict[str, dict[str, Any]] = {
    "mosquitto": {
        "slug": "core_mosquitto",
        "slug_patterns": [r"^core_mosquitto$", r".*_mosquitto$"],
        "repo": None,
        "description": "Mosquitto MQTT broker (official HA add-on)",
    },
    "zigbee2mqtt": {
        # 45df7312 = official HA add-ons repository hash
        "slug": "45df7312_zigbee2mqtt",
        "slug_patterns": [r"^45df7312_zigbee2mqtt$", r".*_zigbee2mqtt$"],
        "repo": None,
        "description": "Zigbee2MQTT (official community add-on)",
    },
    "cloudflared": {
        "slug": None,
        "slug_patterns": [r".*_cloudflared$", r"^cloudflared$"],
        "repo": "https://github.com/brenner-tobias/ha-addons",
        "description": "Cloudflare Tunnel (Tobi's community add-on)",
    },
}

ALLOWED_ADDON_NAMES: frozenset[str] = frozenset(ADDON_CATALOG.keys())


# ─── Moli HA configuration patch ──────────────────────────────────────────────
# The HA supervisor's bridge subnet, allowed to set X-Forwarded-For on the
# requests it proxies to HA Core (notably from the Moli Agent add-on, but also
# from any ingress add-on like cloudflared).
HA_SUPERVISOR_CIDR = "172.30.0.0/16"

MOLI_HA_CONFIG_PATCH: dict[str, Any] = {
    "http": {
        "use_x_forwarded_for": True,
        "trusted_proxies": [HA_SUPERVISOR_CIDR],
    },
    "recorder": {
        "purge_keep_days": 14,
    },
    # Charge nos cartes Lovelace custom (button-card, apexcharts, kiosk-mode) —
    # déposées par le run dans /config/www/moli-cards. frontend est patchable ;
    # extra_module_url est une liste → merge par union (idempotent).
    # kiosk-mode masque la sidebar HA pour les non-admins (mode appliance Moli).
    "frontend": {
        "extra_module_url": [
            "/local/moli-cards/button-card.js",
            "/local/moli-cards/apexcharts-card.js",
            "/local/moli-cards/kiosk-mode.js",
        ],
        # Thème Moli — fond navy de marque, accents vert/ambre, cartes
        # arrondies. Appliqué par vue via `theme: Moli` dans les blocs.
        "themes": {
            "Moli": {
                "primary-color": "#1d9e75",
                "accent-color": "#f5a623",
                "app-header-background-color": "#0E2238",
                "app-header-text-color": "#e8eef2",
                "primary-background-color": "#0b1a2c",
                "secondary-background-color": "#0E2238",
                "divider-color": "rgba(255,255,255,0.08)",
                "card-background-color": "#10243a",
                "ha-card-background": "#10243a",
                "ha-card-border-radius": "16px",
                "ha-card-box-shadow": "0 2px 12px rgba(0,0,0,0.35)",
                "primary-text-color": "#e8eef2",
                "secondary-text-color": "#9fb2c0",
                "state-icon-color": "#1d9e75",
                "paper-item-icon-color": "#9fb2c0",
            },
        },
    },
}


# ─── Polling helpers ─────────────────────────────────────────────────────────
# Used after adding a repo: the supervisor refreshes the store asynchronously.
DEFAULT_POLL_TIMEOUT_S = 60
DEFAULT_POLL_INTERVAL_S = 2.0


# ─── Slug resolution ─────────────────────────────────────────────────────────

async def _find_slug_in_installed(
    addons: list[dict[str, Any]], patterns: list[re.Pattern[str]]
) -> Optional[str]:
    """Return the first installed add-on slug matching any pattern, if any."""
    for a in addons:
        slug = a.get("slug") or ""
        for rx in patterns:
            if rx.match(slug):
                return slug
    return None


async def _find_slug_in_store(
    store_addons: list[dict[str, Any]], patterns: list[re.Pattern[str]]
) -> Optional[str]:
    """Return the first store add-on slug matching any pattern, if any."""
    for a in store_addons:
        slug = a.get("slug") or ""
        for rx in patterns:
            if rx.match(slug):
                return slug
    return None


async def _store_addons() -> list[dict[str, Any]]:
    """Fetch the supervisor store catalog. Best-effort: returns [] on error."""
    try:
        data = await supervisor_client.store_addons_list()
        return data or []
    except Exception as e:
        log.warning("bootstrap: store_addons_list failed: %s", e)
        return []


async def resolve_addon_slug(
    name: str,
    *,
    poll_timeout_s: int = DEFAULT_POLL_TIMEOUT_S,
    poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
    _clock: Any = time.monotonic,
    _sleep: Any = asyncio.sleep,
) -> tuple[Optional[str], str]:
    """Resolve the actual slug for a catalog entry.

    Returns ``(slug, source)`` where ``source`` is one of:
    ``"installed_exact"``, ``"installed_pattern"``, ``"store_pattern"``,
    ``"added_repo"``, ``"not_found"``.

    Strategy:
    1. Try the exact slug against installed add-ons.
    2. Try patterns against installed add-ons.
    3. Try patterns against the store.
    4. If a repo is declared and the slug is still missing, add the repo
       and poll the store for up to ``poll_timeout_s`` seconds.
    """
    if name not in ADDON_CATALOG:
        return None, "forbidden_slug"

    entry = ADDON_CATALOG[name]
    exact_slug = entry.get("slug")
    patterns = [
        re.compile(p, re.IGNORECASE) for p in entry.get("slug_patterns") or []
    ]

    installed = await supervisor_client.addons_list()
    if exact_slug:
        if any((a.get("slug") == exact_slug) for a in installed):
            return exact_slug, "installed_exact"

    found = await _find_slug_in_installed(installed, patterns)
    if found:
        return found, "installed_pattern"

    store = await _store_addons()
    found = await _find_slug_in_store(store, patterns)
    if found:
        return found, "store_pattern"

    repo = entry.get("repo")
    if not repo:
        return None, "not_found"

    log.info("bootstrap: adding repo %s for %s", repo, name)
    try:
        await supervisor_client.store_repositories_add(repo)
    except Exception as e:
        log.warning("bootstrap: store_repositories_add(%s) → %s", repo, e)
        # The repo might already be added — keep polling regardless

    deadline = _clock() + poll_timeout_s
    while _clock() < deadline:
        await _sleep(poll_interval_s)
        store = await _store_addons()
        found = await _find_slug_in_store(store, patterns)
        if found:
            return found, "added_repo"
    return None, "not_found"


# ─── Per-addon install logic ─────────────────────────────────────────────────

async def install_or_start_addon(
    name: str,
    *,
    options: Optional[dict[str, Any]] = None,
    start: bool = True,
    poll_timeout_s: int = DEFAULT_POLL_TIMEOUT_S,
) -> dict[str, Any]:
    """Idempotent install + optional start for a single add-on.

    Returns a structured action report::

        {
          "name": "mosquitto",
          "slug": "core_mosquitto",
          "status": "skipped" | "started" | "installed" | "failed",
          "source": "installed_exact" | ... ,
          "options_applied": False,
          "error": None | str,
        }
    """
    if name not in ALLOWED_ADDON_NAMES:
        return {
            "name": name,
            "slug": None,
            "status": "failed",
            "source": "forbidden_slug",
            "options_applied": False,
            "error": f"forbidden_addon:{name}",
        }

    slug, source = await resolve_addon_slug(name, poll_timeout_s=poll_timeout_s)
    if not slug:
        return {
            "name": name,
            "slug": None,
            "status": "failed",
            "source": source,
            "options_applied": False,
            "error": f"slug_not_resolved:{name}",
        }

    try:
        info = await supervisor_client.addon_info(slug)
    except Exception as e:
        # ``info`` can be missing if the add-on is in store but not installed
        log.info("bootstrap: addon_info(%s) failed → %s", slug, e)
        info = {}

    # Le Supervisor expose la version installée sous ``version`` (et non
    # ``version_installed``). De plus, ``resolve_addon_slug`` a déjà confirmé la
    # présence quand l'add-on figurait dans /addons (source "installed_*"). Sans
    # ce double check, un add-on déjà installé repartait en addon_install → 400
    # "already_installed" → faux "failed" dans le wizard.
    is_installed = source.startswith("installed") or bool(
        info.get("version") or info.get("version_installed") or info.get("installed")
    )
    current_state = info.get("state", "unknown")

    options_applied = False
    if not is_installed:
        try:
            await supervisor_client.addon_install(slug)
        except Exception as e:
            return {
                "name": name,
                "slug": slug,
                "status": "failed",
                "source": source,
                "options_applied": False,
                "error": f"install_failed:{e}",
            }
        if options:
            try:
                await supervisor_client.addon_options(slug, options)
                options_applied = True
            except Exception as e:
                log.warning("bootstrap: addon_options(%s) failed: %s", slug, e)
        if start:
            try:
                await supervisor_client.addon_start(slug)
            except Exception as e:
                return {
                    "name": name,
                    "slug": slug,
                    "status": "failed",
                    "source": source,
                    "options_applied": options_applied,
                    "error": f"start_after_install_failed:{e}",
                }
        return {
            "name": name,
            "slug": slug,
            "status": "installed",
            "source": source,
            "options_applied": options_applied,
            "error": None,
        }

    # Already installed
    if options:
        try:
            await supervisor_client.addon_options(slug, options)
            options_applied = True
        except Exception as e:
            log.warning("bootstrap: addon_options(%s) failed: %s", slug, e)

    if start and current_state != "started":
        try:
            await supervisor_client.addon_start(slug)
            return {
                "name": name,
                "slug": slug,
                "status": "started",
                "source": source,
                "options_applied": options_applied,
                "error": None,
            }
        except Exception as e:
            return {
                "name": name,
                "slug": slug,
                "status": "failed",
                "source": source,
                "options_applied": options_applied,
                "error": f"start_failed:{e}",
            }

    return {
        "name": name,
        "slug": slug,
        "status": "skipped",
        "source": source,
        "options_applied": options_applied,
        "error": None,
    }


# ─── HA config patch ─────────────────────────────────────────────────────────

def patch_ha_config(
    patch: dict[str, Any],
    *,
    config_path: Optional[str] = None,
) -> dict[str, Any]:
    """Apply a (white-listed) patch to the HA ``configuration.yaml``.

    Returns a JSON-friendly report. Raises ``YamlPatchError`` on policy
    violations (forbidden top-level keys). Filesystem / parse errors are
    captured in the report so the central can render a UI message.
    """
    target = config_path or os.environ.get("HA_CONFIG_PATH") or "/config/configuration.yaml"

    try:
        report = apply_patch_to_file(target, patch)
        return {"ok": True, **report}
    except YamlPatchError as e:
        log.warning("bootstrap: yaml policy violation: %s", e)
        return {"ok": False, "path": target, "error": str(e)}
    except OSError as e:
        log.warning("bootstrap: yaml write error: %s", e)
        return {"ok": False, "path": target, "error": f"io_error:{e}"}


# ─── Top-level orchestrator ──────────────────────────────────────────────────

async def bootstrap_stack(
    cfg: Config,
    *,
    payload: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Provision the full Moli stack. Safe to call repeatedly.

    Returns::

        {
          "ok": True | False,
          "actions": [<install_or_start_addon result>, ...],
          "ha_config_patch": <patch_ha_config result>,
          "ha_restart_pending": True | False,
          "errors": [<short error strings>],
          "summary": "X installed, Y started, Z skipped, W failed",
        }
    """
    payload = payload or {}

    # Allow caller to limit which addons we touch (advanced UI use-case).
    requested: list[str] = list(payload.get("addons") or list(ALLOWED_ADDON_NAMES))
    requested = [a for a in requested if a in ALLOWED_ADDON_NAMES]
    # Preserve install order: broker first, then z2m (depends on mqtt), then tunnel
    order = ["mosquitto", "zigbee2mqtt", "cloudflared"]
    requested.sort(key=lambda x: order.index(x) if x in order else 99)

    actions: list[dict[str, Any]] = []
    errors: list[str] = []

    # Garde-fou Zigbee : ne JAMAIS poser Z2M sur une box déjà en ZHA (conflit
    # de coordinateur — cas Carole, ZBT-2). Détection best-effort ; ``unknown``
    # = fail-open (une sonde qui rate ne doit pas bloquer une install saine).
    # Override explicite : payload {"force_z2m": true} (migration assumée).
    if "zigbee2mqtt" in requested and not payload.get("force_z2m"):
        ha = (
            HAClient(cfg.ha_url, cfg.ha_token)
            if getattr(cfg, "ha_url", None) and getattr(cfg, "ha_token", None)
            else None
        )
        try:
            stack = await detect_zigbee_stack(ha)
        finally:
            if ha is not None:
                await ha.close()
        if stack in ("zha", "both"):
            requested.remove("zigbee2mqtt")
            actions.append(guard_payload(stack))
            log.warning(
                "bootstrap: zigbee2mqtt skipped — box en ZHA (stack=%s)", stack
            )

    for name in requested:
        log.info("bootstrap: handling add-on %s", name)
        # Cloudflared is special — we don't start it here without a token.
        # It will be started by ``tunnel_install`` once the central pushes the
        # token. So we install but don't start.
        start_now = name != "cloudflared"
        result = await install_or_start_addon(name, start=start_now)
        actions.append(result)
        if result["status"] == "failed":
            errors.append(f"{name}:{result['error']}")

    # HA config patch (always applied if not skipped via payload)
    skip_yaml = bool(payload.get("skip_ha_config"))
    if skip_yaml:
        config_patch_result: dict[str, Any] = {
            "ok": True,
            "skipped": True,
            "reason": "skip_ha_config_in_payload",
        }
    else:
        # We allow the caller to inject extra patch keys via payload, but they
        # are still validated by ``yaml_patch.PATCHABLE_TOP_KEYS``.
        extra_patch = payload.get("ha_config_extra") or {}
        if not isinstance(extra_patch, dict):
            extra_patch = {}
        # Defensive copy so callers can't reuse mutable state
        full_patch = {**MOLI_HA_CONFIG_PATCH, **extra_patch}
        config_patch_result = patch_ha_config(full_patch)
        if not config_patch_result.get("ok"):
            errors.append(f"ha_config:{config_patch_result.get('error')}")

    # Pose des blocs Moli (homeassistant.packages + lovelace dashboard) —
    # mécanisme dédié hors white-list patch : contenu FIGÉ dans le code,
    # conservateur (n'écrit que ce qui manque). Cf. moli_config.py.
    if skip_yaml:
        moli_config_result: dict[str, Any] = {"ok": True, "skipped": True}
    else:
        moli_config_result = ensure_moli_ha_config()
        if not moli_config_result.get("ok"):
            errors.append(f"moli_config:{moli_config_result.get('error')}")

    # Compute restart pending: True only if HA config was actually changed.
    ha_restart_pending = bool(
        config_patch_result.get("changed") and config_patch_result.get("ok")
    ) or bool(moli_config_result.get("ha_restart_pending"))

    statuses = [a["status"] for a in actions]
    summary = (
        f"{statuses.count('installed')} installed, "
        f"{statuses.count('started')} started, "
        f"{statuses.count('skipped')} skipped, "
        f"{statuses.count('failed')} failed"
    )

    return {
        "ok": not errors,
        "actions": actions,
        "ha_config_patch": config_patch_result,
        "moli_config": moli_config_result,
        "ha_restart_pending": ha_restart_pending,
        "errors": errors,
        "summary": summary,
    }


# ─── Heartbeat enrichment ────────────────────────────────────────────────────

async def collect_bootstrap_state(ha: HAClient | None = None) -> dict[str, Any]:
    """Snapshot to embed in heartbeat under ``bootstrap_state``.

    Used by the central admin to render the install wizard checklist (chantier B)
    and decide whether to auto-enqueue ``bootstrap_stack``.

    ``zigbee_stack`` (``zha``/``z2m``/``both``/``none``/``unknown``) permet au
    central d'afficher le stack Zigbee de la box et au wizard de masquer
    l'install Z2M sur les box en ZHA.
    """
    state: dict[str, Any] = {
        "mosquitto": "unknown",
        "zigbee2mqtt": "unknown",
        "cloudflared": "unknown",
        "zigbee_stack": "unknown",
        "moli_config_ok": None,
        "trusted_proxies_ok": None,
        "purge_keep_days_ok": None,
        "ha_restart_pending": False,
    }

    # Blocs config Moli (packages + dashboard lovelace) présents dans le
    # fichier ? (None = illisible). Indépendant du superviseur → avant le
    # early-return addons_list.
    cfg_path = os.environ.get("HA_CONFIG_PATH") or "/config/configuration.yaml"
    state["moli_config_ok"] = moli_config_present(cfg_path)

    try:
        addons = await supervisor_client.addons_list()
    except Exception as e:
        log.warning("collect_bootstrap_state: addons_list failed: %s", e)
        return state

    def addon_state_for(name: str) -> str:
        entry = ADDON_CATALOG.get(name)
        if not entry:
            return "unknown"
        patterns = [re.compile(p, re.IGNORECASE) for p in entry["slug_patterns"]]
        exact_slug = entry.get("slug")
        for a in addons:
            slug = a.get("slug") or ""
            if exact_slug and slug == exact_slug:
                return a.get("state", "stopped")
            for rx in patterns:
                if rx.match(slug):
                    return a.get("state", "stopped")
        return "not_installed"

    state["mosquitto"] = addon_state_for("mosquitto")
    state["zigbee2mqtt"] = addon_state_for("zigbee2mqtt")
    state["cloudflared"] = addon_state_for("cloudflared")

    # Stack Zigbee (ZHA vs Z2M) — réutilise l'état add-on déjà calculé pour Z2M
    # (pas de 2e appel superviseur) ; sonde ZHA via les config entries HA Core.
    zha: Optional[bool] = None
    if ha is not None:
        try:
            entries = await ha.config_entries()
            if entries is not None:
                zha = any(e.get("domain") == "zha" for e in entries)
        except Exception as e:  # noqa: BLE001 — best-effort
            log.warning("collect_bootstrap_state: zha probe failed: %s", e)
    state["zigbee_stack"] = zigbee_stack_from_states(zha, state["zigbee2mqtt"])

    # HA config check — read configuration.yaml and look for our markers
    target = os.environ.get("HA_CONFIG_PATH") or "/config/configuration.yaml"
    try:
        if os.path.exists(target):
            from ruamel.yaml import YAML

            y = YAML()
            with open(target, "r", encoding="utf-8") as f:
                doc = y.load(f)
            if isinstance(doc, dict):
                http = doc.get("http") or {}
                proxies = http.get("trusted_proxies") or []
                state["trusted_proxies_ok"] = HA_SUPERVISOR_CIDR in proxies
                recorder = doc.get("recorder") or {}
                state["purge_keep_days_ok"] = recorder.get("purge_keep_days") == 14
    except Exception as e:
        log.warning("collect_bootstrap_state: yaml parse failed: %s", e)

    return state
