#!/usr/bin/env python3
"""Migrate query knowledge files by adding missing fields only."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


CURRENT_SCHEMA_VERSION = "1.0"
KNOWLEDGE_DIR = "data-query-knowledge"
SKIP_NAMES = {"manifest.yaml", "OWNERS.yaml", "promotion-log.md", "README.md", ".gitkeep"}
DEFAULTS: dict[str, Any] = {
    "schema_version": CURRENT_SCHEMA_VERSION,
    "status": "draft",
    "created_by": "",
    "reviewed_by": [],
    "approved_by": [],
    "source_status": "unknown",
    "confidence": "low",
    "risk_level": "medium",
    "expires_at": None,
    "supersedes": [],
    "conflicts_with": [],
    "validation_evidence": [],
    "last_verified_at": None,
    "sync_notes": [],
    "maturity": "draft",
    "capture_trigger": "migration",
    "source_interaction": [],
}


def load_markdown(path: Path) -> tuple[dict[str, Any], str, bool]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.startswith("---\n"):
        return {}, text, False
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text, False
    loaded = yaml.safe_load(text[4:end]) or {}
    return (loaded if isinstance(loaded, dict) else {}), text[end + 4 :], True


def dump_markdown(path: Path, data: dict[str, Any], body: str) -> None:
    frontmatter = yaml.safe_dump(data, allow_unicode=True, sort_keys=False).strip()
    path.write_text(f"---\n{frontmatter}\n---{body}", encoding="utf-8")


def load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8", errors="ignore")) or {}
    return loaded if isinstance(loaded, dict) else {}


def iter_paths(root: Path) -> list[Path]:
    knowledge_root = root / KNOWLEDGE_DIR
    if not knowledge_root.exists():
        return []
    return [
        path
        for path in sorted(knowledge_root.rglob("*"))
        if path.is_file() and path.name not in SKIP_NAMES and path.suffix.lower() in {".md", ".yaml", ".yml"}
    ]


def migrate_data(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    changed = dict(data)
    added: list[str] = []
    if "id" not in changed:
        return changed, added
    for key, default in DEFAULTS.items():
        if key not in changed:
            changed[key] = list(default) if isinstance(default, list) else default
            added.append(key)
    return changed, added


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate data-query-knowledge files by adding missing fields.")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing files.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Skill root directory.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    changed_count = 0
    for path in iter_paths(root):
        if path.suffix.lower() == ".md":
            data, body, has_frontmatter = load_markdown(path)
            if not has_frontmatter:
                print(f"SKIP {path.relative_to(root).as_posix()}: markdown has no YAML front matter")
                continue
            migrated, added = migrate_data(data)
            if added:
                changed_count += 1
                print(f"{'DRY-RUN ' if args.dry_run else ''}MIGRATE {path.relative_to(root).as_posix()}: add {', '.join(added)}")
                if not args.dry_run:
                    dump_markdown(path, migrated, body)
        else:
            data = load_yaml(path)
            migrated, added = migrate_data(data)
            if added:
                changed_count += 1
                print(f"{'DRY-RUN ' if args.dry_run else ''}MIGRATE {path.relative_to(root).as_posix()}: add {', '.join(added)}")
                if not args.dry_run:
                    path.write_text(yaml.safe_dump(migrated, allow_unicode=True, sort_keys=False), encoding="utf-8")

    if changed_count == 0:
        print("PASS: no migration needed.")
    else:
        print(f"{'DRY-RUN ' if args.dry_run else ''}SUMMARY: {changed_count} file(s) need/received additive field migration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
