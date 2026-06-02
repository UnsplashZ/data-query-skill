#!/usr/bin/env python3
"""Validate repo-native query knowledge files."""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from lib_workspace import resolve_knowledge_root, warn_if_needed


SKIP_NAMES = {"OWNERS.yaml", "promotion-log.md", "README.md", ".gitkeep"}
VALID_STATUS = {"draft", "candidate", "reviewed", "approved", "deprecated"}
VALID_CONFIDENCE = {"low", "medium", "high"}
REQUIRED_FIELDS = [
    "id",
    "schema_version",
    "status",
    "created_by",
    "reviewed_by",
    "approved_by",
    "source_status",
    "confidence",
    "risk_level",
    "expires_at",
    "supersedes",
    "conflicts_with",
    "validation_evidence",
    "last_verified_at",
    "sync_notes",
    "maturity",
    "capture_trigger",
    "source_interaction",
]


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
    items = []
    for path in sorted(knowledge_root.rglob("*")):
        if path.is_file():
            item = load_item(path)
            if item:
                items.append(item)
    return items


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
        if len(cols) >= 4 and cols[1] and cols[3]:
            entries.add((cols[1], cols[3]))
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate data-query-work/knowledge files.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Skill root directory.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    items = iter_items(root)
    ids = {str(item.get("id")) for item in items if item.get("id")}
    promotion_entries = parse_promotion_log(root)
    ok = True

    knowledge_root = resolve_knowledge_root(root, mode="read").path
    if not (knowledge_root / "OWNERS.yaml").exists():
        print("FAIL: data-query-work/knowledge/OWNERS.yaml missing")
        ok = False

    seen: dict[str, Path] = {}
    for item in items:
        path = item["_path"]
        rel = path.relative_to(root).as_posix()
        item_id = str(item.get("id", ""))
        if not item_id:
            print(f"FAIL {rel}: missing id")
            ok = False
        elif item_id in seen:
            print(f"FAIL {rel}: duplicate id also in {seen[item_id].relative_to(root).as_posix()}")
            ok = False
        else:
            seen[item_id] = path

        for field in REQUIRED_FIELDS:
            if field not in item:
                print(f"FAIL {rel}: missing required field {field}")
                ok = False

        status = str(item.get("status", "")).lower()
        if status not in VALID_STATUS:
            print(f"FAIL {rel}: invalid status {item.get('status')}")
            ok = False
        if str(item.get("confidence", "")).lower() not in VALID_CONFIDENCE:
            print(f"FAIL {rel}: invalid confidence {item.get('confidence')}")
            ok = False
        if not as_list(item.get("created_by")):
            print(f"FAIL {rel}: created_by is required")
            ok = False
        if status in {"reviewed", "approved"} and not as_list(item.get("reviewed_by")):
            print(f"FAIL {rel}: reviewed_by is required for {status}")
            ok = False
        if status == "approved" and not as_list(item.get("approved_by")):
            print(f"FAIL {rel}: approved_by is required for approved")
            ok = False
        if status in {"reviewed", "approved"} and not as_list(item.get("validation_evidence")):
            print(f"FAIL {rel}: validation_evidence is required for {status}")
            ok = False

        for field in ("expires_at", "last_verified_at"):
            value = item.get(field)
            if value not in (None, "", "null") and not parse_date(value):
                print(f"FAIL {rel}: {field} must be ISO date or null")
                ok = False
        expires_at = parse_date(item.get("expires_at"))
        if status == "approved" and expires_at and expires_at < date.today():
            print(f"WARN {rel}: approved item is expired ({expires_at.isoformat()})")

        for field in ("supersedes", "conflicts_with"):
            refs = as_list(item.get(field))
            missing = [ref for ref in refs if ref not in ids]
            if missing:
                print(f"FAIL {rel}: {field} references unknown id(s): {', '.join(missing)}")
                ok = False
            if item_id and item_id in refs:
                print(f"FAIL {rel}: {field} references itself")
                ok = False

        if status in {"reviewed", "approved", "deprecated"} and (item_id, status) not in promotion_entries:
            print(f"WARN {rel}: no promotion-log entry for status {status}")

    if ok:
        print(f"PASS: query knowledge validation passed ({len(items)} item files).")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
