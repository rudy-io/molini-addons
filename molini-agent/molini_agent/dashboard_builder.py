"""Assembleur de dashboard Lovelace modulaire (chantier E).

Charge des blocs YAML partials depuis ``ha-config/dashboards/blocks/`` et
les assemble en un dashboard Lovelace complet écrit dans
``/config/dashboards/molini.yaml`` (côté client).

Principes :
- ``_header`` est toujours premier dans l'ordre des vues (forcé).
- ``_reglages`` est toujours dernier (forcé).
- Tous les autres blocs apparaissent dans l'ordre demandé par l'admin.
- White-list stricte des slugs reçus → anti-path traversal (``../etc``,
  ``foo/bar``, etc.).
- Idempotent : re-run avec le même set de blocs ne modifie pas le fichier
  (octet pour octet identique).
- ``ruamel.yaml`` préserve les commentaires + l'indentation + l'ordre.
- Détecte les entités manquantes via l'API HA → log warning + bloc
  rendu avec placeholder. **Pas de blocage** : le dashboard reste
  fonctionnel même si une partie des entités attendues n'existe pas.

Path écriture absolu fixe : ``/config/dashboards/molini.yaml``. Jamais
d'interpolation avec un input user. Le slug ``blocks`` est white-listé.
"""
from __future__ import annotations

import io
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from ruamel.yaml import YAML

log = logging.getLogger("molini_agent.dashboard_builder")


# ─── White-list des blocs ─────────────────────────────────────────────────────
# Tout slug doit matcher ce set sinon ``build_yaml`` lève une ValueError.
# Le mapping est volontairement explicite — on ne fait pas de scan auto sur
# le dossier pour éviter qu'un attaquant qui poserait un fichier supplémentaire
# puisse le faire référencer.
ALLOWED_BLOCKS: tuple[str, ...] = (
    "_header",
    "energie",
    "chauffage",
    "ve",
    "confort",
    "securite",
    "multimedia",
    "aide",
    "_reglages",
)

# Blocs avec position figée — l'ordre transmis par l'admin est respecté
# pour les autres, mais ces deux-là sont sortis et replacés.
FORCED_FIRST = "_header"
FORCED_LAST = "_reglages"

# Defaults appliqués si la liste de blocs est vide ou si la colonne DB
# n'a jamais été renseignée pour un client.
DEFAULT_BLOCKS: tuple[str, ...] = (
    "_header",
    "energie",
    "chauffage",
    "aide",
    "_reglages",
)


# ─── Path resolution ──────────────────────────────────────────────────────────
# Le path d'écriture est résolu via une env var pour pouvoir tester en local
# sans toucher à ``/config`` (chemin HAOS réel).
DEFAULT_OUTPUT_PATH = "/config/dashboards/molini.yaml"
DEFAULT_BLOCKS_DIR = os.environ.get(
    "MOLINI_DASHBOARD_BLOCKS_DIR",
    "/config/dashboards/blocks",
)


# Slug d'un bloc — uniquement alphanum + underscore. Validé en plus de la
# white-list pour rendre toute construction de path traversal impossible
# au cas où la white-list serait étendue plus tard.
_SLUG_RE = re.compile(r"^[a-z_][a-z0-9_]*$")

# ─── Marqueur de cartes dynamiques ───────────────────────────────────────────
PANEL_MARKER = "MOLINI_PANELS"


def _replace_marker(card_list: list, cards: list[dict]) -> list:
    """Remplace la carte-marqueur MOLINI_PANELS par `cards` dans une liste de cartes."""
    out: list = []
    for c in card_list:
        if isinstance(c, dict) and c.get("type") == "markdown" and c.get("content") == PANEL_MARKER:
            out.extend(cards)
        else:
            out.append(c)
    return out


def _inject_dynamic_cards(view: dict, cards: list[dict]) -> None:
    """Remplace la carte-marqueur MOLINI_PANELS par `cards`.

    Gère les deux layouts : masonry (``view['cards']``) et sections
    (``view['sections'][*]['cards']``)."""
    if isinstance(view.get("cards"), list):
        view["cards"] = _replace_marker(view["cards"], cards)
    sections = view.get("sections")
    if isinstance(sections, list):
        for sec in sections:
            if isinstance(sec, dict) and isinstance(sec.get("cards"), list):
                sec["cards"] = _replace_marker(sec["cards"], cards)


@dataclass(frozen=True)
class BuildResult:
    """Sortie de ``build_yaml`` — exposée pour les tests + l'agent."""

    yaml_text: str
    blocks_used: list[str]
    missing_entities: dict[str, list[str]]  # block_slug → entités manquantes


