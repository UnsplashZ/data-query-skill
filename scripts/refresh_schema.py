#!/usr/bin/env python3
"""Refresh schema metadata from configured readonly data sources."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib_masking import FIELD_NAME_PATTERNS
from lib_table_list import parse_table_list
from lib_data_sources import (
    SUPPORTED_ENGINES,
    bool_value,
    exit_with_error,
    iter_profile_configs,
    load_config_with_path,
    metabase_request,
    profile_missing_fields,
    profile_placeholder_fields,
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slug(value: Any) -> str:
    text = str(value or "unknown").strip()
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", text)
    return text.strip(".-") or "unknown"


def quote_clickhouse(value: str) -> str:
    return "`" + value.replace("`", "``") + "`"


def quote_mysql(value: str) -> str:
    return "`" + value.replace("`", "``") + "`"


def write_ddl(output_dir: Path, engine: str, profile: str, database: str, table: str, ddl: str | None) -> str | None:
    if not ddl:
        return None
    path = output_dir / "ddl" / slug(engine) / slug(profile) / slug(database) / f"{slug(table)}.sql"
    atomic_write_text(path, ddl.rstrip() + "\n")
    return path.relative_to(output_dir.parent).as_posix()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def date_stem() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def canonical_for(database: str, table: str) -> str:
    return f"{database}.{table}" if database else table


def target_rows(table_plan: dict[str, Any] | None, default_database: str = "") -> list[dict[str, str]]:
    if not table_plan:
        return []
    rows = []
    seen: set[str] = set()
    for item in table_plan.get("requested", []):
        database = str(item.get("database") or default_database or "")
        table = str(item.get("table") or "")
        canonical = canonical_for(database, table)
        if not table or canonical in seen:
            continue
        rows.append({"database": database, "table": table, "canonical": canonical})
        seen.add(canonical)
    return rows


def sensitive_field_risks(entries: dict[str, Any]) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    for key, entry in entries.items():
        for column in entry.get("columns") or []:
            name = str(column.get("name") or "")
            for kind, pattern in FIELD_NAME_PATTERNS:
                if pattern.search(name):
                    risks.append({"table": key, "field": name, "kind": kind})
                    break
    return risks


def table_entry(
    *,
    engine: str,
    profile: str,
    database: str,
    table: str,
    columns: list[dict[str, Any]],
    comment: str = "",
    ddl_path: str | None = None,
    source: str = "live_metadata",
) -> tuple[str, dict[str, Any]]:
    key = f"{database}.{table}" if database else table
    return key, {
        "engine": engine,
        "profile": profile,
        "database": database,
        "table": table,
        "comment": comment or "",
        "columns": columns,
        "ddl_path": ddl_path,
        "source": source,
        "refreshed_at": now_iso(),
    }


def refresh_clickhouse(
    cfg: dict[str, Any],
    profile: str,
    output_dir: Path,
    limit_tables: int,
    include_system: bool,
    table_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from clickhouse_driver import Client  # type: ignore

    database = str(cfg.get("database") or "default")
    client = Client(
        host=cfg.get("host"),
        port=int(cfg.get("port") or 9000),
        database=database,
        user=cfg.get("username") or cfg.get("user"),
        password=cfg.get("password"),
        secure=bool_value(cfg.get("secure")),
        send_receive_timeout=60,
        connect_timeout=10,
    )
    targets = target_rows(table_plan, database)
    if targets:
        table_rows = []
        for target in targets:
            db = target["database"] or database
            table_rows.extend(
                client.execute(
                    """
                    SELECT database, name, comment
                    FROM system.tables
                    WHERE database = %(database)s AND name = %(table)s
                    ORDER BY database, name
                    """,
                    {"database": db, "table": target["table"]},
                )
            )
    elif include_system:
        table_sql = """
            SELECT database, name, comment
            FROM system.tables
            ORDER BY database, name
            LIMIT %(limit)s
        """
        table_rows = client.execute(table_sql, {"limit": limit_tables})
    else:
        table_sql = """
            SELECT database, name, comment
            FROM system.tables
            WHERE database = %(database)s
            ORDER BY database, name
            LIMIT %(limit)s
        """
        table_rows = client.execute(table_sql, {"database": database, "limit": limit_tables})

    result: dict[str, Any] = {}
    for db, table, comment in table_rows:
        col_rows = client.execute(
            """
            SELECT name, type, default_kind, default_expression, comment, position
            FROM system.columns
            WHERE database = %(database)s AND table = %(table)s
            ORDER BY position
            """,
            {"database": db, "table": table},
        )
        columns = [
            {
                "name": name,
                "type": col_type,
                "comment": col_comment or "",
                "default_kind": default_kind or "",
                "default_expression": default_expr or "",
                "ordinal": int(position),
            }
            for name, col_type, default_kind, default_expr, col_comment, position in col_rows
        ]
        ddl = None
        try:
            ddl_rows = client.execute(f"SHOW CREATE TABLE {quote_clickhouse(str(db))}.{quote_clickhouse(str(table))}")
            ddl = str(ddl_rows[0][0]) if ddl_rows else None
        except Exception as exc:
            ddl = f"-- SHOW CREATE TABLE failed: {exc}"
        ddl_path = write_ddl(output_dir, "clickhouse", profile, str(db), str(table), ddl)
        key, entry = table_entry(
            engine="clickhouse",
            profile=profile,
            database=str(db),
            table=str(table),
            columns=columns,
            comment=str(comment or ""),
            ddl_path=ddl_path,
        )
        result[key] = entry
    return result


def refresh_mysql(
    cfg: dict[str, Any],
    profile: str,
    output_dir: Path,
    limit_tables: int,
    table_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    import pymysql  # type: ignore

    database = str(cfg.get("database") or cfg.get("schema") or "")
    conn = pymysql.connect(
        host=cfg.get("host"),
        port=int(cfg.get("port") or 3306),
        database=database,
        user=cfg.get("username") or cfg.get("user"),
        password=cfg.get("password"),
        charset=cfg.get("charset") or "utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
        read_timeout=60,
        write_timeout=60,
    )
    try:
        with conn.cursor() as cur:
            targets = target_rows(table_plan, database)
            if targets:
                tables = []
                for target in targets:
                    cur.execute(
                        """
                        SELECT table_schema, table_name, table_comment
                        FROM information_schema.tables
                        WHERE table_schema = %s AND table_name = %s
                        ORDER BY table_schema, table_name
                        """,
                        (target["database"] or database, target["table"]),
                    )
                    tables.extend(list(cur.fetchall()))
            else:
                cur.execute(
                    """
                    SELECT table_schema, table_name, table_comment
                    FROM information_schema.tables
                    WHERE table_schema = %s
                    ORDER BY table_schema, table_name
                    LIMIT %s
                    """,
                    (database, limit_tables),
                )
                tables = list(cur.fetchall())
            result: dict[str, Any] = {}
            for row in tables:
                db = str(row["table_schema"])
                table = str(row["table_name"])
                cur.execute(
                    """
                    SELECT column_name, column_type, is_nullable, column_default, column_comment, ordinal_position
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (db, table),
                )
                columns = [
                    {
                        "name": str(col["column_name"]),
                        "type": str(col["column_type"]),
                        "nullable": str(col["is_nullable"]).upper() == "YES",
                        "default": col["column_default"],
                        "comment": str(col["column_comment"] or ""),
                        "ordinal": int(col["ordinal_position"]),
                    }
                    for col in cur.fetchall()
                ]
                ddl = None
                try:
                    cur.execute(f"SHOW CREATE TABLE {quote_mysql(db)}.{quote_mysql(table)}")
                    ddl_row = cur.fetchone() or {}
                    ddl = ddl_row.get("Create Table") or next(iter(ddl_row.values()), None)
                except Exception as exc:
                    ddl = f"-- SHOW CREATE TABLE failed: {exc}"
                ddl_path = write_ddl(output_dir, "mysql", profile, db, table, str(ddl) if ddl else None)
                key, entry = table_entry(
                    engine="mysql",
                    profile=profile,
                    database=db,
                    table=table,
                    columns=columns,
                    comment=str(row.get("table_comment") or ""),
                    ddl_path=ddl_path,
                )
                result[key] = entry
            return result
    finally:
        conn.close()


