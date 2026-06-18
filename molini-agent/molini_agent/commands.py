"""Récupération + exécution des commandes envoyées par l'admin (mode HAOS).

Mapping des commandes admin vers l'API supervisor HA :

| Commande         | HAOS impl.                                                     |
|------------------|----------------------------------------------------------------|
| backup_now       | tar + age + upload central (chemins /config + /share)          |
| ha_restart       | POST /core/restart via supervisor                              |
| agent_restart    | sys.exit(0) — s6 relance le service                            |
| agent_update     | skipped:managed_by_supervisor (les MAJ passent par store add-on)|
| stack_update     | itère les add-ons et update si update_available                |
| tunnel_install   | install + configure + start de l'add-on cloudflared            |
| tunnel_uninstall | stop + uninstall de l'add-on cloudflared                       |
| ha_provision     | écrit /config/packages/molini_discovered.yaml + reload         |
| bootstrap_stack  | (chantier A) provisionne broker + z2m + cloudflared + config HA|
| install_addon    | (chantier A) installe 1 add-on précis (slug white-listé)       |
| patch_ha_config  | (chantier A) deep-merge YAML configuration.yaml (keys white-listées)|
| rebuild_dashboard| (chantier E) assemble dashboards/molini.yaml + reload Lovelace |
"""
import asyncio
import logging
import os
from typing import Any

import httpx

from . import supervisor_client
from .backup import run_backup_once
from .bootstrap import (
    ALLOWED_ADDON_NAMES,
    bootstrap_stack,
    install_or_start_addon,
    patch_ha_config as bootstrap_patch_ha_config,
)
from .config import Config
from .dashboard_builder import build_and_write
from .ha_client import HAClient
from .ha_discovery import execute_ha_provision

log = logging.getLogger("molini_agent.commands")

# Slug de l'add-on Cloudflare Tunnel communautaire (Tobi/cloudflared).
# Le repo est ajouté à la volée si pas déjà installé.
CLOUDFLARED_REPO = "https://github.com/brenner-tobias/ha-addons"
CLOUDFLARED_SLUG_CANDIDATES = (
    # Le slug réel devient ``<repo_hash>_cloudflared``. On essaie ``cloudflared``
    # en premier (compat HA Yellow/Green pré-équipés) puis on liste pour trouver.
    "cloudflared",
)


async def fetch_pending(cfg: Config) -> list[dict[str, Any]]:
    url = f"{cfg.central_url}/api/agent/commands"
    headers = {"Authorization": f"Bearer {cfg.client_token}"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=headers)
            if r.status_code != 200:
                log.warning("commands fetch %s: %s", r.status_code, r.text[:200])
                return []
            return r.json().get("commands", [])
    except httpx.HTTPError as e:
        log.warning("commands fetch error: %s", e)
        return []


async def report_result(
    cfg: Config,
    cmd_id: str,
    status: str,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    url = f"{cfg.central_url}/api/agent/commands/{cmd_id}/result"
    headers = {"Authorization": f"Bearer {cfg.client_token}"}
    payload: dict[str, Any] = {"status": status}
    if result is not None:
        payload["result"] = result
    if error is not None:
        payload["error"] = error[:1500]
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code >= 400:
                log.warning(
                    "result report rejected (%s): %s", r.status_code, r.text[:200]
                )
    except httpx.HTTPError as e:
        log.warning("result report error: %s", e)


# ─── Handlers ─────────────────────────────────────────────────────────────────

async def execute_backup_now(cfg: Config) -> dict[str, Any]:
    res = await run_backup_once(cfg)
    if res.get("ok"):
        return {
            "backup_id": res.get("backup_id"),
            "size_bytes": res.get("size_bytes"),
        }
    if res.get("skipped"):
        return res
    raise RuntimeError(res.get("error") or "backup_failed")


async def execute_ha_restart() -> dict[str, Any]:
    """Redémarre HA Core via supervisor (équivalent du bouton Restart dans l'UI)."""
    return await supervisor_client.core_restart()


def _suicide() -> None:  # pragma: no cover
    import sys

    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)


async def execute_agent_restart() -> dict[str, Any]:
    """Demande à s6 de relancer le service (via finish hook)."""
    log.info("agent_restart received — exiting in 2s, s6 will respawn")
    asyncio.get_event_loop().call_later(2, _suicide)
    return {"note": "process will exit in 2s; s6 will respawn the service"}