# ─── YAML loader/dumper ───────────────────────────────────────────────────────
# round_trip pour garder commentaires + ordre.
def _yaml() -> YAML:
    y = YAML(typ="rt")
    y.preserve_quotes = True
    y.indent(mapping=2, sequence=4, offset=2)
    y.width = 4096  # évite que ruamel coupe une longue ligne
    return y


def _load_block(blocks_dir: Path, slug: str) -> dict[str, Any]:
    """Charge un bloc YAML depuis le dossier blocks/.

    Lève FileNotFoundError si le bloc n'existe pas sur disque.
    """
    path = blocks_dir / f"{slug}.yaml"
    if not path.is_file():
        raise FileNotFoundError(
            f"Block file not found: {path} (slug={slug})"
        )
    with open(path, "r", encoding="utf-8") as f:
        data = _yaml().load(f)
    if not isinstance(data, dict):
        raise ValueError(
            f"Block {slug} must be a YAML mapping at top-level, got {type(data).__name__}"
        )
    return data


# ─── Detection entités manquantes ─────────────────────────────────────────────
# Regex naïve mais suffisante pour scanner les entity_id référencés dans
# un YAML : on cherche les patterns ``domain.something`` (light.foo,
# sensor.bar, etc.). Volontairement strict — on évite les jinja inline.
_ENTITY_RE = re.compile(
    r"\b(sensor|binary_sensor|light|switch|cover|scene|climate|"
    r"alarm_control_panel|camera|media_player|input_text|input_number|"
    r"input_boolean|input_select|input_datetime)\.[a-z0-9_]+\b"
)


def extract_entities_from_block(block_data: dict[str, Any]) -> set[str]:
    """Scanne un bloc et extrait tous les entity_id référencés.

    Utilisé par ``check_missing_entities`` pour identifier les blocs qui
    référencent des entités absentes côté HA.

    Note : ``findall`` avec un seul groupe nommé renverrait juste le
    domaine — on utilise ``finditer`` pour avoir le match complet.
    """
    buf = io.StringIO()
    _yaml().dump(block_data, buf)
    text = buf.getvalue()
    return {m.group(0) for m in _ENTITY_RE.finditer(text)}


def check_missing_entities(
    block_data: dict[str, Any],
    available_entity_ids: set[str] | None,
) -> list[str]:
    """Retourne les entity_id du bloc qui ne sont pas dans la liste HA.

    Si ``available_entity_ids`` est ``None`` (cas où l'API HA n'est pas
    joignable), on n'a aucune info → on retourne ``[]`` (no-op safe).
    """
    if available_entity_ids is None:
        return []
    referenced = extract_entities_from_block(block_data)
    return sorted(
        eid
        for eid in referenced
        if eid not in available_entity_ids
        # On exclut input_* / scene.molini_* / sensor.molini_* qui sont
        # gérés par packages MOLINI — ils peuvent être absents si pas
        # encore reload, c'est normal au premier déploiement.
        and not eid.startswith("input_")
        and not eid.startswith("scene.molini_")
    )


# ─── Validation ───────────────────────────────────────────────────────────────
def validate_blocks(blocks: Iterable[str]) -> list[str]:
    """Valide la liste de blocs reçue côté admin.

    - Tous les slugs doivent matcher la white-list ``ALLOWED_BLOCKS``.
    - Doublons → conservés une seule fois (dédupe en gardant 1er ordre).
    - Si la liste résultante est vide, lève ValueError (un dashboard sans
      bloc n'a aucun sens).

    Retourne la liste normalisée (slugs uniques dans l'ordre, avec
    ``_header`` forcé en 1 et ``_reglages`` forcé en dernier).
    """
    seen: set[str] = set()
    ordered: list[str] = []
    for slug in blocks:
        if not isinstance(slug, str):
            raise ValueError(f"block slug must be a string, got {type(slug).__name__}")
        if not _SLUG_RE.match(slug):
            raise ValueError(
                f"invalid block slug {slug!r} — only [a-z_][a-z0-9_]* allowed"
            )
        if slug not in ALLOWED_BLOCKS:
            raise ValueError(
                f"block {slug!r} not in allow-list "
                f"(allowed: {', '.join(ALLOWED_BLOCKS)})"
            )
        if slug in seen:
            continue
        seen.add(slug)
        ordered.append(slug)

    if not ordered:
        raise ValueError("blocks list is empty — at least one block required")

    # Force position de _header et _reglages
    body = [s for s in ordered if s not in (FORCED_FIRST, FORCED_LAST)]
    final = []
    if FORCED_FIRST in ordered:
        final.append(FORCED_FIRST)
    final.extend(body)
    if FORCED_LAST in ordered:
        final.append(FORCED_LAST)
    return final


