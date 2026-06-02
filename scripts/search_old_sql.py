#!/usr/bin/env python3
"""Search optional external historical SQL with snippets and context."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path


def default_index_candidates(root: Path) -> list[Path]:
    candidates: list[Path] = []
    env_path = os.environ.get("INTERNAL_DATA_QUERY_OLD_SQL_INDEX")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.extend(
        [
            root / "data-query-work" / "historical-sql" / "historical-sql-index.csv",
        ]
    )
    return candidates


def resolve_index(root: Path, index_path: Path | None) -> Path | None:
    if index_path:
        return index_path.expanduser()
    for candidate in default_index_candidates(root):
        if candidate.exists():
            return candidate
    return None


def load_index(index_csv: Path | None) -> list[dict[str, str]]:
    if not index_csv or not index_csv.exists():
        return []
    with index_csv.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def resolve_sql_path(root: Path, index_csv: Path | None, sql_dir: Path | None, row: dict[str, str]) -> Path:
    normalized_path = row.get("normalized_path", "")
    if sql_dir:
        return sql_dir.expanduser() / Path(normalized_path).name
    candidate = root / normalized_path
    if candidate.exists():
        return candidate
    if index_csv:
        return index_csv.parent / normalized_path
    return candidate


def snippet(lines: list[str], lineno: int, context: int) -> str:
    start = max(1, lineno - context)
    end = min(len(lines), lineno + context)
    parts = []
    for idx in range(start, end + 1):
        prefix = ">" if idx == lineno else " "
        parts.append(f"{prefix}{idx}: {lines[idx - 1].strip()}")
    return "\\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Search optional external historical SQL.")
    parser.add_argument("query", help="Keyword to search in metadata and SQL body.")
    parser.add_argument("--domain", help="Filter by business domain tag.")
    parser.add_argument("--trust", help="Filter by trust level: medium, low, needs-review.")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--context", type=int, default=2)
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--index", type=Path, help="External historical SQL index CSV.")
    parser.add_argument("--sql-dir", type=Path, help="Directory containing SQL files referenced by the index.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Skill root directory.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    index_csv = resolve_index(root, args.index)
    rows = load_index(index_csv)
    if not rows:
        print("No historical SQL index configured. Provide --index or set INTERNAL_DATA_QUERY_OLD_SQL_INDEX.")
        return 0
    needle = args.query.lower()
    hits = 0

    for row in rows:
        if args.domain and args.domain.lower() not in row.get("domain_tags", "").lower():
            continue
        if args.trust and args.trust.lower() != row.get("trust_level", "").lower():
            continue
        sql_path = resolve_sql_path(root, index_csv, args.sql_dir, row)
        metadata = " ".join([row.get("id", ""), row.get("domain_tags", ""), row.get("source_hint", ""), row.get("notes", "")])
        metadata_match = needle in metadata.lower()
        if args.metadata_only:
            if not metadata_match:
                continue
            print(f"{row['id']} | {row['trust_level']} | {row['domain_tags']} | {row['normalized_path']} | source={row.get('source_hint','')}")
            hits += 1
            if hits >= args.limit:
                return 0
            continue

        if not sql_path.exists():
            continue
        lines = sql_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        matched_lines = [i for i, line in enumerate(lines, start=1) if needle in line.lower()]
        if not matched_lines and metadata_match:
            print(f"{row['id']} | {row['trust_level']} | {row['domain_tags']} | {row['normalized_path']} | metadata match")
            hits += 1
            if hits >= args.limit:
                return 0
            continue
        for lineno in matched_lines:
            print(f"{row['id']} | {row['trust_level']} | {row['domain_tags']} | {row['normalized_path']}:{lineno}")
            print(snippet(lines, lineno, args.context))
            print()
            hits += 1
            if hits >= args.limit:
                return 0

    if hits == 0:
        print("No historical SQL hits.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
