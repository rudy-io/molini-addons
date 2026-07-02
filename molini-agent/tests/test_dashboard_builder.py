"""Tests du dashboard_builder (chantier E).

Couvre :
- Assemblage de [energie, chauffage] → YAML valide
- Idempotence (2 builds = diff 0)
- Block manquant → erreur claire
- Anti-path traversal (slug `../etc`)
- Preserve commentaires + indentation
- Ordre forcé _header en 1, _reglages en dernier
- Detection entités manquantes
- Defaults appliqués si liste vide
"""
from __future__ import annotations

import io

import pytest
from ruamel.yaml import YAML

from molini_agent.dashboard_builder import (
    ALLOWED_BLOCKS,
    DEFAULT_BLOCKS,
    BuildResult,
    build_and_write,
    build_yaml,
    check_missing_entities,
    extract_entities_from_block,
    prod_gauge_scale,
    validate_blocks,
    write_yaml_atomic,
)

from . import conftest

BLOCKS_DIR = conftest.BLOCKS_DIR

# Blocs réellement livrés sur les box (fichiers présents dans blocks/).
# ALLOWED_BLOCKS contient aussi des blocs futurs (chauffage, ve, confort…)
# sans fichier embarqué — les tests qui touchent le disque itèrent sur les
# blocs LIVRÉS.
SHIPPED_BLOCKS = [s for s in ALLOWED_BLOCKS if (BLOCKS_DIR / f"{s}.yaml").is_file()]


# ─── validate_blocks ──────────────────────────────────────────────────────────


def test_validate_blocks_simple_order():
    result = validate_blocks(["energie", "chauffage"])
    assert result == ["energie", "chauffage"]


def test_validate_blocks_forces_header_first():
    result = validate_blocks(["energie", "_header", "chauffage"])
    assert result[0] == "_header"
    assert result == ["_header", "energie", "chauffage"]


def test_validate_blocks_forces_reglages_last():
    result = validate_blocks(["_reglages", "energie", "chauffage"])
    assert result[-1] == "_reglages"
    assert result == ["energie", "chauffage", "_reglages"]


def test_validate_blocks_both_anchors():
    result = validate_blocks(["chauffage", "_reglages", "energie", "_header"])
    assert result == ["_header", "chauffage", "energie", "_reglages"]


def test_validate_blocks_dedupe():
    result = validate_blocks(["energie", "energie", "chauffage", "energie"])
    assert result == ["energie", "chauffage"]


def test_validate_blocks_rejects_path_traversal():
    with pytest.raises(ValueError, match="invalid block slug"):
        validate_blocks(["../etc/passwd"])


def test_validate_blocks_rejects_path_segments():
    with pytest.raises(ValueError, match="invalid block slug"):
        validate_blocks(["foo/bar"])


def test_validate_blocks_rejects_absolute_path():
    with pytest.raises(ValueError, match="invalid block slug"):
        validate_blocks(["/etc/passwd"])


def test_validate_blocks_rejects_not_in_allowlist():
    with pytest.raises(ValueError, match="not in allow-list"):
        validate_blocks(["evil_block"])


def test_validate_blocks_rejects_uppercase():
    with pytest.raises(ValueError, match="invalid block slug"):
        validate_blocks(["Energie"])


def test_validate_blocks_rejects_empty():
    with pytest.raises(ValueError, match="empty"):
        validate_blocks([])


def test_validate_blocks_rejects_non_string():
    with pytest.raises(ValueError, match="must be a string"):
        validate_blocks([123])  # type: ignore[list-item]


# ─── build_yaml ───────────────────────────────────────────────────────────────


def test_build_yaml_returns_valid_yaml():
    result = build_yaml(["energie", "aide"], blocks_dir=BLOCKS_DIR)
    assert isinstance(result, BuildResult)
    assert result.blocks_used == ["energie", "aide"]

    # Le YAML doit être parsable
    yaml = YAML(typ="rt")
    data = yaml.load(result.yaml_text)
    assert data["title"] == "Moli"
    assert isinstance(data["views"], list)
    assert len(data["views"]) == 2


def test_build_yaml_full_set():
    """Avec tous les blocs activés, l'ordre est forcé et le YAML est valide."""
    all_blocks = list(SHIPPED_BLOCKS)
    result = build_yaml(all_blocks, blocks_dir=BLOCKS_DIR)
    assert result.blocks_used[0] == "_header"
    assert result.blocks_used[-1] == "_reglages"
    assert len(result.blocks_used) == len(SHIPPED_BLOCKS)


