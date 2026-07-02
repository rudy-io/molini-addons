"""Pose automatique de la config HA requise par Moli (onboarding v0.8).

Chez Carole, ces deux blocs ont dû être posés À LA MAIN (gotcha documenté) :

    homeassistant:
      packages: !include_dir_named packages
    lovelace:
      dashboards:
        moli-energie:          # clé AVEC tiret obligatoire
          mode: yaml
          title: Moli
          icon: mdi:home-lightning-bolt
          show_in_sidebar: true
          filename: dashboards/molini.yaml

Ce module les pose automatiquement — c'est le « mécanisme dédié hors
white-list patch » prévu par le chantier v0.8 :

- ``homeassistant`` et ``lovelace`` sont volontairement ABSENTS de
  ``yaml_patch.PATCHABLE_TOP_KEYS`` (un patch arbitraire de ``homeassistant``
  = surface dangereuse). Ici le contenu est **FIGÉ DANS LE CODE** — aucun
  payload du central n'entre dans le fichier → pas de surface RCE nouvelle.
- **Conservateur** : n'écrit que ce qui MANQUE. Une valeur existante n'est
  JAMAIS modifiée (si l'installateur a déjà un ``packages:`` différent ou un
  dashboard ``moli-energie`` custom, on n'y touche pas).
- Idempotent, backup ``.bak-YYYYMMDD``, écriture atomique (même pattern que
  ``yaml_patch.apply_patch_to_file``).
- Un changement nécessite un **full restart HA** (un reload rapide ne charge
  ni un nouveau package include, ni un dashboard YAML) → ``ha_restart_pending``.
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
from datetime import datetime
from io import StringIO
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, TaggedScalar

log = logging.getLogger("molini_agent.moli_config")

MOLI_DASHBOARD_KEY = "moli-energie"  # tiret obligatoire (gotcha 0.6.x)
MOLI_DASHBOARD_FILENAME = "dashboards/molini.yaml"


def _yaml() -> YAML:
    y = YAML()
    y.preserve_quotes = True
    y.indent(mapping=2, sequence=4, offset=2)
    y.width = 4096
    return y


def _default_dashboard() -> CommentedMap:
    d = CommentedMap()
    d["mode"] = "yaml"
    d["title"] = "Moli"
    d["icon"] = "mdi:home-lightning-bolt"
    d["show_in_sidebar"] = True
    d["filename"] = MOLI_DASHBOARD_FILENAME
    return d


def compute_moli_config(current_text: str) -> tuple[str, bool, dict[str, Any]]:
    """Calcule le nouveau contenu (sans écrire). Retourne (texte, changed, détails)."""
    yaml = _yaml()
    doc = yaml.load(current_text) if current_text.strip() else None
    if doc is None:
        doc = CommentedMap()
    if not isinstance(doc, dict):
        raise RuntimeError("configuration.yaml n'est pas un mapping YAML")

    details: dict[str, Any] = {
        "packages_added": False,
        "dashboard_added": False,
        "skipped_existing": [],
    }

    # 1. homeassistant.packages — uniquement si ABSENT.
    ha = doc.get("homeassistant")
    if ha is None:
        ha = CommentedMap()
        ha["packages"] = TaggedScalar("packages", None, "!include_dir_named")
        doc["homeassistant"] = ha
        details["packages_added"] = True
    elif isinstance(ha, dict):
        if "packages" not in ha:
            ha["packages"] = TaggedScalar("packages", None, "!include_dir_named")
            details["packages_added"] = True
        else:
            details["skipped_existing"].append("homeassistant.packages")
    else:
        # homeassistant: existe mais n'est pas un mapping (rare) — on ne touche pas.
        details["skipped_existing"].append("homeassistant(non-mapping)")

    # 2. lovelace.dashboards.moli-energie — uniquement si ABSENT.
    lv = doc.get("lovelace")
    if lv is None:
        lv = CommentedMap()
        doc["lovelace"] = lv
    if isinstance(lv, dict):
        dashboards = lv.get("dashboards")
        if dashboards is None:
            dashboards = CommentedMap()
            lv["dashboards"] = dashboards
        if isinstance(dashboards, dict):
            if MOLI_DASHBOARD_KEY not in dashboards:
                dashboards[MOLI_DASHBOARD_KEY] = _default_dashboard()
                details["dashboard_added"] = True
            else:
                details["skipped_existing"].append(f"lovelace.dashboards.{MOLI_DASHBOARD_KEY}")
        else:
            details["skipped_existing"].append("lovelace.dashboards(non-mapping)")
    else:
        details["skipped_existing"].append("lovelace(non-mapping)")

    changed = details["packages_added"] or details["dashboard_added"]
    if not changed:
        return current_text, False, details

    buf = StringIO()
    yaml.dump(doc, buf)
    return buf.getvalue(), True, details


def moli_config_present(path: str) -> bool | None:
    """True si les 2 blocs Moli sont présents dans le fichier, False sinon.
    None = fichier illisible (état inconnu). Utilisé par le heartbeat."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        _, changed, _ = compute_moli_config(text)
        return not changed
    except FileNotFoundError:
        return False
    except Exception as e:  # noqa: BLE001 — best-effort heartbeat
        log.warning("moli_config_present: %s", e)
        return None


def ensure_moli_ha_config(path: str | None = None) -> dict[str, Any]:
    """Pose les blocs manquants dans ``configuration.yaml`` (idempotent).

    Returns::

        { "ok": bool, "changed": bool, "ha_restart_pending": bool,
          "packages_added": …, "dashboard_added": …, "skipped_existing": […],
          "path": …, "backup": … (si écrit), "error": … (si ko) }
    """
    target = path or os.environ.get("HA_CONFIG_PATH") or "/config/configuration.yaml"
    report: dict[str, Any] = {"path": target, "ok": True, "changed": False, "ha_restart_pending": False}

    existed = os.path.exists(target)
    current_text = ""
    if existed:
        try:
            with open(target, "r", encoding="utf-8") as f:
                current_text = f.read()
        except OSError as e:
            return {**report, "ok": False, "error": f"read_error:{e}"}

    try:
        new_text, changed, details = compute_moli_config(current_text)
    except Exception as e:  # noqa: BLE001 — parse error = on ne touche PAS au fichier
        return {**report, "ok": False, "error": f"parse_error:{e}"}
    report.update(details)

    if not changed:
        log.info("moli_config: %s déjà conforme", target)
        return report

    parent = os.path.dirname(target)
    if parent:
        os.makedirs(parent, exist_ok=True)

    if existed:
        bak = f"{target}.bak-{datetime.now().strftime('%Y%m%d')}"
        if not os.path.exists(bak):
            try:
                shutil.copy2(target, bak)
                report["backup"] = bak
            except OSError as e:
                log.warning("moli_config: backup failed (%s) — continuing", e)

    fd, tmp = tempfile.mkstemp(prefix=".molini_moli_config_", dir=parent or None)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_text)
        os.replace(tmp, target)
    except Exception as e:  # noqa: BLE001
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        return {**report, "ok": False, "error": f"write_error:{e}"}

    report["changed"] = True
    report["ha_restart_pending"] = True  # package include + dashboard YAML = full restart
    log.info(
        "moli_config: %s mis à jour (packages_added=%s dashboard_added=%s) — restart HA requis",
        target,
        report["packages_added"],
        report["dashboard_added"],
    )
    return report
