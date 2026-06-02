#!/usr/bin/env python3
"""Shared workspace path helpers for data-query scripts."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

WORKSPACE_DIR = "data-query-work"
KNOWLEDGE_DIR = "knowledge"
DEFAULT_KNOWLEDGE_ROOT = Path(WORKSPACE_DIR) / KNOWLEDGE_DIR
LEGACY_KNOWLEDGE_ROOT = Path("data-query-knowledge")

KNOWLEDGE_MARKER_FILES = ("manifest.yaml", "OWNERS.yaml")
KNOWLEDGE_SUBDIRS = (
    "candidates/observations",
    "candidates/query-verified",
    "candidates/reusable-patterns",
    "candidates/user-assertions",
    "metrics",
    "sources",
    "joins",
    "golden-queries",
    "semantic-memory",
    "review-records",
    "deprecated",
)


class LegacyKnowledgeWriteError(RuntimeError):
    """Raised when a write would target the old top-level knowledge path."""


@dataclass(frozen=True)
class KnowledgeRoot:
    path: Path
    is_legacy: bool
    warning: str | None = None


def is_knowledge_root(path: Path) -> bool:
    return all((path / marker).exists() for marker in KNOWLEDGE_MARKER_FILES)


def default_knowledge_root(root: Path) -> Path:
    return root / DEFAULT_KNOWLEDGE_ROOT


def legacy_knowledge_root(root: Path) -> Path:
    return root / LEGACY_KNOWLEDGE_ROOT


def _is_legacy_path(path: Path) -> bool:
    return path.name == LEGACY_KNOWLEDGE_ROOT.name


def resolve_knowledge_root(root: Path, *, mode: str = "read") -> KnowledgeRoot:
    """Resolve query knowledge root.

    Reads prefer the new workspace path and can fall back to the legacy path.
    Writes always use data-query-work/knowledge and never create or mutate the
    legacy top-level data-query-knowledge directory.
    """
    if mode not in {"read", "write"}:
        raise ValueError(f"unsupported mode: {mode}")

    root = root.resolve()
    if is_knowledge_root(root):
        is_legacy = _is_legacy_path(root)
        if mode == "write" and is_legacy:
            raise LegacyKnowledgeWriteError(
                "Refusing to write to legacy data-query-knowledge/. "
                "Use data-query-work/knowledge/ for new writes."
            )
        return KnowledgeRoot(root, is_legacy=is_legacy)

    new_root = default_knowledge_root(root)
    old_root = legacy_knowledge_root(root)

    if mode == "write":
        warning = None
        if old_root.exists() and not new_root.exists():
            warning = (
                "Legacy data-query-knowledge/ exists and is read-only compatibility input; "
                "new writes will create data-query-work/knowledge/."
            )
        return KnowledgeRoot(new_root, is_legacy=False, warning=warning)

    if new_root.exists():
        warning = None
        if old_root.exists():
            warning = (
                "Both data-query-work/knowledge/ and legacy data-query-knowledge/ exist; "
                "using data-query-work/knowledge/ and leaving legacy read-only."
            )
        return KnowledgeRoot(new_root, is_legacy=False, warning=warning)

    if old_root.exists():
        return KnowledgeRoot(
            old_root,
            is_legacy=True,
            warning=(
                "Using legacy data-query-knowledge/ as read-only compatibility input. "
                "Migrate it to data-query-work/knowledge/ before writing new shared knowledge."
            ),
        )

    return KnowledgeRoot(new_root, is_legacy=False)


def warn_if_needed(selection: KnowledgeRoot) -> None:
    if selection.warning:
        print(f"WARN: {selection.warning}", file=sys.stderr)


def ensure_knowledge_skeleton(knowledge_root: Path) -> None:
    knowledge_root.mkdir(parents=True, exist_ok=True)
    for subdir in KNOWLEDGE_SUBDIRS:
        (knowledge_root / subdir).mkdir(parents=True, exist_ok=True)

    manifest = knowledge_root / "manifest.yaml"
    if not manifest.exists():
        manifest.write_text(
            "schema_version: 1.0\n"
            "knowledge_root: data-query-work/knowledge\n"
            "domains: []\n"
            "owners: []\n"
            "last_validated_at: null\n",
            encoding="utf-8",
        )

    owners = knowledge_root / "OWNERS.yaml"
    if not owners.exists():
        owners.write_text("owners: []\nreviewers: []\napprovers: []\n", encoding="utf-8")

    promotion_log = knowledge_root / "promotion-log.md"
    if not promotion_log.exists():
        promotion_log.write_text(
            "# Query Knowledge Promotion Log\n\n"
            "| timestamp | id | from_status | to_status | actor | reviewer | evidence | notes |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- |\n",
            encoding="utf-8",
        )


def writable_knowledge_root(root: Path) -> KnowledgeRoot:
    selection = resolve_knowledge_root(root, mode="write")
    ensure_knowledge_skeleton(selection.path)
    return selection