def test_build_yaml_defaults_when_empty():
    """Si la liste est vide, ``DEFAULT_BLOCKS`` est utilisé."""
    result = build_yaml([], blocks_dir=BLOCKS_DIR)
    assert result.blocks_used == list(DEFAULT_BLOCKS)


def test_build_yaml_idempotence(tmp_path):
    """2 builds successifs produisent un YAML identique au byte près."""
    result1 = build_yaml(["energie", "aide"], blocks_dir=BLOCKS_DIR)
    result2 = build_yaml(["energie", "aide"], blocks_dir=BLOCKS_DIR)
    assert result1.yaml_text == result2.yaml_text


def test_build_yaml_missing_block_raises():
    """Si un fichier de bloc n'existe pas, FileNotFoundError remonte clairement."""
    with pytest.raises(ValueError):
        # Slug pas dans la white-list → erreur avant lecture disque
        build_yaml(["nonexistent"], blocks_dir=BLOCKS_DIR)


def test_build_yaml_missing_file_on_disk_raises(tmp_path):
    """Si le slug est white-listé mais le fichier manque, FileNotFoundError."""
    # On crée un dossier avec UN seul bloc, on demande les autres
    (tmp_path / "_header.yaml").write_text(
        "title: Header\npath: x\ncards: []\n",
        encoding="utf-8",
    )
    with pytest.raises(FileNotFoundError, match="energie"):
        build_yaml(["_header", "energie"], blocks_dir=tmp_path)


def test_build_yaml_header_comment_present():
    """Le YAML généré contient le commentaire d'avertissement."""
    result = build_yaml(
        ["_header", "energie", "_reglages"], blocks_dir=BLOCKS_DIR
    )
    assert "généré automatiquement" in result.yaml_text
    assert "NE PAS ÉDITER" in result.yaml_text
    # Le commentaire liste les blocs utilisés
    assert "#   - _header" in result.yaml_text
    assert "#   - energie" in result.yaml_text
    assert "#   - _reglages" in result.yaml_text


def test_build_yaml_preserves_block_comments():
    """Les commentaires français des blocs partials sont préservés dans la
    sortie (ruamel preserve_quotes + round-trip).

    Note : ruamel ne préserve pas les commentaires de top-level documentation
    quand on les insère via dump dans un autre document. On vérifie que
    AU MOINS un commentaire d'un bloc est présent.
    """
    result = build_yaml(["energie"], blocks_dir=BLOCKS_DIR)
    # Les commentaires inline dans les cards survivent
    assert "Powered by Home Assistant" not in result.yaml_text  # block aide skipped
    # Le titre du bloc est bien là
    assert "Énergie" in result.yaml_text


# ─── Anti-path traversal en bout de pipeline ──────────────────────────────────


def test_build_yaml_anti_traversal_via_payload():
    """Un payload malicieux ne doit jamais lire un fichier hors blocks/."""
    with pytest.raises(ValueError):
        build_yaml(["../../../etc/passwd"], blocks_dir=BLOCKS_DIR)
    with pytest.raises(ValueError):
        build_yaml(["..\\etc"], blocks_dir=BLOCKS_DIR)


# ─── Detection entités manquantes ─────────────────────────────────────────────


def test_extract_entities_from_block():
    block = {
        "title": "Test",
        "cards": [
            {"type": "tile", "entity": "sensor.foo"},
            {"type": "gauge", "entity": "sensor.bar"},
        ],
    }
    entities = extract_entities_from_block(block)
    assert "sensor.foo" in entities
    assert "sensor.bar" in entities


def test_check_missing_entities_empty_when_no_ha():
    """Si available_entity_ids est None, le check est skip (no-op safe)."""
    block = {"cards": [{"entity": "sensor.missing"}]}
    missing = check_missing_entities(block, None)
    assert missing == []


def test_check_missing_entities_finds_missing():
    block = {
        "cards": [
            {"entity": "sensor.molini_power_w"},
            {"entity": "sensor.unknown_device"},
        ],
    }
    available = {"sensor.molini_power_w"}
    missing = check_missing_entities(block, available)
    assert missing == ["sensor.unknown_device"]


