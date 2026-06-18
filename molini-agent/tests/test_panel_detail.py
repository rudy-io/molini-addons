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

def test_label_for_inverter():
    assert pd.inverter_label("inverter", 0) == "Onduleur 1"
    assert pd.inverter_label("inverter_2", 1) == "Onduleur 2"

def test_label_for_izypower():
    lbl = pd.inverter_label("sensor.izypower_cloud_maison_35486_55180000aa2e", 2)
    assert lbl == "Micro-onduleur 3"

def test_build_cards_structure():
    cards = pd.build_panel_cards(CAROLE)
    # 1 heading + 1 grid par onduleur (4 détectés : 2 SolarMan + 2 IzyPower)
    headings = [c for c in cards if c.get("type") == "heading"]
    grids = [c for c in cards if c.get("type") == "grid"]
    assert len(headings) == 4 and len(grids) == 4
    # chaque grid contient des gauge référençant les entity_id réels
    first_grid = grids[0]
    assert all(g["type"] == "gauge" for g in first_grid["cards"])
    assert first_grid["cards"][0]["entity"].startswith("sensor.")
    # gauge bornée et en W
    assert first_grid["cards"][0]["max"] == 600
    assert first_grid["cards"][0]["unit"] == "W"

def test_build_cards_empty():
    assert pd.build_panel_cards({"sensor.x"}) == []

def test_build_cards_per_type_numbering():
    cards = pd.build_panel_cards(CAROLE)
    headings = [c["heading"] for c in cards if c.get("type") == "heading"]
    # numérotation par type : les 2 micro-onduleurs sont 1 et 2, pas 3 et 4
    assert headings == ["Onduleur 1", "Onduleur 2", "Micro-onduleur 1", "Micro-onduleur 2"]
