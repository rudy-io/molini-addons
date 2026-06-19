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

def test_group_by_installation():
    groups = pd.group_panels(CAROLE)
    # 2 installations (marque), pas 4 onduleurs
    assert [g["label"] for g in groups] == ["Onduleur SolarMan", "Micro-onduleurs IzyPower"]
    assert len(groups[0]["panels"]) == 6  # inverter (2) + inverter_2 (4) fusionnés
    assert len(groups[1]["panels"]) == 3  # aa2e (2) + c3e6 (1) dans cette fixture
    assert groups[0]["panels"][0]["name"] == "P1"
    assert groups[0]["panels"][0]["eid"] == "sensor.inverter_pv1_power"

def test_build_cards_button_card_fill():
    cards = pd.build_panel_cards(CAROLE)
    headings = [c["heading"] for c in cards if c.get("type") == "heading"]
    grids = [c for c in cards if c.get("type") == "grid"]
    assert headings == ["Onduleur SolarMan", "Micro-onduleurs IzyPower"]
    assert len(grids) == 2
    first = grids[0]["cards"][0]
    assert first["type"] == "custom:button-card"
    assert first["entity"].startswith("sensor.")
    # le fond est un template button-card qui se remplit selon la prod
    bg = next(s["background"] for s in first["styles"]["card"] if "background" in s)
    assert "linear-gradient" in bg and "entity.state" in bg

def test_build_cards_empty():
    assert pd.build_panel_cards({"sensor.x"}) == []