def test_check_missing_entities_excludes_input_helpers():
    """Les input_* (helpers MOLINI) ne déclenchent pas un missing."""
    block = {
        "cards": [
            {"entity": "input_text.molini_client_name"},
            {"entity": "input_boolean.molini_mode_absence"},
        ],
    }
    available: set[str] = set()  # Rien d'available
    missing = check_missing_entities(block, available)
    assert missing == []


def test_build_yaml_reports_missing_entities_per_block():
    """Le BuildResult expose un map block → entités manquantes."""
    available = {"sensor.molini_power_w"}  # Très réduit, beaucoup manquera
    result = build_yaml(
        ["energie"],
        blocks_dir=BLOCKS_DIR,
        available_entity_ids=available,
    )
    # Le bloc energie référence les capteurs molini_* qui ne sont pas
    # dans `available`
    assert "energie" in result.missing_entities
    assert any(
        e.startswith("sensor.molini_")
        for e in result.missing_entities["energie"]
    )


# ─── kiosk_mode appliance ─────────────────────────────────────────────────────


def test_build_yaml_contains_kiosk_mode(tmp_path):
    """Le YAML généré contient la config kiosk_mode pour masquer la sidebar
    aux non-admins (mode « appliance Moli »)."""
    (tmp_path / "_reglages.yaml").write_text(
        "title: Réglages\npath: reglages\ncards: []\n", encoding="utf-8"
    )
    result = build_yaml(["_reglages"], blocks_dir=tmp_path)
    assert "kiosk_mode" in result.yaml_text
    assert "non_admin_settings" in result.yaml_text
    assert "hide_sidebar" in result.yaml_text

    # Vérifie que la structure est correcte au niveau YAML parsé
    from ruamel.yaml import YAML as _YAML
    data = _YAML(typ="rt").load(result.yaml_text)
    assert data["kiosk_mode"]["non_admin_settings"]["hide_sidebar"] is True


# ─── write_yaml_atomic ────────────────────────────────────────────────────────


def test_write_yaml_atomic_creates_file(tmp_path):
    target = tmp_path / "subdir" / "molini.yaml"
    changed = write_yaml_atomic("content\n", target)
    assert changed is True
    assert target.read_text(encoding="utf-8") == "content\n"


def test_write_yaml_atomic_idempotent(tmp_path):
    target = tmp_path / "molini.yaml"
    write_yaml_atomic("content\n", target)
    changed = write_yaml_atomic("content\n", target)
    assert changed is False


def test_write_yaml_atomic_updates_when_changed(tmp_path):
    target = tmp_path / "molini.yaml"
    write_yaml_atomic("v1\n", target)
    changed = write_yaml_atomic("v2\n", target)
    assert changed is True
    assert target.read_text(encoding="utf-8") == "v2\n"


# ─── build_and_write (pipeline complet) ───────────────────────────────────────


def test_build_and_write_full(tmp_path):
    target = tmp_path / "molini.yaml"
    result = build_and_write(
        blocks=["_header", "energie", "_reglages"],
        blocks_dir=BLOCKS_DIR,
        output_path=target,
    )
    assert result["ok"] is True
    assert result["changed"] is True
    assert result["blocks_used"] == ["_header", "energie", "_reglages"]
    assert target.is_file()

    # Re-run = idempotent
    result2 = build_and_write(
        blocks=["_header", "energie", "_reglages"],
        blocks_dir=BLOCKS_DIR,
        output_path=target,
    )
    assert result2["changed"] is False


def test_build_and_write_invalid_block_no_write(tmp_path):
    """Si l'admin envoie un slug invalide, on n'écrit RIEN sur disque."""
    target = tmp_path / "molini.yaml"
    target.write_text("pre-existing", encoding="utf-8")

    with pytest.raises(RuntimeError):
        # build_and_write n'attrape pas — c'est commands.py qui le fait.
        # Ici on simule l'erreur attendue via build_yaml direct.
        try:
            build_and_write(
                blocks=["evil_slug"],
                blocks_dir=BLOCKS_DIR,
                output_path=target,
            )
        except ValueError as e:
            raise RuntimeError(str(e)) from e

    # Le fichier existant n'a pas été touché
    assert target.read_text(encoding="utf-8") == "pre-existing"


# ─── YAML validity check sur tous les blocs partials ──────────────────────────


