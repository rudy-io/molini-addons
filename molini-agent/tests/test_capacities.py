"""Tests du store high-water-mark des capacités PV (auto-calibrage dashboard)."""
from molini_agent import capacities


def _states(**kv):
    return [{"entity_id": e, "state": s} for e, s in kv.items()]


def test_load_missing_returns_empty(tmp_path):
    assert capacities.load_capacities(str(tmp_path / "nope.json")) == {}


def test_update_from_states_tracks_pv_and_prod(tmp_path):
    p = str(tmp_path / "cap.json")
    merged = capacities.update_from_states(
        _states(**{
            "sensor.molini_solaire_production": "5200",
            "sensor.inverter_pv1_power": "430",
            "sensor.izypower_x_pv2": "455",
            # non suivis :
            "sensor.inverter_pv1_voltage": "33",       # voltage, pas power
            "sensor.inverter_pv_power": "820",          # agrégat (pas de digit)
            "sensor.something_else": "999",
        }),
        path=p,
    )
    assert merged["sensor.molini_solaire_production"] == 5200.0
    assert merged["sensor.inverter_pv1_power"] == 430.0
    assert merged["sensor.izypower_x_pv2"] == 455.0
    assert "sensor.inverter_pv1_voltage" not in merged
    assert "sensor.inverter_pv_power" not in merged
    assert "sensor.something_else" not in merged


def test_high_water_mark_never_decreases(tmp_path):
    p = str(tmp_path / "cap.json")
    capacities.update_from_states(_states(**{"sensor.molini_solaire_production": "5200"}), path=p)
    # une valeur plus basse plus tard ne doit PAS écraser le pic
    merged = capacities.update_from_states(
        _states(**{"sensor.molini_solaire_production": "1200"}), path=p
    )
    assert merged["sensor.molini_solaire_production"] == 5200.0
    # une valeur plus haute le met à jour
    merged = capacities.update_from_states(
        _states(**{"sensor.molini_solaire_production": "5800"}), path=p
    )
    assert merged["sensor.molini_solaire_production"] == 5800.0


def test_persisted_and_reloaded(tmp_path):
    p = str(tmp_path / "cap.json")
    capacities.update_from_states(_states(**{"sensor.inverter_pv1_power": "440"}), path=p)
    assert capacities.load_capacities(p)["sensor.inverter_pv1_power"] == 440.0


def test_update_from_maxes_merges(tmp_path):
    p = str(tmp_path / "cap.json")
    capacities.update_from_states(_states(**{"sensor.inverter_pv1_power": "440"}), path=p)
    merged = capacities.update_from_maxes(
        {"sensor.inverter_pv1_power": 500.0, "sensor.molini_solaire_production": 6000.0}, path=p
    )
    assert merged["sensor.inverter_pv1_power"] == 500.0
    assert merged["sensor.molini_solaire_production"] == 6000.0


def test_ignores_non_numeric_states(tmp_path):
    p = str(tmp_path / "cap.json")
    merged = capacities.update_from_states(
        _states(**{"sensor.molini_solaire_production": "unavailable"}), path=p
    )
    assert merged == {}
