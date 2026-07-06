# molini-agent/tests/test_pilotage.py
"""Tests du package pilotage chauffe-eau (molini_pilotage.yaml).

Le package est du YAML HA (helpers + template binary_sensors + automations) —
on valide sa STRUCTURE (parse, ids, garde-fous d'entités) et la LOGIQUE des
templates Jinja (heures creuses avec repli fenêtre + passage minuit, surplus)
en les rendant réellement via jinja2.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pytest
from jinja2 import Environment
from ruamel.yaml import YAML

PKG = (
    Path(__file__).resolve().parents[1]
    / "rootfs/usr/share/molini/packages/molini_pilotage.yaml"
)


@pytest.fixture(scope="module")
def doc():
    return YAML(typ="safe").load(PKG.read_text(encoding="utf-8"))


# ─── Structure ───────────────────────────────────────────────────────────────

def test_package_parses_and_sections(doc):
    assert set(doc.keys()) == {
        "input_select", "input_number", "input_datetime", "template", "automation",
    }


def test_default_mode_is_toujours_allume(doc):
    """SÛRETÉ DEPLOY : la PREMIÈRE option = état initial à la création des
    helpers = « Toujours allumé » (comportement contacteur fermé, zéro
    changement de comportement au rollout flotte)."""
    options = doc["input_select"]["molini_chauffe_eau_mode"]["options"]
    assert options[0] == "Toujours allumé"
    assert set(options) == {
        "Toujours allumé", "Auto (solaire + heures creuses)", "Heures creuses", "Arrêt",
    }


def test_binary_sensors_uids_mirror_constant(doc):
    from molini_agent.ha_discovery import PILOTAGE_TEMPLATE_UIDS
    uids = {
        b["unique_id"]
        for item in doc["template"]
        for b in item.get("binary_sensor", [])
    }
    assert uids == set(PILOTAGE_TEMPLATE_UIDS)


def test_binary_sensor_slug_matches_uid(doc):
    """Invariant slug(name) == unique_id (post-mortem 0.18.x) — binaires inclus."""
    import unicodedata
    def slug(n):
        s = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode().lower()
        return re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    for item in doc["template"]:
        for b in item.get("binary_sensor", []):
            assert slug(b["name"]) == b["unique_id"], b["name"]


def test_automations_ids_and_modes(doc):
    autos = doc["automation"]
    ids = {a["id"] for a in autos}
    assert ids == {
        "molini_ce_hc_debut", "molini_ce_hc_fin",
        "molini_ce_surplus_debut", "molini_ce_surplus_fin", "molini_ce_mode",
    }
    for a in autos:
        assert a["mode"] == "single"
        assert a["max_exceeded"] == "silent"


def test_automations_only_touch_moli_entities(doc):
    """SÛRETÉ : les actions ne pilotent QUE switch.molini_chauffe_eau — jamais
    une entité hardware en dur ni un autre appareil de la maison."""
    text = PKG.read_text(encoding="utf-8")
    # tous les entity_id cités dans le package
    eids = set(re.findall(
        r"\b(?:switch|sensor|binary_sensor|input_select|input_number|input_datetime)"
        r"\.[a-z0-9_]+", text,
    ))
    # les noms de SERVICES matchent le même motif (switch.turn_on…) — exclus
    eids = {e for e in eids if not re.search(r"\.(turn_on|turn_off|toggle|reload)$", e)}
    for e in eids:
        assert re.match(r"^(?:input_[a-z]+\.molini_|switch\.molini_|"
                        r"sensor\.molini_|binary_sensor\.molini_)", e), e
    # la seule cible d'action est l'alias chauffe-eau
    targets = set(re.findall(r"entity_id:\s*(switch\.[a-z0-9_]+)", text))
    assert targets == {"switch.molini_chauffe_eau"}


def test_surplus_fin_has_anticycle_and_hc_guard(doc):
    a = next(x for x in doc["automation"] if x["id"] == "molini_ce_surplus_fin")
    conds = str(a["conditions"])
    assert "molini_heures_creuses" in conds          # jamais couper pendant HC
    assert "last_changed" in conds                   # anti-court-cycle
    assert "900" in conds


# ─── Logique Jinja (rendue réellement) ───────────────────────────────────────

def _render(tpl: str, states: dict, now: datetime) -> str:
    env = Environment()
    env.globals["states"] = lambda e: str(states.get(e, "unknown"))
    env.globals["now"] = lambda: now
    env.filters["float"] = lambda v, d=0.0: float(v) if str(v).replace(".", "", 1).replace("-", "", 1).isdigit() else d
    env.filters["int"] = lambda v, d=0: int(v) if str(v).isdigit() else d
    # normalise la casse : HA accepte "true"/"True" indifféremment pour un
    # binary_sensor — le template mélange littéraux et expressions Jinja.
    return env.from_string(tpl).render().strip().lower()


def _hc_template(doc):
    b = doc["template"][0]["binary_sensor"]
    return next(x for x in b if x["unique_id"] == "molini_heures_creuses")["state"]


def _surplus_template(doc):
    b = doc["template"][0]["binary_sensor"]
    return next(x for x in b if x["unique_id"] == "molini_surplus_solaire")["state"]


BASE = {
    "input_datetime.molini_hc_debut": "23:00:00",
    "input_datetime.molini_hc_fin": "07:00:00",
    "sensor.molini_ptec": "unknown",
}


@pytest.mark.parametrize(
    "hour,minute,expected",
    [
        (23, 30, "true"),   # nuit, dans la fenêtre
        (1, 0, "true"),     # après minuit
        (6, 59, "true"),    # juste avant la fin
        (7, 0, "false"),    # fin exclue
        (12, 0, "false"),   # plein jour
        (22, 59, "false"),  # juste avant le début
    ],
)
def test_hc_fallback_window_overnight(doc, hour, minute, expected):
    """Fenêtre 23:00 → 07:00 (passage minuit) sans PTEC."""
    out = _render(_hc_template(doc), BASE, datetime(2026, 7, 6, hour, minute))
    assert out == expected, f"{hour}:{minute} → {out}"


def test_hc_ptec_takes_priority(doc):
    """PTEC dispo → elle prime sur la fenêtre (même en plein jour)."""
    st = {**BASE, "sensor.molini_ptec": "HC.."}
    assert _render(_hc_template(doc), st, datetime(2026, 7, 6, 14, 0)) == "true"
    st["sensor.molini_ptec"] = "HP.."
    assert _render(_hc_template(doc), st, datetime(2026, 7, 6, 2, 0)) == "false"
    # Tempo : HCJB / HPJR
    st["sensor.molini_ptec"] = "HCJB"
    assert _render(_hc_template(doc), st, datetime(2026, 7, 6, 14, 0)) == "true"


def test_surplus_threshold(doc):
    tpl = _surplus_template(doc)
    st = {"input_number.molini_ce_seuil_surplus": "2200"}
    st["sensor.molini_reseau"] = "-2500"   # injection 2500 W > seuil
    assert _render(tpl, st, datetime(2026, 7, 6, 13, 0)) == "true"
    st["sensor.molini_reseau"] = "-1000"   # injection insuffisante
    assert _render(tpl, st, datetime(2026, 7, 6, 13, 0)) == "false"
    st["sensor.molini_reseau"] = "800"     # soutirage
    assert _render(tpl, st, datetime(2026, 7, 6, 13, 0)) == "false"


# ─── Correctifs revue 0.20.0 ─────────────────────────────────────────────────

def test_hc_window_unconfigured_defaults_to_23_07(doc):
    """B1 : helpers créés à 00:00:00 (état réel HA à la création, PAS unknown)
    → deb==fin → la fenêtre bascule sur le défaut codé 23:00→07:00. La
    garantie eau chaude ne peut pas être « morte » par défaut."""
    st = {
        "input_datetime.molini_hc_debut": "00:00:00",
        "input_datetime.molini_hc_fin": "00:00:00",
        "sensor.molini_ptec": "unknown",
    }
    tpl = _hc_template(doc)
    assert _render(tpl, st, datetime(2026, 7, 6, 23, 30)) == "true"
    assert _render(tpl, st, datetime(2026, 7, 6, 3, 0)) == "true"
    assert _render(tpl, st, datetime(2026, 7, 6, 12, 0)) == "false"


def test_hc_ptec_base_contract_falls_back_to_window(doc):
    """M4 : contrat Base (PTEC « TH.. ») → ni HC ni HP → la fenêtre sert de
    GARANTIE (en Base la nuit coûte pareil — chauffer la nuit reste sain)."""
    st = {**BASE, "sensor.molini_ptec": "TH.."}
    tpl = _hc_template(doc)
    assert _render(tpl, st, datetime(2026, 7, 6, 2, 0)) == "true"    # fenêtre
    assert _render(tpl, st, datetime(2026, 7, 6, 14, 0)) == "false"


def test_soutirage_binary_and_reevaluable_cutoff(doc):
    """M2 : la coupure repose sur binary molini_soutirage_reseau + un trigger
    time_pattern /5 min (réévaluable — un front raté par l'anti-cycle est
    rattrapé), la condition portant le `for: 10 min`."""
    b = doc["template"][0]["binary_sensor"]
    assert any(x["unique_id"] == "molini_soutirage_reseau" for x in b)
    a = next(x for x in doc["automation"] if x["id"] == "molini_ce_surplus_fin")
    kinds = [t.get("trigger") for t in a["triggers"]]
    assert "time_pattern" in kinds and "state" in kinds
    # condition d'état avec for: 10 min sur le binaire soutirage
    conds = str(a["conditions"])
    assert "molini_soutirage_reseau" in conds and "00:10:00" in conds


def test_surplus_min_threshold_is_realistic(doc):
    """m5 : seuil surplus min 1500 W — aucun ballon ne tire moins ; empêche le
    scénario « Auto sans réglage → cyclage » sur une future box."""
    assert doc["input_number"]["molini_ce_seuil_surplus"]["min"] >= 1500
