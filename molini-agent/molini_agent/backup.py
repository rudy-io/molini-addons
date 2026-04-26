"""Backup quotidien — adapté HAOS.

Pipeline :
1. Tar les volumes (par défaut /config + /share/zigbee2mqtt sous HAOS) avec
   un set d'exclusions raisonnable
2. Pipe dans `age -r <recipient>` pour chiffrer
3. POST le binaire vers le central /api/agent/backup avec Bearer token

Le binaire `age` est installé dans l'image Alpine (Dockerfile add-on).
"""
import asyncio
import json
import logging
import os
import shutil
from typing import Any

import httpx

from .config import AGENT_VERSION, Config
from .runtime import is_haos

log = logging.getLogger("molini_agent.backup")


def _resolve_paths(raw: str) -> list[str]:
    items = [p.strip() for p in raw.replace(":", ",").split(",") if p.strip()]
    existing: list[str] = []
    for p in items:
        if os.path.exists(p):
            existing.append(p)
        else:
            log.warning("Backup path skipped (not found): %s", p)
    return existing


_DEFAULT_EXCLUDES = [
    # Médias HA — peuvent peser plusieurs GB
    "*/media/*",
    "*/backups/*",
    "*/tts/*",
    "*/frigate/*",
    "*/recordings/*",
    "*/snapshots/*",
    "*/image/*",
    # Bases d'historique HA — reconstructibles, énormes (souvent >500 MB).
    "*/home-assistant_v2.db*",
    "*/zigbee2mqtt/data/log/*",
    # Logs & runtime
    "*/home-assistant.log*",
    "*.log",
    "*/log/*",
    "*/logs/*",
    # Caches
    "*/__pycache__/*",
    "*/.cache/*",
    "*/deps/*",
    "*/.git/*",
]


def _excludes_from_env() -> list[str]:
    raw = os.environ.get("BACKUP_EXCLUDES", "").strip()
    if not raw:
        return _DEFAULT_EXCLUDES
    items = [p.strip() for p in raw.split(",") if p.strip()]
    return items or _DEFAULT_EXCLUDES


def _default_volumes() -> str:
    """Sélection des volumes par défaut selon le runtime."""
    if is_haos():
        # /config = HA config, /share = Z2M data + autres add-ons partagés
        return "/config,/share/zigbee2mqtt"
    return (
        "/home/rudy/docker/homeassistant/config,"
        "/home/rudy/docker/zigbee2mqtt/data,"
        "/home/rudy/docker/molini-agent/.env"
    )


async def _run_pipeline(paths: list[str], recipient: str) -> bytes:
    if not paths:
        raise RuntimeError("No backup paths to archive")
    if not shutil.which("age"):
        raise RuntimeError("`age` binary not found in PATH")
    if not shutil.which("tar"):
        raise RuntimeError("`tar` binary not found in PATH")

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        excludes = _excludes_from_env()
        tar_cmd = ["tar"]
        for ex in excludes:
            tar_cmd.extend(["--exclude", ex])
        tar_cmd.extend(["-czf", tmp_path, *paths])
        log.info("tar with %d exclude patterns", len(excludes))
        tar_proc = await asyncio.create_subprocess_exec(
            *tar_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, tar_err = await tar_proc.communicate()
        if tar_proc.returncode not in (0, 1):
            raise RuntimeError(
                f"tar failed ({tar_proc.returncode}): "
                f"{(tar_err or b'').decode(errors='replace')[:300]}"
            )
        if tar_proc.returncode == 1:
            log.warning("tar exit 1 (files changed during read), continuing")

        age_proc = await asyncio.create_subprocess_exec(
            "age",
            "-r",
            recipient,
            "-o",
            "-",
            tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        enc_data, age_err = await age_proc.communicate()
        if age_proc.returncode != 0:
            raise RuntimeError(
                f"age failed ({age_proc.returncode}): "
                f"{(age_err or b'').decode(errors='replace')[:300]}"
            )
        if not enc_data:
            raise RuntimeError("Empty backup archive")
        return enc_data
    finally:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass


async def run_backup_once(cfg: Config) -> dict[str, Any]:
    recipient = os.environ.get("BACKUP_AGE_RECIPIENT", "").strip()
    if not recipient or not recipient.startswith("age1"):
        log.warning("BACKUP_AGE_RECIPIENT not set or invalid → backup skipped")
        return {"skipped": True, "reason": "no_recipient"}

    raw_paths = os.environ.get("BACKUP_VOLUMES") or _default_volumes()
    paths = _resolve_paths(raw_paths)
    if not paths:
        log.warning("No existing backup paths — skipping")
        return {"skipped": True, "reason": "no_paths"}

    log.info("Backup starting — paths=%d recipient=%s...", len(paths), recipient[:14])
    enc = await _run_pipeline(paths, recipient)
    size = len(enc)
    log.info("Backup encrypted, size=%.2f MB — uploading", size / 1024 / 1024)

    metadata = {
        "agent_version": AGENT_VERSION,
        "encrypted_size": size,
        "paths": paths,
    }

    url = f"{cfg.central_url}/api/agent/backup"
    headers = {
        "Authorization": f"Bearer {cfg.client_token}",
        "Content-Type": "application/octet-stream",
        "X-Backup-Metadata": json.dumps(metadata),
    }
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            r = await client.post(url, headers=headers, content=enc)
            if r.status_code >= 400:
                log.error("Backup upload rejected (%s): %s", r.status_code, r.text[:200])
                return {"ok": False, "status": r.status_code, "error": r.text[:200]}
            data = r.json()
            log.info(
                "Backup OK — id=%s key=%s size=%s",
                data.get("backup_id"),
                data.get("key"),
                data.get("size_bytes"),
            )
            return {"ok": True, **data}
    except httpx.HTTPError as e:
        log.exception("Backup upload network error: %s", e)
        return {"ok": False, "error": str(e)}


async def backup_loop(cfg: Config) -> None:
    target_hour = int(os.environ.get("BACKUP_HOUR_LOCAL", "3"))
    while True:
        try:
            now = _local_now()
            next_run = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run = next_run + _one_day()
            wait_s = (next_run - now).total_seconds()
            log.info(
                "Next backup scheduled at %s (in %.0f min)",
                next_run.isoformat(timespec="minutes"),
                wait_s / 60,
            )
            await asyncio.sleep(wait_s)
            await run_backup_once(cfg)
        except asyncio.CancelledError:
            return
        except Exception as e:
            log.exception("Backup loop error: %s", e)
            await asyncio.sleep(60 * 30)


def _local_now():
    from datetime import datetime
    return datetime.now()


def _one_day():
    from datetime import timedelta
    return timedelta(days=1)
