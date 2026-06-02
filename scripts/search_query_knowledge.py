#!/usr/bin/env python3
"""Search repo-native query knowledge files."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from lib_workspace import resolve_knowledge_root, warn_if_needed


CURRENT_SCHEMA_VERSION = "1.0"
DEFAULT_EXCLUDED_STATUS = {"draft", "candidate", "deprecated"}
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


def is_expired(item: dict[str, Any], today: date | None = None) -> bool:
    expires_at = parse_date(item.get("expires_at"))
    return bool(expires_at and expires_at < (today or date.today()))


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v is not None]
    return [str(value)]


def load_markdown(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 4 :]
    data = yaml.safe_load(raw) or {}
    return (data if isinstance(data, dict) else {}), body


def load_item(path: Path) -> tuple[dict[str, Any], str] | None:
    if path.name in SKIP_NAMES:
        return None
    if path.suffix.lower() == ".md":
        data, body = load_markdown(path)
    elif path.suffix.lower() in {".yaml", ".yml"}:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8", errors="ignore")) or {}
        data, body = (loaded if isinstance(loaded, dict) else {}), ""
    else:
        return None
    if not data.get("id"):
        return None
    data["_path"] = path
    return data, body


def iter_items(root: Path) -> list[tuple[dict[str, Any], str]]:
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


def text_matches(query: str, item: dict[str, Any], body: str) -> bool:
    if not query:
        return True
    haystack = " ".join(
        [
            str(item.get("id", "")),
            str(item.get("domain", "")),
            " ".join(as_list(item.get("metric"))),
            str(item.get("grain", "")),
            " ".join(as_list(item.get("source"))),
            body,
        ]
    ).lower()
    return query.lower() in haystack


def value_matches(value: Any, expected: str | None) -> bool:
    if expected is None:
        return True
    expected_lower = expected.lower()
    return any(expected_lower == item.lower() for item in as_list(value))


def confidence_matches(value: Any, expected: str | None) -> bool:
    if expected is None:
        return True
    actual = str(value or "").lower()
    if expected.lower().startswith(">="):
        threshold = expected[2:].strip().lower()
        return CONFIDENCE_ORDER.get(actual, 0) >= CONFIDENCE_ORDER.get(threshold, 99)
    return actual == expected.lower()


def effective_confidence(item: dict[str, Any]) -> str:
    confidence = str(item.get("confidence") or "low").lower()
    if as_list(item.get("conflicts_with")):
        return ORDER_CONFIDENCE.get(max(CONFIDENCE_ORDER.get(confidence, 1) - 1, 1), "low")
    return confidence


def conflict_summary(item: dict[str, Any], by_id: dict[str, dict[str, Any]], root: Path) -> str:
    refs = as_list(item.get("conflicts_with"))
    if not refs:
        return ""
    parts = []
    for ref in refs:
        other = by_id.get(ref)
        if other:
            rel = other["_path"].relative_to(root).as_posix()
            parts.append(f"{ref}(status={other.get('status')}, confidence={other.get('confidence')}, path={rel})")
        else:
            parts.append(f"{ref}(missing)")
    return "; ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Search data-query-work/knowledge.")
    parser.add_argument("query", nargs="?", default="", help="Keyword to search.")
    parser.add_argument("--status", help="Filter by lifecycle status.")
    parser.add_argument("--domain", help="Filter by domain.")
    parser.add_argument("--metric", help="Filter by metric.")
    parser.add_argument("--grain", help="Filter by grain.")
    parser.add_argument("--source", help="Filter by source.")
    parser.add_argument("--confidence", help="Filter by confidence, e.g. high or >=medium.")
    parser.add_argument("--include-candidate", action="store_true", help="Include candidate items.")
    parser.add_argument("--include-deprecated", action="store_true", help="Include deprecated items.")
    parser.add_argument("--include-draft", action="store_true", help="Include draft items.")
    parser.add_argument("--include-expired", action="store_true", help="Include expired items.")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Skill root directory.",
    )
    args = parser.parse_args()

    excluded = set(DEFAULT_EXCLUDED_STATUS)
    if args.include_candidate:
        excluded.discard("candidate")
    if args.include_deprecated:
        excluded.discard("deprecated")
    if args.include_draft:
        excluded.discard("draft")

    hits = 0
    root = args.root.resolve()
    items = iter_items(root)
    by_id = {str(item.get("id")): item for item, _body in items if item.get("id")}
    for item, body in items:
        status = str(item.get("status", "")).lower()
        if not args.status and status in excluded:
            continue
        if args.status and status != args.status.lower():
            continue
        if not args.include_expired and is_expired(item):
            continue
        if not value_matches(item.get("domain"), args.domain):
            continue
        if not value_matches(item.get("metric"), args.metric):
            continue
        if not value_matches(item.get("grain"), args.grain):
            continue
        if not value_matches(item.get("source"), args.source):
            continue
        effective = effective_confidence(item)
        if not confidence_matches(effective, args.confidence):
            continue
        if not text_matches(args.query, item, body):
            continue
        rel = item["_path"].relative_to(root).as_posix()
        expired = " expired" if is_expired(item) else ""
        conflicts = conflict_summary(item, by_id, root)
        conflict_suffix = f" | conflicts_with={conflicts}" if conflicts else ""
        print(
            f"{item.get('id')} | {status}{expired} | confidence={item.get('confidence')} "
            f"| effective_confidence={effective} | domain={item.get('domain', '')} "
            f"| metric={','.join(as_list(item.get('metric')))} | {rel}{conflict_suffix}"
        )
        hits += 1
        if hits >= args.limit:
            break

    if hits == 0:
        print("No query knowledge hits.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