async def execute_agent_update(_cfg: Config) -> dict[str, Any]:
    """Sous HAOS, les mises à jour de l'add-on passent par le store HA.

    Le central peut détecter un add-on Moli Agent obsolète via le flag
    ``update_available`` de la liste des services (heartbeat). Pour pousser
    une MAJ, on déclenche ``stack_update`` filtré sur le slug Moli Agent.
    """
    return {
        "skipped": True,
        "reason": "managed_by_supervisor",
        "hint": "publier une nouvelle version dans le repo add-on, puis stack_update.",
    }


async def execute_stack_update(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Met à jour les add-ons HA qui ont ``update_available=true``.

    Si ``payload.services`` est passé (liste de slugs), ne met à jour que
    ceux-ci. Sinon, met à jour tous les add-ons éligibles.
    """
    services = (payload or {}).get("services") or []
    if services and not isinstance(services, list):
        raise RuntimeError("invalid `services` (expected list)")

    addons = await supervisor_client.addons_list()
    updated: list[str] = []
    skipped: list[str] = []
    for a in addons:
        slug = a.get("slug")
        if not slug:
            continue
        if services and slug not in services:
            continue
        if not a.get("update_available"):
            skipped.append(slug)
            continue
        try:
            await supervisor_client.addon_update(slug)
            updated.append(slug)
        except Exception as e:
            log.exception("addon_update %s failed: %s", slug, e)
            skipped.append(f"{slug} (error)")

    return {"updated": updated, "skipped": skipped}


async def _find_cloudflared_slug() -> str | None:
    """Cherche le slug réel de l'add-on cloudflared installé."""
    addons = await supervisor_client.addons_list()
    for a in addons:
        slug = a.get("slug") or ""
        name = (a.get("name") or "").lower()
        if "cloudflared" in slug.lower() or "cloudflared" in name:
            return slug
    return None


async def execute_tunnel_install(
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    """Installe + configure + démarre l'add-on cloudflared communautaire.

    payload attendu : ``{ "token": "...", "subdomain": "..." }``

    Stratégie :
    1. Si un add-on cloudflared est déjà installé → on pousse juste les options
       et on (re)démarre.
    2. Sinon, on ajoute le repo communautaire au store, on tente l'install via
       le slug supposé.
    """
    token = (payload or {}).get("token")
    subdomain = (payload or {}).get("subdomain")
    if not token or not isinstance(token, str) or len(token) < 20:
        raise RuntimeError("missing or invalid token")

    slug = await _find_cloudflared_slug()
    if not slug:
        # Ajout du repo, puis on retente la résolution du slug
        try:
            await supervisor_client.store_repositories_add(CLOUDFLARED_REPO)
        except Exception as e:
            raise RuntimeError(
                f"impossible d'ajouter le repo cloudflared: {e}"
            ) from e
        slug = await _find_cloudflared_slug()
        if not slug:
            raise RuntimeError(
                "add-on cloudflared introuvable après ajout du repo — "
                "merci de l'installer manuellement depuis le store HA."
            )

    # Pose la config (le schéma exact dépend de l'add-on, on se contente du token)
    options = {"tunnel_token": token}
    try:
        await supervisor_client.addon_options(slug, options)
    except Exception as e:
        log.warning("addon_options %s failed: %s — on tente quand même un start", slug, e)

    # Install si pas encore installé (l'API renvoie 400 si déjà — on tolère)
    try:
        await supervisor_client.addon_install(slug)
    except Exception as e:
        log.info("addon_install %s noop: %s", slug, e)

    await supervisor_client.addon_start(slug)
    log.info("cloudflared add-on started — slug=%s subdomain=%s", slug, subdomain)
    return {"status": "running", "slug": slug, "subdomain": subdomain}


async def execute_tunnel_uninstall(
    _payload: dict[str, Any] | None,
) -> dict[str, Any]:
    """Stop + uninstall l'add-on cloudflared via supervisor."""
    slug = await _find_cloudflared_slug()
    if not slug:
        return {"status": "no_tunnel_found"}

    try:
        await supervisor_client.addon_stop(slug)
    except Exception as e:
        log.info("addon_stop %s noop: %s", slug, e)

    try:
        await supervisor_client.addon_uninstall(slug)
    except Exception as e:
        raise RuntimeError(f"addon_uninstall {slug} failed: {e}") from e

    return {"status": "stopped", "slug": slug}


# ─── Bootstrap commands (chantier A — agent-first onboarding) ─────────────────

async def execute_bootstrap_stack(
    cfg: Config, payload: dict[str, Any] | None
) -> dict[str, Any]:
    """Provisionne toute la stack Moli (Mosquitto + Z2M + cloudflared + patch HA).

    Idempotent : un 2e appel ne ré-installe pas, ne re-patche pas.
    """
    return await bootstrap_stack(cfg, payload=payload)


async def execute_install_addon(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Installe un add-on précis depuis la white-list ``ALLOWED_ADDON_NAMES``.

    payload attendu::

        { "name": "mosquitto" | "zigbee2mqtt" | "cloudflared",
          "options": {...} (optionnel),
          "start": true (default true) }

    Lève RuntimeError si ``name`` est hors white-list — c'est l'unique mécanisme
    qui empêche un admin compromis d'installer un add-on arbitraire (un add-on
    HA peut wrapper du code Python exécuté par le superviseur, donc c'est une
    surface RCE).
    """
    payload = payload or {}
    name = payload.get("name")
    if not name or not isinstance(name, str):
        raise RuntimeError("missing `name` in payload")
    if name not in ALLOWED_ADDON_NAMES:
        raise RuntimeError(
            f"forbidden_addon:{name}: only {sorted(ALLOWED_ADDON_NAMES)} allowed"
        )

    options = payload.get("options")
    if options is not None and not isinstance(options, dict):
        raise RuntimeError("invalid `options` (expected object)")

    start = payload.get("start", True)
    if not isinstance(start, bool):
        raise RuntimeError("invalid `start` (expected boolean)")

    return await install_or_start_addon(name, options=options, start=start)


async def execute_patch_ha_config(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Patch idempotent de ``/config/configuration.yaml`` (white-list de clés).

    payload attendu::

        { "config": { "http": { "trusted_proxies": [...] }, "recorder": {...} } }

    La validation des clés top-level passe par ``yaml_patch.PATCHABLE_TOP_KEYS``.
    Toute clé hors de cette liste fait échouer la commande — protège contre la
    pose d'``automation:`` ou ``python_script:`` malveillants.
    """
    payload = payload or {}
    cfg_patch = payload.get("config")
    if not cfg_patch or not isinstance(cfg_patch, dict):
        raise RuntimeError("missing `config` in payload")
    return bootstrap_patch_ha_config(cfg_patch)
async def _ha_available_entity_ids(cfg: Config) -> set[str] | None:
    """Liste les entity_id dispo côté HA pour le check des blocs.

    Retourne None si HA est injoignable — le builder skip le check
    (no-op safe).
    """
    ha = HAClient(cfg.ha_url, cfg.ha_token)
    try:
        states = await ha.states()
        if not states:
            return None
        return {s.get("entity_id", "") for s in states if s.get("entity_id")}
    finally:
        await ha.close()


async def execute_rebuild_dashboard(
    cfg: Config, payload: dict[str, Any] | None
) -> dict[str, Any]:
    """Reconstruit /config/dashboards/molini.yaml depuis la liste de blocs.

    Payload attendu : ``{ "blocks": ["_header", "energie", ...] }``

    Étapes :
    1. Liste les entity_id dispo côté HA pour détecter les blocs avec
       entités manquantes (warning, pas d'erreur fatale).
    2. Valide la white-list ``ALLOWED_BLOCKS`` (anti path traversal).
    3. Charge les partials depuis ``HA_DASHBOARDS_BLOCKS_DIR`` (défaut
       ``/config/dashboards/blocks``).
    4. Assemble + écrit atomiquement ``/config/dashboards/molini.yaml``.
    5. Demande à HA de recharger la conf Lovelace.

    Le chemin de sortie est fixe — pas d'interpolation user.
    """
    blocks = (payload or {}).get("blocks")
    if blocks is None:
        # Permet à l'admin de retomber sur les defaults en envoyant
        # un payload vide.
        blocks = []

    if not isinstance(blocks, list):
        raise RuntimeError("invalid payload: blocks must be a list")

    available = await _ha_available_entity_ids(cfg)

    # Le builder gère la validation + écriture atomique. Path absolu fixe.
    blocks_dir = os.environ.get(
        "MOLINI_DASHBOARD_BLOCKS_DIR", "/config/dashboards/blocks"
    )
    output_path = os.environ.get(
        "MOLINI_DASHBOARD_OUTPUT_PATH", "/config/dashboards/molini.yaml"
    )

    try:
        result = build_and_write(
            blocks=blocks,
            blocks_dir=blocks_dir,
            output_path=output_path,
            available_entity_ids=available,
        )
    except (ValueError, FileNotFoundError) as e:
        # ValueError = slug invalide / hors white-list ; FileNotFoundError
        # = un fichier .yaml manque sur disque. Les deux remontent en
        # erreur côté admin (commande failed).
        raise RuntimeError(f"build failed: {e}") from e

    # Reload Lovelace côté HA — l'endpoint exact dépend de la version.
    # On essaie le reload via /api/services/lovelace/reload_resources puis
    # un fallback frontend reload. Si les deux échouent, on log et on
    # rapporte tout de même le succès du write (le client peut F5 son
    # dashboard à la main).
    reload = await _reload_lovelace(cfg)
    result["reload"] = reload
    log.info(
        "rebuild_dashboard ok — blocks=%s changed=%s missing=%s",
        result.get("blocks_used"),
        result.get("changed"),
        list((result.get("missing_entities") or {}).keys()),
    )
    return result


async def _reload_lovelace(cfg: Config) -> dict[str, Any]:
    """Demande à HA de recharger la conf Lovelace.

    Note : pour un dashboard en mode YAML, HA recharge automatiquement
    le fichier au prochain refresh du frontend. On déclenche en plus un
    reload des resources frontend pour forcer.
    """
    headers = {"Authorization": f"Bearer {cfg.ha_token}"}
    results: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=15) as client:
        for service, endpoint in (
            ("lovelace.reload_resources", "/api/services/lovelace/reload_resources"),
            ("frontend.reload_themes", "/api/services/frontend/reload_themes"),
        ):
            try:
                r = await client.post(
                    f"{cfg.ha_url}{endpoint}", headers=headers, json={}
                )
                results[service] = r.status_code
            except httpx.HTTPError as e:
                results[service] = f"err: {e}"
    return results


# ─── Dispatcher ───────────────────────────────────────────────────────────────

HANDLERS = {
    "backup_now": lambda cfg, payload: execute_backup_now(cfg),
    "ha_restart": lambda cfg, payload: execute_ha_restart(),
    "agent_restart": lambda cfg, payload: execute_agent_restart(),
    "agent_update": lambda cfg, payload: execute_agent_update(cfg),
    "stack_update": lambda cfg, payload: execute_stack_update(payload),
    "tunnel_install": lambda cfg, payload: execute_tunnel_install(payload),
    "tunnel_uninstall": lambda cfg, payload: execute_tunnel_uninstall(payload),
    "ha_provision": lambda cfg, payload: execute_ha_provision(cfg),
    "bootstrap_stack": lambda cfg, payload: execute_bootstrap_stack(cfg, payload),
    "install_addon": lambda cfg, payload: execute_install_addon(payload),
    "patch_ha_config": lambda cfg, payload: execute_patch_ha_config(payload),
    "rebuild_dashboard": lambda cfg, payload: execute_rebuild_dashboard(cfg, payload),
}


async def execute_one(cfg: Config, cmd: dict[str, Any]) -> None:
    cmd_id = cmd.get("id")
    cmd_type = cmd.get("type")
    payload = cmd.get("payload")

    handler = HANDLERS.get(cmd_type)  # type: ignore[arg-type]
    if not handler:
        log.warning("Unknown command type: %s", cmd_type)
        await report_result(
            cfg, cmd_id, "failed", error=f"unknown command type: {cmd_type}"
        )
        return

    log.info("Executing command %s (%s)", cmd_id, cmd_type)
    await report_result(cfg, cmd_id, "running")
    try:
        result = await handler(cfg, payload)  # type: ignore[arg-type]
        await report_result(cfg, cmd_id, "done", result=result)
        log.info("Command %s done: %s", cmd_id, result)
    except Exception as e:
        log.exception("Command %s failed: %s", cmd_id, e)
        await report_result(cfg, cmd_id, "failed", error=str(e))


async def poll_and_execute(cfg: Config) -> None:
    pending = await fetch_pending(cfg)
    if not pending:
        return
    log.info("Got %d pending commands", len(pending))
    for cmd in pending:
        await execute_one(cfg, cmd)