def odps_type(value: Any) -> str:
    return str(value or "")


def build_odps_ddl(project: str, table: str, columns: list[dict[str, Any]], comment: str) -> str:
    lines = [f"CREATE TABLE {project}.{table} ("]
    col_lines = []
    for col in columns:
        suffix = f" COMMENT '{str(col.get('comment') or '').replace(chr(39), chr(39) + chr(39))}'" if col.get("comment") else ""
        col_lines.append(f"  {col['name']} {col['type']}{suffix}")
    lines.append(",\n".join(col_lines))
    lines.append(")")
    if comment:
        lines.append(f"COMMENT '{comment.replace(chr(39), chr(39) + chr(39))}'")
    lines.append(";")
    return "\n".join(lines)


def refresh_odps(
    cfg: dict[str, Any],
    profile: str,
    output_dir: Path,
    limit_tables: int,
    table_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from odps import ODPS  # type: ignore

    project = str(cfg.get("project") or "")
    odps = ODPS(
        cfg.get("access_id"),
        cfg.get("access_key"),
        project,
        endpoint=cfg.get("endpoint"),
    )
    result: dict[str, Any] = {}
    targets = target_rows(table_plan, project)
    if targets:
        table_names = [target["table"] for target in targets]
    else:
        table_names = []
        for i, table_obj in enumerate(odps.list_tables()):
            if i >= limit_tables:
                break
            table_names.append(str(getattr(table_obj, "name", table_obj)))
    for table_name in table_names:
        table = odps.get_table(table_name)
        schema = getattr(table, "schema", None)
        raw_columns = list(getattr(schema, "columns", []) or [])
        columns = []
        for pos, col in enumerate(raw_columns, start=1):
            columns.append(
                {
                    "name": str(getattr(col, "name", "")),
                    "type": odps_type(getattr(col, "type", "")),
                    "comment": str(getattr(col, "comment", "") or ""),
                    "ordinal": pos,
                }
            )
        comment = str(getattr(table, "comment", "") or "")
        ddl = build_odps_ddl(project, table_name, columns, comment)
        ddl_path = write_ddl(output_dir, "odps", profile, project, table_name, ddl)
        key, entry = table_entry(
            engine="odps",
            profile=profile,
            database=project,
            table=table_name,
            columns=columns,
            comment=comment,
            ddl_path=ddl_path,
            source="live_metadata_generated_ddl",
        )
        result[key] = entry
    return result


def refresh_metabase(cfg: dict[str, Any], profile: str, limit_tables: int, table_plan: dict[str, Any] | None = None) -> dict[str, Any]:
    databases = metabase_request(cfg, "GET", "/api/database")
    items = databases.get("data") if isinstance(databases, dict) else databases
    result: dict[str, Any] = {}
    targets = {item["table"] for item in target_rows(table_plan)}
    for db in list(items or []):
        db_id = db.get("id")
        if not db_id:
            continue
        metadata = metabase_request(cfg, "GET", f"/api/database/{db_id}/metadata")
        database_name = str(metadata.get("name") or db.get("name") or db_id)
        candidates = list(metadata.get("tables") or [])
        if targets:
            candidates = [table for table in candidates if str(table.get("name") or table.get("display_name") or table.get("id")) in targets]
        for table in candidates[:limit_tables]:
            table_name = str(table.get("name") or table.get("display_name") or table.get("id"))
            fields = table.get("fields") or []
            columns = [
                {
                    "name": str(field.get("name") or field.get("display_name") or ""),
                    "type": str(field.get("base_type") or field.get("semantic_type") or ""),
                    "comment": str(field.get("description") or ""),
                    "ordinal": int(field.get("position") or i + 1),
                }
                for i, field in enumerate(fields)
            ]
            key, entry = table_entry(
                engine="metabase",
                profile=profile,
                database=database_name,
                table=table_name,
                columns=columns,
                comment=str(table.get("description") or ""),
                ddl_path=None,
                source="metabase_metadata_filtered_after_fetch" if targets else "metabase_metadata",
            )
            result[key] = entry
    return result


def load_existing(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "tables": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"version": 1, "tables": {}}
    data.setdefault("version", 1)
    data.setdefault("tables", {})
    return data


def should_skip(engine: str, cfg: dict[str, Any]) -> str | None:
    missing = profile_missing_fields(engine, cfg)
    if missing:
        return "missing fields: " + ", ".join(missing)
    placeholders = profile_placeholder_fields(engine, cfg)
    if placeholders:
        return "placeholder fields: " + ", ".join(placeholders)
    return None


def profile_default_database(config: dict[str, Any], engine_filter: str, profile_filter: str | None) -> str:
    engines = SUPPORTED_ENGINES if engine_filter == "all" else (engine_filter,)
    for engine, profile, cfg in iter_profile_configs(config):
        if engine not in engines:
            continue
        if profile_filter and profile != profile_filter:
            continue
        value = cfg.get("database") or cfg.get("schema") or cfg.get("project")
        if value:
            return str(value)
    return ""


def write_discovery_report(root: Path, engine: str, summary: dict[str, Any], *, write_json: bool = True) -> dict[str, str]:
    report_dir = root / "data-query-work" / "discovery-reports"
    stem = f"{date_stem()}-{slug(engine)}-schema-refresh-report"
    md_path = report_dir / f"{stem}.md"
    json_path = report_dir / f"{stem}.json"
    lines = [
        f"# {date_stem()} / schema-refresh / {engine} / report",
        "",
        f"- mode: {summary.get('mode')}",
        f"- schema_index: {summary.get('output', {}).get('schema_index')}",
        f"- ddl_root: {summary.get('output', {}).get('ddl_root')}",
        "",
        f"## Requested ({len(summary.get('requested') or [])})",
    ]
    for item in summary.get("requested") or []:
        duplicate = f" duplicate_of={item.get('duplicate_of')}" if item.get("duplicate_of") else ""
        lines.append(f"- {item.get('raw')} -> {item.get('canonical')}{duplicate}")
    for section in ("found", "missing", "duplicate_aliases", "skipped", "failed", "sensitive_field_name_risks"):
        rows = summary.get(section) or []
        lines.append("")
        lines.append(f"## {section} ({len(rows)})")
        if not rows:
            lines.append("- none")
            continue
        for row in rows:
            lines.append(f"- {json.dumps(row, ensure_ascii=False, sort_keys=True)}")
    lines.append("")
    lines.append("## Validation")
    lines.append("- python scripts/refresh_schema.py --table-list <file> --dry-run --root <target-repo>")
    atomic_write_text(md_path, "\n".join(lines).rstrip() + "\n")
    outputs = {"markdown": str(md_path)}
    if write_json:
        atomic_write_text(json_path, json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        outputs["json"] = str(json_path)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh data-query-work/schema from configured readonly data sources.")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--engine", choices=["all", *SUPPORTED_ENGINES], default="all")
    parser.add_argument("--profile", help="Only refresh one profile name.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Target repository root. Defaults to current directory.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Defaults to <root>/data-query-work/schema.")
    parser.add_argument("--limit-tables", type=int, default=500)
    parser.add_argument("--include-system", action="store_true", help="ClickHouse only: include non-current/system databases.")
    parser.add_argument("--replace", action="store_true", help="Replace the existing unified index instead of merging.")
    parser.add_argument("--table-list", type=Path, help="txt/csv/xlsx table list for scoped refresh.")
    parser.add_argument("--table-column", help="CSV/XLSX column name containing table names.")
    parser.add_argument("--sheet", help="XLSX sheet name. Defaults to first sheet.")
    parser.add_argument("--default-database", help="Database/schema/project used for bare table names.")
    parser.add_argument("--dry-run", action="store_true", help="Parse scoped table list and write discovery report without connecting.")
    parser.add_argument("--no-report-json", action="store_true", help="Do not write discovery report JSON.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    target_root = args.root.resolve()
    output_dir = (args.output_dir or target_root / "data-query-work" / "schema").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "unified_schema_index.json"
    _, config = load_config_with_path(args.config, args.env_file)
    effective_default_database = args.default_database or profile_default_database(config, args.engine, args.profile)
    table_plan = None
    if args.table_list:
        table_plan = parse_table_list(
            args.table_list,
            default_database=effective_default_database,
            table_column=args.table_column,
            sheet=args.sheet,
        )
    summary: dict[str, Any] = {
        "mode": "dry-run" if args.dry_run else "refresh",
        "engine": args.engine,
        "profile": args.profile or "all",
        "requested": (table_plan or {}).get("requested", []),
        "found": [],
        "missing": [],
        "duplicate_aliases": (table_plan or {}).get("duplicate_aliases", []),
        "skipped": [],
        "failed": [],
        "sensitive_field_name_risks": [],
        "output": {
            "schema_index": str(index_path),
            "ddl_root": str(output_dir / "ddl"),
        },
    }
    if args.dry_run:
        requested = target_rows(table_plan, effective_default_database) if table_plan else []
        summary["missing"] = [{"canonical": row["canonical"], "reason": "dry_run_no_live_metadata"} for row in requested]
        reports = write_discovery_report(target_root, args.engine, summary, write_json=not args.no_report_json)
        summary["output"]["reports"] = reports
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"DRY-RUN: parsed {len(summary['requested'])} requested table(s); report={reports['markdown']}")
        return 0

    data = {"version": 1, "tables": {}} if args.replace else load_existing(index_path)
    data["generated_at"] = now_iso()
    data["source"] = "scripts/refresh_schema.py"
    data.setdefault("tables", {})

    engines = SUPPORTED_ENGINES if args.engine == "all" else (args.engine,)
    profiles = [
        item for item in iter_profile_configs(config) if item[0] in engines and (not args.profile or item[1] == args.profile)
    ]
    report: list[dict[str, Any]] = []
    for engine, profile, cfg in profiles:
        skip = should_skip(engine, cfg)
        if skip:
            report.append({"engine": engine, "profile": profile, "status": "skipped", "reason": skip, "tables": 0})
            summary["skipped"].append({"engine": engine, "profile": profile, "reason": skip})
            continue
        try:
            scoped_plan = table_plan
            if scoped_plan and args.default_database is None:
                scoped_plan = parse_table_list(
                    args.table_list,
                    default_database=str(cfg.get("database") or cfg.get("schema") or cfg.get("project") or ""),
                    table_column=args.table_column,
                    sheet=args.sheet,
                )
            if engine == "clickhouse":
                refreshed = refresh_clickhouse(cfg, profile, output_dir, args.limit_tables, args.include_system, scoped_plan)
            elif engine == "mysql":
                refreshed = refresh_mysql(cfg, profile, output_dir, args.limit_tables, scoped_plan)
            elif engine == "odps":
                refreshed = refresh_odps(cfg, profile, output_dir, args.limit_tables, scoped_plan)
            elif engine == "metabase":
                refreshed = refresh_metabase(cfg, profile, args.limit_tables, scoped_plan)
            else:
                continue
            data["tables"].setdefault(engine, {})
            data["tables"][engine].update(refreshed)
            found_keys = sorted(refreshed)
            summary["found"].extend({"engine": engine, "profile": profile, "canonical": key} for key in found_keys)
            requested_keys = {row["canonical"] for row in target_rows(scoped_plan, str(cfg.get("database") or cfg.get("schema") or cfg.get("project") or ""))}
            for key in sorted(requested_keys - set(found_keys)):
                summary["missing"].append({"engine": engine, "profile": profile, "canonical": key})
            summary["sensitive_field_name_risks"].extend(sensitive_field_risks(refreshed))
            report.append({"engine": engine, "profile": profile, "status": "ok", "tables": len(refreshed)})
        except Exception as exc:
            report.append({"engine": engine, "profile": profile, "status": "failed", "reason": str(exc), "tables": 0})
            summary["failed"].append({"engine": engine, "profile": profile, "reason": str(exc)})

    atomic_write_text(index_path, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    reports = write_discovery_report(target_root, args.engine, summary, write_json=not args.no_report_json)
    result = {"schema_index": str(index_path), "profiles": report, "discovery": summary, "reports": reports}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"schema_index: {index_path}")
        print(f"discovery_report: {reports['markdown']}")
        for row in report:
            detail = f" ({row.get('reason')})" if row.get("reason") else ""
            print(f"- {row['engine']}/{row['profile']}: {row['status']} tables={row['tables']}{detail}")
    return 1 if any(row["status"] == "failed" for row in report) else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        raise SystemExit(exit_with_error(exc))
