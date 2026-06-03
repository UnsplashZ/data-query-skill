#!/usr/bin/env python3
"""Search an optional external schema index and print table/field oriented results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from lib_schema_index import discover_schema_index, load_schema_index


def lower(value: Any) -> str:
    return str(value or "").lower()


def iter_matches(data: dict[str, Any], args: argparse.Namespace, source_file: str):
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
                        "source_file": source_file,
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
                    "source_file": source_file,
                }


def print_table(rows: list[dict[str, Any]]) -> None:
    headers = ["engine", "database", "table", "field", "type", "comment", "source_file"]
    print(" | ".join(headers))
    print(" | ".join(["---"] * len(headers)))
    for row in rows:
        print(" | ".join(str(row.get(h, "")).replace("\n", " ")[:180] for h in headers))


def print_discovery_error(message: str, candidates: list[Path], as_json: bool) -> None:
    if as_json:
        print(
            json.dumps(
                {
                    "error": message,
                    "schema_index_candidates": [str(path) for path in candidates],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="Search an optional external schema index by table, field, engine, or keyword.")
    parser.add_argument("query", nargs="?", default="", help="Keyword to search in table/field/comment.")
    parser.add_argument("--table", help="Filter by table name substring.")
    parser.add_argument("--field", help="Filter by field name substring.")
    parser.add_argument("--engine", help="Filter by engine/source.")
    parser.add_argument("--file", type=Path, help="Schema index JSON. Overrides env/config/default discovery.")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Target repository root directory.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    discovery = discover_schema_index(root, args.file)
    if discovery.ambiguous:
        print_discovery_error(discovery.message, discovery.candidates, args.json)
        return 2
    if not discovery.path or not discovery.exists:
        message = discovery.message or "No schema index configured. Provide --file or set INTERNAL_DATA_QUERY_SCHEMA_INDEX."
        if discovery.path:
            print_discovery_error(message, discovery.candidates, args.json)
            return 2
        if args.json:
            print("[]")
        else:
            print(message)
        return 0

    data = load_schema_index(discovery.path)
    rows = []
    for item in iter_matches(data, args, discovery.path.name):
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
