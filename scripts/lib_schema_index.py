#!/usr/bin/env python3
"""Shared schema-index discovery helpers."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_INDEX_ENV = "INTERNAL_DATA_QUERY_SCHEMA_INDEX"
SCHEMA_INDEX_CONFIG = Path("data-query-work/schema/schema-index.config.json")
PREFERRED_INDEX_NAMES = ("unified_schema_index.json", "all_sources_schema_index.json")


@dataclass(frozen=True)
class SchemaIndexDiscovery:
    path: Path | None
    exists: bool
    source: str
    candidates: list[Path]
    ambiguous: bool = False
    message: str = ""


def normalize_path(path: Path, *, root: Path, base: Path | None = None) -> Path:
    expanded = Path(path).expanduser()
    if expanded.is_absolute():
        return expanded
    if base:
        return (base / expanded).resolve()
    return (root / expanded).resolve()


def dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def pick_preferred(candidates: list[Path]) -> tuple[Path | None, bool]:
    unique = dedupe_paths(candidates)
    if not unique:
        return None, False
    if len(unique) == 1:
        return unique[0], False
    for preferred in PREFERRED_INDEX_NAMES:
        matches = [path for path in unique if path.name == preferred]
        if matches:
            return matches[0], False
    return None, True


def config_candidates(config_path: Path, root: Path) -> list[Path]:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"schema index config must be a JSON object: {config_path}")
    values: list[Any] = []
    for key in ("schema_index", "schema_index_path", "file", "path"):
        value = data.get(key)
        if value:
            values.append(value)
    for key in ("schema_indexes", "schema_index_files", "files", "candidates"):
        value = data.get(key)
        if isinstance(value, list):
            values.extend(item for item in value if item)
    return [
        normalize_path(Path(str(value)), root=root, base=config_path.parent)
        for value in values
        if isinstance(value, (str, os.PathLike))
    ]


def default_schema_candidates(root: Path) -> list[Path]:
    workspace_schema = root / "data-query-work" / "schema"
    reference_schema = root / "references" / "schema-kb"
    workspace_candidates: list[Path] = []
    if workspace_schema.exists():
        workspace_candidates.extend(sorted(workspace_schema.glob("*_schema_index.json")))
    if workspace_candidates:
        return dedupe_paths(workspace_candidates)
    candidates: list[Path] = []
    if reference_schema.exists():
        candidates.extend(sorted(reference_schema.glob("*_schema_index.json")))
    return dedupe_paths(candidates)


def discover_schema_index(root: Path, explicit_file: Path | None = None) -> SchemaIndexDiscovery:
    root = root.resolve()
    if explicit_file:
        path = normalize_path(explicit_file, root=root)
        return SchemaIndexDiscovery(
            path=path,
            exists=path.exists(),
            source="file",
            candidates=[path],
            message="" if path.exists() else f"schema index not found: {path}",
        )

    env_value = os.environ.get(SCHEMA_INDEX_ENV)
    if env_value:
        path = normalize_path(Path(env_value), root=root)
        return SchemaIndexDiscovery(
            path=path,
            exists=path.exists(),
            source="env",
            candidates=[path],
            message="" if path.exists() else f"schema index from {SCHEMA_INDEX_ENV} not found: {path}",
        )

    cfg_path = root / SCHEMA_INDEX_CONFIG
    if cfg_path.exists():
        candidates = config_candidates(cfg_path, root)
        existing = [path for path in candidates if path.exists()]
        if not candidates:
            return SchemaIndexDiscovery(
                path=None,
                exists=False,
                source="config",
                candidates=[],
                message=f"schema index config has no path entries: {cfg_path}",
            )
        if not existing:
            return SchemaIndexDiscovery(
                path=candidates[0],
                exists=False,
                source="config",
                candidates=candidates,
                message=f"schema index from config not found: {candidates[0]}",
            )
        selected, ambiguous = pick_preferred(existing)
        return SchemaIndexDiscovery(
            path=selected,
            exists=bool(selected),
            source="config",
            candidates=existing,
            ambiguous=ambiguous,
            message=ambiguous_message(existing) if ambiguous else "",
        )

    candidates = default_schema_candidates(root)
    selected, ambiguous = pick_preferred(candidates)
    return SchemaIndexDiscovery(
        path=selected,
        exists=bool(selected),
        source="default",
        candidates=candidates,
        ambiguous=ambiguous,
        message=ambiguous_message(candidates) if ambiguous else "",
    )


def ambiguous_message(candidates: list[Path]) -> str:
    rendered = ", ".join(str(path) for path in candidates)
    return f"multiple schema indexes found; specify --file/--from-schema-index: {rendered}"


def load_schema_index(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"schema index not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("schema index must be a JSON object")
    return data
