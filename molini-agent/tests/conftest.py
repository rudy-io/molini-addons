<<<<<<< HEAD
"""Pytest configuration for molini-agent tests.

Adds the addon root to ``sys.path`` so tests can import ``molini_agent.*``
without installing the package in editable mode (we don't ship a setup.py;
the package is run via ``python -m molini_agent`` inside the Alpine image).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
=======
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

# Le dossier blocks est dans box/ha-config/dashboards/blocks/ (relatif au repo).
REPO_ROOT = ADDON_ROOT.parent.parent.parent  # molini/
BLOCKS_DIR = REPO_ROOT / "box" / "ha-config" / "dashboards" / "blocks"
>>>>>>> night/chantier-E-dashboards-blocks
