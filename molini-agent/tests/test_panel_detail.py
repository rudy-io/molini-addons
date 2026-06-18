# molini-agent/tests/test_panel_detail.py
from molini_agent import panel_detail as pd

CAROLE = {
    "sensor.inverter_pv1_power", "sensor.inverter_pv2_power",
    "sensor.inverter_2_pv1_power", "sensor.inverter_2_pv2_power",
    "sensor.inverter_2_pv3_power", "sensor.inverter_2_pv4_power",
    "sensor.izypower_cloud_maison_35486_55180000aa2e_pv1",
    "sensor.izypower_cloud_maison_35486_55180000aa2e_pv2",
    "sensor.izypower_cloud_maison_35486_60580000c3e6_pv1",
    "sensor.light_salon", "sensor.inverter_2_power",  # bruit : ne doit pas matcher
}

def test_detect_groups_panels_by_inverter():
    groups = pd.detect_panels(CAROLE)
    # clé = préfixe (tout ce qui précède _pvN, "sensor." inclus) ; valeurs = eids triés
    assert groups["sensor.inverter"] == ["sensor.inverter_pv1_power", "sensor.inverter_pv2_power"]
    assert len(groups["sensor.inverter_2"]) == 4
    assert "sensor.izypower_cloud_maison_35486_55180000aa2e" in groups
    assert len(groups) == 4  # 2 SolarMan + 2 IzyPower (aa2e, c3e6)
    flat = [e for v in groups.values() for e in v]
    assert "sensor.inverter_2_power" not in flat  # total AC exclu
    assert "sensor.light_salon" not in flat

def test_detect_empty_when_no_pv():
    assert pd.detect_panels({"sensor.temperature"}) == {}
