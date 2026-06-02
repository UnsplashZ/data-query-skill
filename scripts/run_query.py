#!/usr/bin/env python3
"""Run readonly queries against ClickHouse, ODPS, MySQL, or Metabase."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from query_static_check import check_sql
from lib_data_sources import (
    bool_value,
    exit_with_error,
    export_rows,
    load_profile,
    metabase_request,
    metabase_result_to_rows,
    now_stem,
    read_sql,
)


def static_check_result(sql: str | None, engine: str) -> dict[str, Any]:
    if not sql:
        return {
            "ok": True,
            "skipped": True,
            "reason": "no SQL text provided; Metabase card execution records card source and parameters instead",
        }
    return check_sql(sql, engine)


def infer_execution_stage(args: argparse.Namespace) -> str:
    if args.execution_stage:
        return args.execution_stage
    if args.card_id:
        return "card"
    if args.full_scope:
        return "full"
    if args.sample_limit:
        return "sample"
    return "manual"


def infer_confidence(args: argparse.Namespace, stage: str, static_result: dict[str, Any]) -> str:
    if args.confidence:
        return args.confidence
    if not static_result.get("ok"):
        return "unverified"
    if stage in {"card", "sample", "full"}:
        return "partially_verified"
    return "unverified"


def validation_notes(args: argparse.Namespace, stage: str, static_result: dict[str, Any]) -> list[str]:
    notes = list(args.validation_note or [])
    if static_result.get("skipped"):
        notes.append(str(static_result.get("reason")))
    elif static_result.get("warning_count"):
        notes.append("static_check completed with warnings; review before treating results as final.")
    else:
        notes.append("static_check passed.")
    if stage == "sample":
        notes.append(f"sample stage declared; sample_limit={args.sample_limit or 'not provided'}.")
    elif stage == "full":
        notes.append("full stage declared by caller; this script does not automatically rerun a separate sample query.")
    elif stage == "card":
        notes.append("Metabase card stage executed with provided card_id/parameters.")
    else:
        notes.append("manual stage; confidence defaults to unverified unless overridden.")
    return notes


def run_clickhouse(cfg: dict[str, Any], sql: str) -> tuple[list[str], list[dict[str, Any]]]:
    try:
        from clickhouse_driver import Client  # type: ignore
    except ImportError as exc:
        raise RuntimeError("clickhouse-driver is required for ClickHouse queries.") from exc
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
    rows = [dict(zip(columns, row)) for row in data]
    return columns, rows


def run_mysql(cfg: dict[str, Any], sql: str) -> tuple[list[str], list[dict[str, Any]]]:
    try:
        import pymysql  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pymysql is required for MySQL queries.") from exc
    conn = pymysql.connect(
        host=cfg.get("host"),
        port=int(cfg.get("port") or 3306),
        database=cfg.get("database"),
        user=cfg.get("username") or cfg.get("user"),
        password=cfg.get("password"),
        charset=cfg.get("charset") or "utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        read_timeout=300,
        write_timeout=300,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = list(cur.fetchall())
            columns = [desc[0] for desc in cur.description or []]
        return columns, rows
    finally:
        conn.close()


def run_odps(cfg: dict[str, Any], sql: str) -> tuple[list[str], list[dict[str, Any]]]:
    try:
        from odps import ODPS  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pyodps is required for ODPS queries.") from exc
    odps = ODPS(
        cfg.get("access_id"),
        cfg.get("access_key"),
        cfg.get("project"),
        endpoint=cfg.get("endpoint"),
    )
    instance = odps.execute_sql(sql)
    rows: list[dict[str, Any]] = []
    columns: list[str] = []
    with instance.open_reader(tunnel=True) as reader:
        for record in reader:
            if not columns:
                columns = [col.name for col in record._columns]
            rows.append({col: record[col] for col in columns})
    return columns, rows


def run_metabase(cfg: dict[str, Any], args: argparse.Namespace, sql: str | None) -> tuple[list[str], list[dict[str, Any]]]:
    params = json.loads(args.parameters or "[]")
    if args.card_id:
        result = metabase_request(cfg, "POST", f"/api/card/{args.card_id}/query/json", {"parameters": params})
        return metabase_result_to_rows(result)
    if not args.database_id:
        raise RuntimeError("Metabase SQL execution requires --database-id or --card-id.")
    payload = {
        "database": int(args.database_id),
        "type": "native",
        "native": {"query": sql, "template-tags": {}},
        "parameters": params,
    }
    result = metabase_request(cfg, "POST", "/api/dataset", payload)
    return metabase_result_to_rows(result)


def run_mock_result(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("rows") or data.get("result") or data.get("query_result")
    if not isinstance(data, list):
        raise RuntimeError("--mock-result-file must contain a JSON array or an object with rows/result/query_result.")
    rows = [dict(item) for item in data]
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    return columns, rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a readonly query and export CSV/XLSX.")
    parser.add_argument("--engine", required=True, choices=["clickhouse", "odps", "mysql", "metabase"])
    parser.add_argument("--profile", default="default")
    parser.add_argument(
        "--config",
        type=Path,
        help="YAML config. Defaults: $INTERNAL_DATA_QUERY_CONFIG, data-query-work/config/data-sources.yaml, local/data-sources.yaml, ~/.internal-data-query/data-sources.yaml.",
    )
    parser.add_argument("--env-file", type=Path, help="Optional .env file.")
    parser.add_argument("--sql")
    parser.add_argument("--sql-file", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("data-query-work/exports"))
    parser.add_argument("--output-format", choices=["csv", "xlsx"], default="csv")
    parser.add_argument("--name", default="query")
    parser.add_argument("--card-id", type=int, help="Metabase card id.")
    parser.add_argument("--database-id", type=int, help="Metabase database id for native SQL execution.")
    parser.add_argument("--parameters", help="Metabase parameters JSON array.")
    parser.add_argument("--mock-result-file", type=Path, help="Offline eval/test only: export rows from a local JSON fixture instead of connecting.")
    parser.add_argument(
        "--execution-stage",
        choices=["card", "sample", "full", "manual"],
        help="Declare the current execution stage for the query report; does not trigger extra executions.",
    )
    parser.add_argument("--sample-limit", type=int, help="Metadata hint for sample-stage queries.")
    parser.add_argument("--full-scope", action="store_true", help="Mark this single execution as full-scope in the report.")
    parser.add_argument(
        "--confidence",
        choices=["partially_verified", "unverified"],
        help="Override default report confidence. Defaults to partially_verified for card/sample/full, otherwise unverified.",
    )
    parser.add_argument("--validation-note", action="append", default=[], help="Append a validation note to the JSON report.")
    args = parser.parse_args()

    sql = None if args.engine == "metabase" and args.card_id and not (args.sql or args.sql_file) else read_sql(args.sql, args.sql_file)
    static_result = static_check_result(sql, args.engine)
    if not static_result["ok"]:
        print(json.dumps({"static_check": static_result}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise RuntimeError("SQL static check failed; query execution blocked.")
    if static_result.get("warning_count"):
        print(json.dumps({"static_check": static_result}, ensure_ascii=False, indent=2), file=sys.stderr)

    stage = infer_execution_stage(args)
    confidence = infer_confidence(args, stage, static_result)
    started = time.perf_counter()
    source = "mock_file" if args.mock_result_file else args.engine
    if args.mock_result_file:
        columns, rows = run_mock_result(args.mock_result_file)
    elif args.engine == "clickhouse":
        cfg = load_profile(args.engine, args.profile, args.config, args.env_file)
        columns, rows = run_clickhouse(cfg, sql or "")
    elif args.engine == "mysql":
        cfg = load_profile(args.engine, args.profile, args.config, args.env_file)
        columns, rows = run_mysql(cfg, sql or "")
    elif args.engine == "odps":
        cfg = load_profile(args.engine, args.profile, args.config, args.env_file)
        columns, rows = run_odps(cfg, sql or "")
    else:
        cfg = load_profile(args.engine, args.profile, args.config, args.env_file)
        columns, rows = run_metabase(cfg, args, sql)
    elapsed = time.perf_counter() - started

    out = export_rows(args.output_dir, now_stem(args.name), args.output_format, rows, columns)
    print(json.dumps({
        "engine": args.engine,
        "source": source,
        "profile": args.profile,
        "static_check": static_result,
        "execution_stage": stage,
        "sample_limit": args.sample_limit,
        "full_scope": bool(args.full_scope or stage == "full"),
        "confidence": confidence,
        "validation_notes": validation_notes(args, stage, static_result),
        "row_count": len(rows),
        "elapsed_seconds": round(elapsed, 3),
        "output_path": str(out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        raise SystemExit(exit_with_error(exc))
