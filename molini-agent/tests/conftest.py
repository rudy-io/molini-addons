"""Configuration pytest commune.

Rend le package ``molini_agent`` importable depuis le dossier parent
(``box/addons/molini-agent/``) sans avoir besoin d'installer l'add-on.
"""
import sys
from pathlib import Path

# Le package vit dans box/addons/molini-agent/molini_agent.
# Les tests vivent dans box/addons/molini-agent/tests.
# On ajoute le parent (dossier add-on) au sys.path pour rendre
# ``from molini_agent.dashboard_builder import ...`` fonctionnel.
ADDON_ROOT = Path(__file__).resolve().parent.parent
if str(ADDON_ROOT) not in sys.path:
    sys.path.insert(0, str(ADDON_ROOT))

# Le dossier blocks : layout historique repo central (molini/box/ha-config/...)
# OU, dans le repo standalone molini-addons, les blocs embarqués dans rootfs/
# (ceux réellement livrés sur les box). Fallback = rootfs → les tests tournent
# partout (prérequis CI).
REPO_ROOT = ADDON_ROOT.parent.parent.parent  # molini/ (layout historique)
BLOCKS_DIR = REPO_ROOT / "box" / "ha-config" / "dashboards" / "blocks"
if not BLOCKS_DIR.is_dir():
    BLOCKS_DIR = (
        ADDON_ROOT / "rootfs" / "usr" / "share" / "molini" / "dashboards" / "blocks"
    )
