"""Détection du runtime de l'agent.

Trois modes possibles :
- ``haos``    : add-on Home Assistant OS (ce package). On utilise l'API
                supervisor pour tout ce qui touche à la stack (restart Core,
                update add-ons, install cloudflared, etc.).
- ``debian``  : container Docker autonome sur box Debian/Ubuntu (le mode
                historique du dossier ``agent/`` à la racine du repo).
                On utilise ``docker.sock`` + ``docker compose`` directement.
- ``unknown`` : fallback prudent, on désactive les commandes qui touchent
                à la stack.

La distinction se fait via la variable d'env ``MOLINI_RUNTIME`` (positionnée
par ``run.sh`` de l'add-on) ou par détection de ``SUPERVISOR_TOKEN``.
"""
import os


def detect_runtime() -> str:
    explicit = (os.environ.get("MOLINI_RUNTIME") or "").strip().lower()
    if explicit in ("haos", "debian", "unknown"):
        return explicit
    if os.environ.get("SUPERVISOR_TOKEN"):
        return "haos"
    if os.path.exists("/var/run/docker.sock"):
        return "debian"
    return "unknown"


RUNTIME = detect_runtime()


def is_haos() -> bool:
    return RUNTIME == "haos"


def supervisor_url() -> str:
    return os.environ.get("SUPERVISOR_URL", "http://supervisor").rstrip("/")


def supervisor_token() -> str:
    return os.environ.get("SUPERVISOR_TOKEN", "")
