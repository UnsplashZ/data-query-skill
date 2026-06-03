#!/usr/bin/env python3
"""Sample latest rows from schema-index tables and write masked outputs."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib_data_sources import bool_value, load_profile
from lib_masking import FIELD_NAME_PATTERNS, assert_no_high_risk_text, field_name_findings, mask_records, residual_scan_file
from lib_schema_index import discover_schema_index, load_schema_index
from lib_table_list import parse_table_list


LATEST_PRIORITY = [
    ("updated_at", "high", "exact update timestamp"),
    ("update_time", "high", "exact update timestamp"),
    ("modified_at", "high", "exact modify timestamp"),
    ("modify_time", "high", "exact modify timestamp"),
    ("created_at", "medium", "business/create timestamp"),
    ("create_time", "medium", "business/create timestamp"),
    ("event_time", "medium", "business event timestamp"),
    ("finish_time", "medium", "business finish timestamp"),
    ("pay_time", "medium", "business payment timestamp"),
    ("dt", "medium", "partition date"),
    ("date", "medium", "partition date"),
    ("biz_date", "medium", "partition date"),
    ("pt", "medium", "partition field"),
    ("id", "low", "monotonic id fallback"),
    ("version", "low", "version fallback"),
]


def slug(value: Any) -> str:
    text = str(value or "unknown").strip()
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", text)
    return text.strip(".-") or "unknown"


def quote_clickhouse(value: str) -> str:
    return "`" + value.replace("`", "``") + "`"


def date_stem() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def columns_for(entry: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(col) for col in entry.get("columns") or []]


def infer_latest_column(columns: list[dict[str, Any]]) -> tuple[str, str, str]:
    names = {str(col.get("name") or "").lower(): str(col.get("name") or "") for col in columns}
    for candidate, confidence, reason in LATEST_PRIORITY:
        if candidate in names:
            return names[candidate], confidence, reason
    return "", "none", "no known latest/order column found; using LIMIT only"


def has_column(columns: list[dict[str, Any]], name: str) -> bool:
    return any(str(col.get("name") or "").lower() == name.lower() for col in columns)


def is_local_table(table: str) -> bool:
    lowered = table.lower()
    return lowered.endswith("_local") or lowered.startswith("local_") or ".local_" in lowered


def build_clickhouse_sql(entry: dict[str, Any], rows: int, include_local: bool) -> tuple[str, dict[str, Any]]:
    database = str(entry.get("database") or "")
    table = str(entry.get("table") or "")
    columns = columns_for(entry)
    if is_local_table(table) and not include_local:
        return "", {"status": "skipped", "error": "local table skipped by default"}
    latest, confidence, reason = infer_latest_column(columns)
    table_expr = f"{quote_clickhouse(database)}.{quote_clickhouse(table)}" if database else quote_clickhouse(table)
    rules: list[str] = []
    if table.startswith("drh_"):
        table_expr += " FINAL"
        rules.append("drh_final")
    where_parts: list[str] = []
    if has_column(columns, "_sign"):
        where_parts.append("_sign > 0")
        rules.append("sign_positive")
    where_clause = " AND ".join(where_parts)
    order_by = f"{quote_clickhouse(latest)} DESC" if latest else ""
    sql_parts = [f"SELECT * FROM {table_expr}"]
    if where_clause:
        sql_parts.append(f"WHERE {where_clause}")
    if order_by:
        sql_parts.append(f"ORDER BY {order_by}")
    sql_parts.append(f"LIMIT {int(rows)}")
    status = "sampled" if latest else "limit_only"
    if not latest:
        status = "missing_latest_column"
    return " ".join(sql_parts), {
        "status": status,
        "latest_column": latest,
        "latest_confidence": confidence,
        "latest_reason": reason,
        "where_clause": where_clause,
        "order_by": order_by,
        "clickhouse_rules_applied": ",".join(rules),
    }


def schema_field_risks(entry: dict[str, Any], key: str) -> list[dict[str, str]]:
    risks: list[dict[str, str]] = []
    for column in columns_for(entry):
        name = str(column.get("name") or "")
        for kind, pattern in FIELD_NAME_PATTERNS:
            if pattern.search(name):
                risks.append({"table": key, "field": name, "kind": kind})
                break
    return risks


def build_generic_sql(entry: dict[str, Any], rows: int) -> tuple[str, dict[str, Any]]:
    database = str(entry.get("database") or "")
    table = str(entry.get("table") or "")
    columns = columns_for(entry)
    latest, confidence, reason = infer_latest_column(columns)
    table_expr = f"{database}.{table}" if database else table
    order_by = f"{latest} DESC" if latest else ""
    sql = f"SELECT * FROM {table_expr}"
    if order_by:
        sql += f" ORDER BY {order_by}"
    sql += f" LIMIT {int(rows)}"
    return sql, {
        "status": "sampled" if latest else "missing_latest_column",
        "latest_column": latest,
        "latest_confidence": confidence,
        "latest_reason": reason,
        "where_clause": "",
        "order_by": order_by,
        "clickhouse_rules_applied": "",
    }


def selected_entries(schema: dict[str, Any], engine: str, table_plan: dict[str, Any] | None, include_local: bool) -> list[tuple[str, dict[str, Any]]]:
    tables = dict((schema.get("tables") or {}).get(engine) or {})
    if not table_plan:
        return sorted(tables.items())
    else:
        wanted = {str(item.get("canonical")) for item in table_plan.get("requested", []) if not item.get("duplicate_of")}
        wanted_tables = {str(item.get("table")) for item in table_plan.get("requested", []) if not item.get("duplicate_of")}
        return [
            (key, entry)
            for key, entry in sorted(tables.items())
            if key in wanted or str(entry.get("table")) in wanted_tables
        ]


def missing_requested(schema: dict[str, Any], engine: str, table_plan: dict[str, Any] | None) -> list[str]:
    if not table_plan:
        return []
    tables = dict((schema.get("tables") or {}).get(engine) or {})
    existing_keys = set(tables)
    existing_names = {str(entry.get("table")) for entry in tables.values()}
    missing: list[str] = []
    for item in table_plan.get("requested", []):
        if item.get("duplicate_of"):
            continue
        canonical = str(item.get("canonical") or "")
        table = str(item.get("table") or "")
        if canonical not in existing_keys and table not in existing_names:
            missing.append(canonical)
    return missing


def run_clickhouse_sample(cfg: dict[str, Any], sql: str) -> list[dict[str, Any]]:
    from clickhouse_driver import Client  # type: ignore

    client = Client(
        host=cfg.get("host"),
        port=int(cfg.get("port") or 9000),
        database=cfg.get("database"),
        user=cfg.get("username") or cfg.get("user"),
        password=cfg.get("password"),
        secure=bool_value(cfg.get("secure")),
    )
    data, meta = client.execute(sql, with_column_types=True)
    columns = [item[0] for item in meta]
    return [dict(zip(columns, row)) for row in data]


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    text = "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records)
    assert_no_high_risk_text(text, context=str(path))
    atomic_write_text(path, text)


def write_status_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "engine",
        "profile",
        "database",
        "table",
        "status",
        "rows_requested",
        "rows_returned",
        "latest_column",
        "latest_confidence",
        "latest_reason",
        "where_clause",
        "order_by",
        "clickhouse_rules_applied",
        "output_file",
        "sql",
        "error",
    ]
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def write_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        f"# {date_stem()} / sample-tables / {summary['engine']} / report",
        "",
        f"- mode: {summary['mode']}",
        f"- profile: {summary['profile']}",
        f"- schema_index: {summary.get('schema_index')}",
        f"- schema_index_source: {summary.get('schema_index_source')}",
        f"- rows_requested: {summary['rows_requested']}",
        f"- masked_jsonl: {summary.get('masked_jsonl')}",
        f"- status_csv: {summary.get('status_csv')}",
        "",
        f"## Table List ({len(summary.get('requested') or [])})",
    ]
    for item in summary.get("requested") or []:
        duplicate = f" duplicate_of={item.get('duplicate_of')}" if item.get("duplicate_of") else ""
        lines.append(f"- {item.get('raw')} -> {item.get('canonical')}{duplicate}")
    if not summary.get("requested"):
        lines.append("- not provided")
    lines.extend([
        "",
        f"## Tables ({len(summary['tables'])})",
    ])
    for row in summary["tables"]:
        lines.append(f"- {row['database']}.{row['table']}: {row['status']} latest={row.get('latest_column') or 'none'} reason={row.get('latest_reason')}")
    for section in ("missing", "failed", "skipped"):
        rows = summary.get(section) or []
        lines.append("")
        lines.append(f"## {section} ({len(rows)})")
        if not rows:
            lines.append("- none")
        else:
            for item in rows:
                lines.append(f"- {json.dumps(item, ensure_ascii=False, sort_keys=True)}")
    lines.append("")
    lines.append(f"## Sensitive Field Name Risks ({len(summary['sensitive_field_name_risks'])})")
    for item in summary["sensitive_field_name_risks"] or []:
        lines.append(f"- {item.to_dict() if hasattr(item, 'to_dict') else item}")
    if not summary["sensitive_field_name_risks"]:
        lines.append("- none")
    lines.append("")
    lines.append("## Residual Scan")
    lines.append(f"- status: {summary.get('residual_scan', {}).get('status')}")
    lines.append(f"- high_risk_findings: {summary.get('residual_scan', {}).get('high_risk_findings')}")
    lines.append("")
    lines.append("## Validation")
    lines.append("- python scripts/sample_tables.py --engine <engine> --rows 2 --root <target-repo> --dry-run")
    atomic_write_text(path, "\n".join(lines).rstrip() + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sample latest rows from schema-index tables and write masked outputs.")
    parser.add_argument("--engine", required=True, choices=["clickhouse", "odps", "mysql", "metabase"])
    parser.add_argument("--profile", default="default")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--from-schema-index", type=Path, help="Schema index JSON. Overrides env/config/default discovery.")
    parser.add_argument("--table-list", type=Path)
    parser.add_argument("--table-column")
    parser.add_argument("--sheet")
    parser.add_argument("--default-database")
    parser.add_argument("--rows", type=int, default=2)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true", help="Generate SQL/status/report without connecting or writing sample rows.")
    parser.add_argument("--include-local-tables", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    discovery = discover_schema_index(root, args.from_schema_index)
    if discovery.ambiguous or not discovery.path or not discovery.exists:
        message = discovery.message or "No schema index configured. Provide --from-schema-index or set INTERNAL_DATA_QUERY_SCHEMA_INDEX."
        if args.json:
            print(json.dumps({"error": message, "schema_index_candidates": [str(path) for path in discovery.candidates]}, ensure_ascii=False, indent=2))
        else:
            print(message, file=sys.stderr)
        return 2
    schema = load_schema_index(discovery.path)
    table_plan = (
        parse_table_list(args.table_list, default_database=args.default_database, table_column=args.table_column, sheet=args.sheet)
        if args.table_list
        else None
    )
    entries = selected_entries(schema, args.engine, table_plan, args.include_local_tables)
    missing = missing_requested(schema, args.engine, table_plan)
    export_dir = root / "data-query-work" / "exports"
    report_dir = root / "data-query-work" / "discovery-reports"
    stem = f"{date_stem()}__sample-tables__{slug(args.engine)}"
    jsonl_path = export_dir / f"{stem}__masked.jsonl"
    status_path = export_dir / f"{stem}__status.csv"
    report_path = report_dir / f"{stem}__report.md"

    all_masked_records: list[dict[str, Any]] = []
    status_rows: list[dict[str, Any]] = []
    field_risks: list[Any] = []
    skipped_rows: list[dict[str, Any]] = []
    failed_rows: list[dict[str, Any]] = []
    cfg = None if args.dry_run else load_profile(args.engine, args.profile, args.config, args.env_file)
    for key, entry in entries:
        database = str(entry.get("database") or "")
        table = str(entry.get("table") or key)
        if is_local_table(table) and not args.include_local_tables:
            row = {
                "engine": args.engine,
                "profile": args.profile,
                "database": database,
                "table": table,
                "status": "skipped",
                "rows_requested": args.rows,
                "rows_returned": 0,
                "latest_column": "",
                "latest_confidence": "none",
                "latest_reason": "local table skipped by default",
                "where_clause": "",
                "order_by": "",
                "clickhouse_rules_applied": "skip_local",
                "output_file": str(jsonl_path),
                "sql": "",
                "error": "local table skipped by default",
            }
            status_rows.append(row)
            skipped_rows.append(row)
            continue
        if args.engine == "clickhouse":
            sql, meta = build_clickhouse_sql(entry, args.rows, args.include_local_tables)
        else:
            sql, meta = build_generic_sql(entry, args.rows)
        field_risks.extend(schema_field_risks(entry, key))
        row = {
            "engine": args.engine,
            "profile": args.profile,
            "database": database,
            "table": table,
            "rows_requested": args.rows,
            "rows_returned": 0,
            "output_file": str(jsonl_path),
            "sql": sql,
            "error": meta.get("error", ""),
            **meta,
        }
        if not sql:
            status_rows.append(row)
            continue
        try:
            raw_rows: list[dict[str, Any]] = []
            if not args.dry_run:
                if args.engine == "clickhouse":
                    raw_rows = run_clickhouse_sample(cfg or {}, sql)
                else:
                    raise RuntimeError(f"live sampling for {args.engine} is not implemented yet; use --dry-run")
            masked = mask_records(raw_rows)
            for masked_row in masked:
                all_masked_records.append({"engine": args.engine, "database": database, "table": table, "row": masked_row})
                field_risks.extend(field_name_findings(masked_row, path=f"{database}.{table}"))
            row["rows_returned"] = len(masked)
        except Exception as exc:
            row["status"] = "query_failed"
            row["error"] = str(exc)
            failed_rows.append(row)
        status_rows.append(row)

    residual_count = 0
    if not args.dry_run:
        write_jsonl(jsonl_path, all_masked_records)
        residual = residual_scan_file(jsonl_path)
        residual_count = len(residual)
        if residual:
            raise RuntimeError(f"masked jsonl residual scan failed: {residual[0].matched_kind}")
    else:
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    write_status_csv(status_path, status_rows)
    summary = {
        "mode": "dry-run" if args.dry_run else "sample",
        "engine": args.engine,
        "profile": args.profile,
        "rows_requested": args.rows,
        "schema_index": str(discovery.path),
        "schema_index_source": discovery.source,
        "masked_jsonl": None if args.dry_run else str(jsonl_path),
        "status_csv": str(status_path),
        "report": str(report_path),
        "requested": (table_plan or {}).get("requested", []),
        "missing": [{"canonical": item} for item in missing],
        "failed": failed_rows,
        "skipped": skipped_rows,
        "tables": status_rows,
        "sensitive_field_name_risks": field_risks,
        "residual_scan": {
            "status": "not_run_dry_run" if args.dry_run else "passed",
            "high_risk_findings": residual_count,
        },
    }
    write_report(report_path, summary)
    if args.json:
        printable = dict(summary)
        printable["sensitive_field_name_risks"] = [item.to_dict() if hasattr(item, "to_dict") else item for item in field_risks]
        print(json.dumps(printable, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"status_csv: {status_path}")
        print(f"report: {report_path}")
        if not args.dry_run:
            print(f"masked_jsonl: {jsonl_path}")
    return 0 if not any(row["status"] == "query_failed" for row in status_rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
