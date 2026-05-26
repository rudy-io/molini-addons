"""Idempotent deep-merge patch for Home Assistant configuration.yaml.

This module is intentionally **defensive**: only a strict white-list of top-level
keys can be patched. HA's ``configuration.yaml`` is loaded by HA Core as Python
code in some integrations (e.g. ``python_script:``), so an arbitrary patch
endpoint would be a remote code execution surface. We therefore restrict patches
to integrations known to be pure data (``http``, ``recorder``, ``frontend``,
``logger``, ``logbook``, ``recorder``, ``api``, ``zone``, ``default_config``,
``homeassistant.customize`` is intentionally **not** included).

The merge is performed via ``ruamel.yaml`` to preserve comments and ordering.

Properties guaranteed:

- **Idempotent**: applying the same patch twice yields the same file bytes.
- **Deep merge**: nested mappings are merged key by key (``http.use_x_forwarded_for``
  does not erase a pre-existing ``http.ssl_certificate``).
- **List merge**: lists are merged as **set union, order-preserving**. This is
  the desired semantic for ``http.trusted_proxies`` (we want to add our CIDR
  without erasing the user's manual entries).
- **Comments preserved**: ruamel round-trip mode keeps user comments intact.
- **No side-effects on dry-run**: a separate ``compute_patch`` function returns
  the new content without writing.

Returns a structured dict so the caller (``bootstrap.py``) can include it in
the agent → central report.
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
from datetime import datetime
from io import StringIO
from typing import Any, Iterable

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

log = logging.getLogger("molini_agent.yaml_patch")

# White-list of top-level integrations we accept to patch.
# Anything outside this set is rejected with ``forbidden_key``.
#
# Important: ``python_script``, ``shell_command``, ``rest_command``,
# ``command_line``, ``homeassistant`` (allow_*), ``automation`` are **NOT**
# in the allow-list — these can execute code or shells when reloaded.
PATCHABLE_TOP_KEYS: frozenset[str] = frozenset(
    {
        "http",
        "recorder",
        "frontend",
        "logger",
        "logbook",
        "api",
        "zone",
        "default_config",
        "discovery",
        "mobile_app",
        "system_health",
        "person",
        "sun",
        "tts",
        "media_source",
    }
)


class YamlPatchError(RuntimeError):
    """Raised when the requested patch violates security policy."""


def _yaml() -> YAML:
    y = YAML()
    y.preserve_quotes = True
    y.indent(mapping=2, sequence=4, offset=2)
    y.width = 4096
    return y


def _validate_top_keys(patch: dict[str, Any]) -> None:
    """Reject any top-level key outside the white-list."""
    bad = [k for k in patch.keys() if k not in PATCHABLE_TOP_KEYS]
    if bad:
        raise YamlPatchError(
            f"forbidden_key:{bad[0]}: only {sorted(PATCHABLE_TOP_KEYS)} are patchable"
        )


def _is_mapping(v: Any) -> bool:
    return isinstance(v, dict)


def _is_list(v: Any) -> bool:
    return isinstance(v, list)


def _merge_list_union(existing: list, incoming: Iterable) -> tuple[list, bool]:
    """Add elements from ``incoming`` to ``existing`` if not already present.

    Returns (new_list, mutated). Order of pre-existing items is preserved;
    new items are appended at the end. ``mutated`` tells whether at least one
    item was added — used to decide whether the file actually needs to be written.
    """
    mutated = False
    out = list(existing)
    seen = list(existing)
    for item in incoming:
        if item not in seen:
            out.append(item)
            seen.append(item)
            mutated = True
    return out, mutated


def _deep_merge(target: Any, patch: Any) -> bool:
    """Mutate ``target`` in place with values from ``patch`` (deep merge).

    Returns True if ``target`` was actually mutated. Used by callers to
    short-circuit a no-op write (idempotence guarantee).

    Rules:
    - dict + dict   → recursive merge
    - list + list   → set-union, order-preserving
    - scalar + any  → overwrite (only if value differs)
    """
    mutated = False
    for k, v in patch.items():
        if k not in target:
            target[k] = v
            mutated = True
            continue
        existing = target[k]
        if _is_mapping(existing) and _is_mapping(v):
            if _deep_merge(existing, v):
                mutated = True
        elif _is_list(existing) and _is_list(v):
            new_list, list_mutated = _merge_list_union(existing, v)
            if list_mutated:
                # Replace contents while keeping ruamel commented seq type if any
                if isinstance(existing, CommentedSeq):
                    existing.clear()
                    existing.extend(new_list)
                else:
                    target[k] = new_list
                mutated = True
        else:
            if existing != v:
                target[k] = v
                mutated = True
    return mutated


def compute_patch(
    current_text: str, patch: dict[str, Any]
) -> tuple[str, bool, dict[str, Any]]:
    """Return (new_text, changed, report).

    Pure function: no filesystem side-effect. ``report`` is a JSON-friendly
    summary of what was modified (caller adds it to the heartbeat).
    """
    _validate_top_keys(patch)

    y = _yaml()
    if current_text.strip():
        try:
            doc = y.load(current_text)
        except Exception as e:
            raise YamlPatchError(f"yaml_parse_error: {e}") from e
        if doc is None:
            doc = CommentedMap()
    else:
        doc = CommentedMap()

    if not _is_mapping(doc):
        raise YamlPatchError(
            f"yaml_root_not_mapping: got {type(doc).__name__}, expected mapping"
        )

    mutated = _deep_merge(doc, patch)

    if not mutated:
        return current_text, False, {"changed": False, "applied_keys": []}

    buf = StringIO()
    y.dump(doc, buf)
    new_text = buf.getvalue()

    return new_text, True, {"changed": True, "applied_keys": sorted(patch.keys())}


def apply_patch_to_file(
    path: str, patch: dict[str, Any], make_backup: bool = True
) -> dict[str, Any]:
    """Apply ``patch`` to the YAML file at ``path`` atomically + idempotently.

    - Creates a ``.bak-YYYYMMDD`` snapshot before first modification (per day)
    - Writes to ``<path>.tmp`` then renames (atomic on POSIX, best-effort on Win)
    - Skips the write entirely if the patch produces no change

    Returns a structured report dict.
    """
    if not os.path.isabs(path):
        raise YamlPatchError(f"path_not_absolute: {path}")

    existed = os.path.exists(path)
    current_text = ""
    if existed:
        with open(path, "r", encoding="utf-8") as f:
            current_text = f.read()

    new_text, changed, report = compute_patch(current_text, patch)
    report["path"] = path
    report["existed"] = existed

    if not changed:
        log.info("yaml_patch: %s already up-to-date", path)
        return report

    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    if existed and make_backup:
        bak = f"{path}.bak-{datetime.now().strftime('%Y%m%d')}"
        if not os.path.exists(bak):
            try:
                shutil.copy2(path, bak)
                report["backup"] = bak
            except OSError as e:
                log.warning("yaml_patch: backup failed (%s) — continuing", e)

    fd, tmp = tempfile.mkstemp(prefix=".molini_yaml_patch_", dir=parent or None)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_text)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise

    log.info(
        "yaml_patch: wrote %s (applied %s)", path, ", ".join(sorted(patch.keys()))
    )
    return report
