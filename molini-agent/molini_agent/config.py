import logging
import os
from dataclasses import dataclass

# Version de l'add-on (figée au build par le Dockerfile via MOLINI_AGENT_VERSION).
# Pas d'OTA self-update sous HAOS : c'est le mécanisme add-on store qui s'en occupe.
AGENT_VERSION = os.environ.get("AGENT_VERSION", "0.5.0")


@dataclass(frozen=True)
class Config:
    central_url: str
    client_token: str
    ha_url: str
    ha_token: str
    heartbeat_interval_s: int
    linky_power_entity: str
    linky_hc_entity: str
    linky_hp_entity: str
    linky_tempo_today_entity: str
    linky_tempo_tomorrow_entity: str

    @classmethod
    def from_env(cls) -> "Config":
        def require(name: str) -> str:
            v = os.environ.get(name)
            if not v:
                raise RuntimeError(f"Missing required env var: {name}")
            return v

        return cls(
            central_url=require("CENTRAL_URL").rstrip("/"),
            client_token=require("CLIENT_TOKEN"),
            ha_url=require("HA_URL").rstrip("/"),
            ha_token=require("HA_TOKEN"),
            heartbeat_interval_s=int(os.environ.get("HEARTBEAT_INTERVAL_S", "300")),
            linky_power_entity=os.environ.get(
                "LINKY_POWER_ENTITY", "sensor.linky_puissance_apparente"
            ),
            linky_hc_entity=os.environ.get(
                "LINKY_HC_ENTITY", "sensor.linky_index_hchc"
            ),
            linky_hp_entity=os.environ.get(
                "LINKY_HP_ENTITY", "sensor.linky_index_hchp"
            ),
            linky_tempo_today_entity=os.environ.get(
                "LINKY_TEMPO_TODAY_ENTITY", "sensor.rte_tempo_couleur_actuelle"
            ),
            linky_tempo_tomorrow_entity=os.environ.get(
                "LINKY_TEMPO_TOMORROW_ENTITY", "sensor.rte_tempo_prochaine_couleur"
            ),
        )


def configure_logging() -> None:
    """Niveau de log piloté par MOLINI_LOG_LEVEL (pos. par run.sh)."""
    level_name = (os.environ.get("MOLINI_LOG_LEVEL") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