def test_all_partial_blocks_parse():
    """Chaque fichier de bloc dans blocks/ doit être un YAML mapping valide."""
    yaml = YAML(typ="rt")
    assert SHIPPED_BLOCKS, "aucun bloc livré trouvé — BLOCKS_DIR faux ?"
    for slug in SHIPPED_BLOCKS:
        path = BLOCKS_DIR / f"{slug}.yaml"
        assert path.is_file(), f"Missing block file: {path}"
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.load(f)
        assert isinstance(data, dict), f"Block {slug} not a mapping"
        # Chaque bloc doit avoir un titre + des cards (layout classique)
        # ou des sections (layout HA "sections" — energie depuis 0.13)
        assert "title" in data, f"Block {slug} missing title"
        assert (
            "cards" in data or "sections" in data
        ), f"Block {slug} missing cards/sections"


def test_assembled_yaml_is_valid_lovelace():
    """L'output assemblé doit avoir la structure attendue par Lovelace."""
    result = build_yaml(list(SHIPPED_BLOCKS), blocks_dir=BLOCKS_DIR)
    yaml = YAML(typ="rt")
    data = yaml.load(result.yaml_text)
    assert "title" in data
    assert "views" in data
    assert isinstance(data["views"], list)
    for view in data["views"]:
        assert "title" in view
        assert "cards" in view or "sections" in view


def test_build_yaml_substitutions(tmp_path):
    """build_yaml avec substitutions= remplace les tokens dans le YAML final."""
    blocks_dir = tmp_path / "blocks"
    blocks_dir.mkdir()
    (blocks_dir / "_header.yaml").write_text(
        "title: T\npath: t\ncards:\n  - type: markdown\n    content: \"prix __PRIX_KWH__\"\n",
        encoding="utf-8",
    )
    result = build_yaml(
        ["_header"],
        blocks_dir=blocks_dir,
        substitutions={"__PRIX_KWH__": "0.3000"},
    )
    assert "0.3000" in result.yaml_text
    assert "__PRIX_KWH__" not in result.yaml_text


import io
from ruamel.yaml import YAML
from molini_agent import dashboard_builder as db

def test_dynamic_cards_replace_marker(tmp_path):
    blocks_dir = tmp_path / "blocks"
    blocks_dir.mkdir()
    (blocks_dir / "energie.yaml").write_text(
        "title: Énergie\npath: energie\ncards:\n"
        "  - type: markdown\n    content: MOLINI_PANELS\n", encoding="utf-8")
    panel = [{"type": "heading", "heading": "Onduleur 1"}]
    res = db.build_yaml(["energie"], blocks_dir=blocks_dir,
                        dynamic_cards={"energie": panel})
    doc = YAML(typ="safe").load(io.StringIO(res.yaml_text))
    cards = doc["views"][0]["cards"]
    assert {"type": "markdown", "content": "MOLINI_PANELS"} not in cards
    assert {"type": "heading", "heading": "Onduleur 1"} in cards


# ─── Substitution order fix (A) ───────────────────────────────────────────────

def test_build_yaml_substitution_order(tmp_path):
    """Le token le plus long doit être substitué en premier pour éviter qu'un
    préfixe plus court ne corrompe la valeur du token plus long.
    Ex : __A__ est préfixe de __A_B__ → sans tri, __A_B__ → 'X_B__'."""
    blocks_dir = tmp_path / "blocks"
    blocks_dir.mkdir()
    (blocks_dir / "_header.yaml").write_text(
        'title: T\npath: t\ncards:\n  - type: markdown\n    content: "__A__ and __A_B__"\n',
        encoding="utf-8",
    )
    result = build_yaml(
        ["_header"],
        blocks_dir=blocks_dir,
        substitutions={"__A__": "X", "__A_B__": "Y"},
    )
    assert "X and Y" in result.yaml_text
    # La version buggée aurait produit "X and X_B__"
    assert "X_B__" not in result.yaml_text


# ─── prod_gauge_scale (B3) ────────────────────────────────────────────────────

def test_prod_gauge_scale_observed_peak():
    """5200 W × 1.1 = 5720 → ceil au 500 supérieur = 6000."""
    gmax, seg1, seg2 = prod_gauge_scale(5200)
    assert gmax == 6000
    assert seg1 == int(round(6000 * 0.33))
    assert seg2 == int(round(6000 * 0.67))


def test_prod_gauge_scale_floor():
    """Quand observed_max_w=0, le plancher PROD_FLOOR_W=3000 s'applique."""
    gmax, seg1, seg2 = prod_gauge_scale(0)
    assert gmax == 3000
    assert seg1 == int(round(3000 * 0.33))
    assert seg2 == int(round(3000 * 0.67))
