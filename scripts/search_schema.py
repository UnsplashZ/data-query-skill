#!/usr/bin/env python3
"""Search bundled schema KB and print table/field oriented results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_unified(root: Path) -> dict[str, Any]:
    path = root / "references" / "sql-query-method-internal" / "references" / "schema-kb" / "unified_schema_index.json"
    if not path.exists():
        raise FileNotFoundError(f"schema index not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def lower(value: Any) -> str:
    return str(value or "").lower()


def iter_matches(data: dict[str, Any], args: argparse.Namespace):
    query = lower(args.query)
    table_filter = lower(args.table)
    field_filter = lower(args.field)
    engine_filter = lower(args.engine)
    tables_by_engine = data.get("tables") or {}

    for engine, tables in tables_by_engine.items():
        if engine_filter and engine_filter != lower(engine):
            continue
        for table_name, meta in (tables or {}).items():
            table_blob = " ".join(
                [
                    table_name,
                    str(meta.get("comment") or ""),
                    str(meta.get("database") or ""),
                    str(meta.get("engine") or ""),
                ]
            )
            if table_filter and table_filter not in lower(table_name):
                continue

            columns = meta.get("columns") or []
            table_level_match = bool(query and query in lower(table_blob))
            if not columns:
                if table_level_match:
                    yield {
                        "engine": engine,
                        "database": meta.get("database", ""),
                        "table": table_name,
                        "field": "",
                        "type": "",
                        "comment": meta.get("comment", ""),
                        "source_file": "unified_schema_index.json",
                    }
                continue

            for col in columns:
                field = col.get("name") or ""
                col_blob = " ".join([field, str(col.get("type") or ""), str(col.get("comment") or "")])
                if field_filter and field_filter not in lower(field):
                    continue
                if query and not (query in lower(table_blob) or query in lower(col_blob)):
                    continue
                yield {
                    "engine": engine,
                    "database": meta.get("database", ""),
                    "table": table_name,
                    "field": field,
                    "type": col.get("type", ""),
                    "comment": col.get("comment", "") or meta.get("comment", ""),
                    "source_file": "unified_schema_index.json",
                }


def print_table(rows: list[dict[str, Any]]) -> None:
    headers = ["engine", "database", "table", "field", "type", "comment", "source_file"]
    print(" | ".join(headers))
    print(" | ".join(["---"] * len(headers)))
    for row in rows:
        print(" | ".join(str(row.get(h, "")).replace("\n", " ")[:180] for h in headers))


def main() -> int:
    parser = argparse.ArgumentParser(description="Search schema KB by table, field, engine, or keyword.")
    parser.add_argument("query", nargs="?", default="", help="Keyword to search in table/field/comment.")
    parser.add_argument("--table", help="Filter by table name substring.")
    parser.add_argument("--field", help="Filter by field name substring.")
    parser.add_argument("--engine", choices=["odps", "clickhouse"], help="Filter by engine/source.")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Skill root directory.",
    )
    args = parser.parse_args()

    data = load_unified(args.root)
    rows = []
    for item in iter_matches(data, args):
        rows.append(item)
        if len(rows) >= args.limit:
            break
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    elif rows:
        print_table(rows)
    else:
        print("No schema hits.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
