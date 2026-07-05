import asyncio
import logging
import signal
import sys
from typing import Any

import httpx

from .backup import backup_loop
from .bootstrap import collect_bootstrap_state
from .moli_config import ensure_moli_ha_config
from .commands import poll_and_execute
from .config import AGENT_VERSION, Config, configure_logging
from .ha_client import HAClient
from .metrics import agent_uptime_seconds, collect_metrics
from .runtime import RUNTIME, is_haos


configure_logging()
log = logging.getLogger("molini_agent")


async def send_heartbeat(cfg: Config, payload: dict[str, Any]) -> bool:
    url = f"{cfg.central_url}/api/agent/heartbeat"
    headers = {"Authorization": f"Bearer {cfg.client_token}"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code >= 400:
                log.warning("Heartbeat rejected (%s): %s", r.status_code, r.text[:200])
                return False
            return True
    except httpx.HTTPError as e:
        log.warning("Heartbeat network error: %s", e)
        return False


async def loop(cfg: Config) -> None:
    stop = asyncio.Event()

    def _handle_signal(*_: Any) -> None:
        log.info("Stop signal received, exiting cleanly")
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            asyncio.get_running_loop().add_signal_handler(sig, _handle_signal)
        except (NotImplementedError, RuntimeError):
            pass

    ha = HAClient(cfg.ha_url, cfg.ha_token)
    backup_task: asyncio.Task[None] | None = None
    try:
        ha_config = await ha.config()
        ha_version = (ha_config or {}).get("version")
        log.info(
            "Moli Agent %s starting — runtime=%s central=%s ha_version=%s interval=%ss",
            AGENT_VERSION,
            RUNTIME,
            cfg.central_url,
            ha_version,
            cfg.heartbeat_interval_s,
        )

        # Onboarding v0.8 : pose des blocs config Moli (packages + dashboard)
        # dès le boot — conservateur (n'écrit que ce qui manque), donc sans
        # risque sur une box déjà configurée. Le restart HA qui charge ces
        # blocs est séquencé par le central (jamais auto au boot → pas de
        # boucle de restart).
        if is_haos():
            try:
                mc = ensure_moli_ha_config()
                if mc.get("changed"):
                    log.info("moli_config posé au boot — restart HA requis (piloté par le central)")
            except Exception as e:
                log.warning("ensure_moli_ha_config au boot: %s", e)
            # 0.19.0 — applique aussi le patch config Moli (thème Le Relevé,
            # trusted_proxies, extra_module_url…) au boot : le rollout d'un
            # nouveau thème suit ainsi la MAJ de l'add-on sur toute la flotte,
            # sans dépendre d'un bootstrap_stack. Deep-merge idempotent ;
            # comme moli_config, le restart HA qui le charge reste piloté par
            # le central (jamais auto au boot).
            try:
                from .bootstrap import MOLI_HA_CONFIG_PATCH, patch_ha_config
                pr = patch_ha_config(MOLI_HA_CONFIG_PATCH)
                if pr.get("changed"):
                    log.info(
                        "config Moli patchée au boot (%s) — restart HA requis (piloté par le central)",
                        ", ".join(pr.get("applied_keys", [])) or "modifs",
                    )
            except Exception as e:
                log.warning("patch config Moli au boot: %s", e)

        backup_task = asyncio.create_task(backup_loop(cfg))

        while not stop.is_set():
            try:
                metrics = await collect_metrics(cfg, ha)
            except Exception as e:
                log.exception("Metrics collection failed: %s", e)
                metrics = {}

            payload: dict[str, Any] = {
                "agent_version": AGENT_VERSION,
                "uptime_seconds": agent_uptime_seconds(),
                "metrics": metrics,
                "runtime": RUNTIME,
            }
            if ha_version:
                payload["ha_version"] = ha_version

            # Bootstrap state — exposes mosquitto/z2m/cloudflared install state
            # + HA config flags so the admin wizard can render its checklist
            # without having to query each add-on individually.
            if is_haos():
                try:
                    payload["bootstrap_state"] = await collect_bootstrap_state(ha)
                except Exception as e:
                    log.warning("bootstrap_state collection failed: %s", e)

            ok = await send_heartbeat(cfg, payload)
            log.info(
                "Heartbeat %s — power=%sW cpu=%s%% ram=%s%% entities=%s",
                "OK" if ok else "FAIL",
                metrics.get("linky_power_w"),
                metrics.get("cpu_pct"),
                metrics.get("ram_pct"),
                metrics.get("ha_entities_count"),
            )

            try:
                await poll_and_execute(cfg)
            except Exception as e:
                log.exception("Command polling error: %s", e)

            try:
                await asyncio.wait_for(stop.wait(), timeout=cfg.heartbeat_interval_s)
            except asyncio.TimeoutError:
                pass
    finally:
        if backup_task and not backup_task.done():
            backup_task.cancel()
            try:
                await backup_task
            except asyncio.CancelledError:
                pass
        await ha.close()


def run() -> None:
    try:
        cfg = Config.from_env()
    except RuntimeError as e:
        log.error("%s", e)
        sys.exit(1)

    asyncio.run(loop(cfg))


if __name__ == "__main__":
    run()