# ─── Build core ───────────────────────────────────────────────────────────────
def build_yaml(
    blocks: Iterable[str],
    blocks_dir: str | os.PathLike[str] | None = None,
    available_entity_ids: set[str] | None = None,
    dynamic_cards: dict[str, list[dict[str, Any]]] | None = None,
) -> BuildResult:
    """Assemble la liste de blocs en un dashboard Lovelace complet.

    Args:
        blocks: liste de slugs (validés par ``validate_blocks``).
        blocks_dir: dossier qui contient les ``{slug}.yaml`` partials.
            Par défaut ``MOLINI_DASHBOARD_BLOCKS_DIR`` ou
            ``/config/dashboards/blocks``.
        available_entity_ids: liste des entity_id dispo côté HA pour
            détecter les blocs qui référencent des entités absentes.
            Si None, le check est skip.

    Returns:
        BuildResult avec le YAML final, les blocks utilisés, et le map
        des entités manquantes par bloc.

    Raises:
        ValueError: liste invalide / slug hors white-list.
        FileNotFoundError: un fichier de bloc manque sur disque.
    """
    blocks_list = list(blocks) if blocks else list(DEFAULT_BLOCKS)
    validated = validate_blocks(blocks_list)
    bdir = Path(blocks_dir or DEFAULT_BLOCKS_DIR)

    # Construction du document Lovelace
    yaml = _yaml()
    doc: dict[str, Any] = {}
    doc["title"] = "Moli"
    views = []
    missing_by_block: dict[str, list[str]] = {}

    for slug in validated:
        block = _load_block(bdir, slug)
        if dynamic_cards and slug in dynamic_cards:
            _inject_dynamic_cards(block, dynamic_cards[slug])
        miss = check_missing_entities(block, available_entity_ids)
        if miss:
            log.warning(
                "Block %s references missing entities: %s", slug, ", ".join(miss)
            )
            missing_by_block[slug] = miss
        views.append(block)
    doc["views"] = views

    # Sérialisation
    buf = io.StringIO()
    buf.write(
        "# Moli — dashboard Lovelace généré automatiquement\n"
        "# Construit par molini_agent/dashboard_builder.py — NE PAS ÉDITER À LA MAIN.\n"
        "# Source de vérité : la liste de blocs côté admin Moli\n"
        "# (clients.dashboard_blocks). Re-générer via la commande\n"
        "# rebuild_dashboard depuis /admin/clients/[id].\n"
        "#\n"
        "# Blocs activés (ordre forcé _header → ... → _reglages) :\n"
    )
    for slug in validated:
        buf.write(f"#   - {slug}\n")
    buf.write("\n")
    yaml.dump(doc, buf)
    text = buf.getvalue()

    return BuildResult(
        yaml_text=text,
        blocks_used=validated,
        missing_entities=missing_by_block,
    )


def write_yaml_atomic(yaml_text: str, output_path: str | os.PathLike[str]) -> bool:
    """Écrit le YAML de façon atomique (.tmp + os.replace).

    Retourne ``True`` si le contenu a changé, ``False`` si identique
    (idempotence — pas d'écriture inutile).
    """
    output = Path(output_path)
    if output.is_file():
        try:
            existing = output.read_text(encoding="utf-8")
        except OSError:
            existing = None
        if existing == yaml_text:
            log.info("dashboard unchanged at %s (%d bytes)", output, len(yaml_text))
            return False

    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".tmp")
    tmp.write_text(yaml_text, encoding="utf-8")
    os.replace(tmp, output)
    log.info("dashboard written to %s (%d bytes)", output, len(yaml_text))
    return True


def build_and_write(
    blocks: Iterable[str],
    blocks_dir: str | os.PathLike[str] | None = None,
    output_path: str | os.PathLike[str] = DEFAULT_OUTPUT_PATH,
    available_entity_ids: set[str] | None = None,
    dynamic_cards: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Pipeline complet : validate → build → write atomic.

    Utilisé par le handler ``rebuild_dashboard`` de l'agent. Renvoie un
    dict sérialisable pour le résultat de la commande admin.
    """
    result = build_yaml(blocks, blocks_dir=blocks_dir, available_entity_ids=available_entity_ids, dynamic_cards=dynamic_cards)
    changed = write_yaml_atomic(result.yaml_text, output_path)
    return {
        "ok": True,
        "blocks_used": result.blocks_used,
        "missing_entities": result.missing_entities,
        "changed": changed,
        "output_path": str(output_path),
        "size_bytes": len(result.yaml_text),
    }
