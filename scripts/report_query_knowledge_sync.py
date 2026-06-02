#!/usr/bin/env python3
"""Report sync health for data-query-work/knowledge."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from lib_workspace import resolve_knowledge_root, warn_if_needed


CURRENT_SCHEMA_VERSION = "1.0"
SKIP_NAMES = {"OWNERS.yaml", "promotion-log.md", "README.md", ".gitkeep"}
CONFIDENCE_ORDER = {"low": 1, "medium": 2, "high": 3}
ORDER_CONFIDENCE = {value: key for key, value in CONFIDENCE_ORDER.items()}


def parse_date(value: Any) -> date | None:
    if value in (None, "", "null"):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v not in (None, "")]
    return [str(value)] if str(value) else []


def effective_confidence(item: dict[str, Any]) -> str:
    confidence = str(item.get("confidence") or "low").lower()
    if as_list(item.get("conflicts_with")):
        return ORDER_CONFIDENCE.get(max(CONFIDENCE_ORDER.get(confidence, 1) - 1, 1), "low")
    return confidence


def load_markdown(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    loaded = yaml.safe_load(text[4:end]) or {}
    return loaded if isinstance(loaded, dict) else {}


def load_item(path: Path) -> dict[str, Any] | None:
    if path.name in SKIP_NAMES:
        return None
    if path.suffix.lower() == ".md":
        data = load_markdown(path)
    elif path.suffix.lower() in {".yaml", ".yml"}:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8", errors="ignore")) or {}
        data = loaded if isinstance(loaded, dict) else {}
    else:
        return None
    if not data:
        return None
    data["_path"] = path
    return data


def iter_items(root: Path) -> list[dict[str, Any]]:
    selection = resolve_knowledge_root(root, mode="read")
    warn_if_needed(selection)
    knowledge_root = selection.path
    if not knowledge_root.exists():
        return []
    return [item for p in sorted(knowledge_root.rglob("*")) if p.is_file() for item in [load_item(p)] if item]


def parse_promotion_log(root: Path) -> set[tuple[str, str]]:
    selection = resolve_knowledge_root(root, mode="read")
    log_path = selection.path / "promotion-log.md"
    if not log_path.exists():
        return set()
    entries: set[tuple[str, str]] = set()
    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.startswith("|") or "---" in line or "timestamp" in line:
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) >= 4:
            entries.add((cols[1], cols[3]))
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Report data-query-work/knowledge sync health.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Skill root directory.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    knowledge_root = resolve_knowledge_root(root, mode="read").path
    items = iter_items(root)
    by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_id[str(item.get("id", ""))].append(item)
    promotion_entries = parse_promotion_log(root)

    print("# Query Knowledge Sync Report")
    print(f"root: {knowledge_root}")
    print(f"items: {len(items)}")

    duplicate_ids = {item_id: entries for item_id, entries in by_id.items() if item_id and len(entries) > 1}
    print(f"\n## Duplicate IDs ({len(duplicate_ids)})")
    for item_id, entries in duplicate_ids.items():
        paths = ", ".join(e["_path"].relative_to(root).as_posix() for e in entries)
        print(f"- {item_id}: {paths}")

    expired_approved = [
        item
        for item in items
        if str(item.get("status", "")).lower() == "approved"
        and (expires_at := parse_date(item.get("expires_at")))
        and expires_at < date.today()
    ]
    print(f"\n## Expired Approved ({len(expired_approved)})")
    for item in expired_approved:
        print(f"- {item.get('id')}: expires_at={item.get('expires_at')} path={item['_path'].relative_to(root).as_posix()}")

    conflicts = [item for item in items if as_list(item.get("conflicts_with"))]
    print(f"\n## Conflicts ({len(conflicts)})")
    for item in conflicts:
        print(
            f"- {item.get('id')} confidence={item.get('confidence')} "
            f"effective_confidence={effective_confidence(item)} "
            f"conflicts_with={','.join(as_list(item.get('conflicts_with')))}"
        )

    old_schema = [item for item in items if item.get("schema_version") != CURRENT_SCHEMA_VERSION]
    print(f"\n## Old Schema ({len(old_schema)})")
    for item in old_schema:
        print(f"- {item.get('id')}: schema_version={item.get('schema_version')} path={item['_path'].relative_to(root).as_posix()}")

    missing_log = [
        item
        for item in items
        if str(item.get("status", "")).lower() in {"reviewed", "approved", "deprecated"}
        and (str(item.get("id", "")), str(item.get("status", "")).lower()) not in promotion_entries
    ]
    print(f"\n## Missing Promotion Log ({len(missing_log)})")
    for item in missing_log:
        print(f"- {item.get('id')}: status={item.get('status')} path={item['_path'].relative_to(root).as_posix()}")

    if not any([duplicate_ids, expired_approved, conflicts, old_schema, missing_log]):
        print("\nPASS: no sync issues found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
