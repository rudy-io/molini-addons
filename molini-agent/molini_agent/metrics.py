import time
from typing import Any, Optional

import psutil

from .config import Config
from .ha_client import HAClient
from .service_status import collect_services


_START_TS = time.time()


def agent_uptime_seconds() -> int:
    return int(time.time() - _START_TS)


def system_metrics() -> dict[str, float]:
    try:
        cpu = psutil.cpu_percent(interval=0.5)
    except Exception:
        cpu = 0.0
    try:
        ram = psutil.virtual_memory().percent
    except Exception:
        ram = 0.0
    try:
        disk = psutil.disk_usage("/").percent
    except Exception:
        disk = 0.0
    return {"cpu_pct": round(cpu, 2), "ram_pct": round(ram, 2), "disk_pct": round(disk, 2)}


def _as_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _as_int(v: Any) -> Optional[int]:
    f = _as_float(v)
    return int(f) if f is not None else None


async def collect_metrics(cfg: Config, ha: HAClient) -> dict[str, Any]:
    sys_m = system_metrics()
    metrics: dict[str, Any] = {**sys_m}

    # HA global metrics
    states = await ha.states()
    if states:
        metrics["ha_entities_count"] = len(states)
        metrics["ha_unavailable_count"] = sum(
            1 for s in states if s.get("state") in ("unavailable", "unknown")
        )
        zigbee_devices = {
            s.get("attributes", {}).get("device_id")
            for s in states
            if "zigbee" in (s.get("entity_id") or "").lower()
            or s.get("attributes", {}).get("via_device_id")
        }
        zigbee_devices.discard(None)
        if zigbee_devices:
            metrics["ha_zigbee_devices_count"] = len(zigbee_devices)

    # Linky — n'inclut la clé que si la valeur est exploitable
    power_state = await ha.get_state(cfg.linky_power_entity)
    if power_state:
        v = _as_int(power_state.get("state"))
        if v is not None:
            metrics["linky_power_w"] = v

    hc_state = await ha.get_state(cfg.linky_hc_entity)
    if hc_state:
        v = _as_int(hc_state.get("state"))
        if v is not None:
            metrics["linky_idx_hc_wh"] = v

    hp_state = await ha.get_state(cfg.linky_hp_entity)
    if hp_state:
        v = _as_int(hp_state.get("state"))
        if v is not None:
            metrics["linky_idx_hp_wh"] = v

    today = await ha.get_state(cfg.linky_tempo_today_entity)
    if today and today.get("state"):
        metrics["linky_tempo_today"] = str(today["state"])[:10]

    tomorrow = await ha.get_state(cfg.linky_tempo_tomorrow_entity)
    if tomorrow and tomorrow.get("state"):
        metrics["linky_tempo_tomorrow"] = str(tomorrow["state"])[:10]

    # Services (HAOS : add-ons via supervisor / Debian : containers Docker)
    services = await collect_services()
    if services:
        metrics["raw"] = {"services": services}

    return metrics
