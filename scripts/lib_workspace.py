#!/usr/bin/env python3
"""Shared workspace path helpers for data-query scripts."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

WORKSPACE_DIR = "data-query-work"
KNOWLEDGE_DIR = "knowledge"
DEFAULT_KNOWLEDGE_ROOT = Path(WORKSPACE_DIR) / KNOWLEDGE_DIR

KNOWLEDGE_MARKER_FILES = ("OWNERS.yaml",)
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


@dataclass(frozen=True)
class KnowledgeRoot:
    path: Path
    warning: str | None = None


def is_knowledge_root(path: Path) -> bool:
    return all((path / marker).exists() for marker in KNOWLEDGE_MARKER_FILES)


def default_knowledge_root(root: Path) -> Path:
    return root / DEFAULT_KNOWLEDGE_ROOT


def resolve_knowledge_root(root: Path, *, mode: str = "read") -> KnowledgeRoot:
    """Resolve the data-query-work/knowledge root."""
    if mode not in {"read", "write"}:
        raise ValueError(f"unsupported mode: {mode}")

    root = root.resolve()
    if is_knowledge_root(root):
        return KnowledgeRoot(root)

    return KnowledgeRoot(default_knowledge_root(root))


def warn_if_needed(selection: KnowledgeRoot) -> None:
    if selection.warning:
        print(f"WARN: {selection.warning}", file=sys.stderr)


def ensure_knowledge_skeleton(knowledge_root: Path) -> None:
    knowledge_root.mkdir(parents=True, exist_ok=True)
    for subdir in KNOWLEDGE_SUBDIRS:
        (knowledge_root / subdir).mkdir(parents=True, exist_ok=True)

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
