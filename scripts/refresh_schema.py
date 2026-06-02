#!/usr/bin/env python3
"""Refresh schema metadata from configured readonly data sources."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ddl.rstrip() + "\n", encoding="utf-8")
    return path.relative_to(output_dir.parent).as_posix()


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


def refresh_clickhouse(cfg: dict[str, Any], profile: str, output_dir: Path, limit_tables: int, include_system: bool) -> dict[str, Any]:
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
    table_sql = """
        SELECT database, name, comment
        FROM system.tables
        WHERE database = %(database)s
        ORDER BY database, name
        LIMIT %(limit)s
    """
    if include_system:
        table_sql = """
            SELECT database, name, comment
            FROM system.tables
            ORDER BY database, name
            LIMIT %(limit)s
        """
        table_rows = client.execute(table_sql, {"limit": limit_tables})
    else:
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


def refresh_mysql(cfg: dict[str, Any], profile: str, output_dir: Path, limit_tables: int) -> dict[str, Any]:
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


def refresh_odps(cfg: dict[str, Any], profile: str, output_dir: Path, limit_tables: int) -> dict[str, Any]:
    from odps import ODPS  # type: ignore

    project = str(cfg.get("project") or "")
    odps = ODPS(
        cfg.get("access_id"),
        cfg.get("access_key"),
        project,
        endpoint=cfg.get("endpoint"),
    )
    result: dict[str, Any] = {}
    for i, table_obj in enumerate(odps.list_tables()):
        if i >= limit_tables:
            break
        table_name = str(getattr(table_obj, "name", table_obj))
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


def refresh_metabase(cfg: dict[str, Any], profile: str, limit_tables: int) -> dict[str, Any]:
    databases = metabase_request(cfg, "GET", "/api/database")
    items = databases.get("data") if isinstance(databases, dict) else databases
    result: dict[str, Any] = {}
    for db in list(items or []):
        db_id = db.get("id")
        if not db_id:
            continue
        metadata = metabase_request(cfg, "GET", f"/api/database/{db_id}/metadata")
        database_name = str(metadata.get("name") or db.get("name") or db_id)
        for table in list(metadata.get("tables") or [])[:limit_tables]:
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
                source="metabase_metadata",
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
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    target_root = args.root.resolve()
    output_dir = (args.output_dir or target_root / "data-query-work" / "schema").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "unified_schema_index.json"
    data = {"version": 1, "tables": {}} if args.replace else load_existing(index_path)
    data["generated_at"] = now_iso()
    data["source"] = "scripts/refresh_schema.py"
    data.setdefault("tables", {})

    _, config = load_config_with_path(args.config, args.env_file)
    engines = SUPPORTED_ENGINES if args.engine == "all" else (args.engine,)
    profiles = [
        item for item in iter_profile_configs(config) if item[0] in engines and (not args.profile or item[1] == args.profile)
    ]
    report: list[dict[str, Any]] = []
    for engine, profile, cfg in profiles:
        skip = should_skip(engine, cfg)
        if skip:
            report.append({"engine": engine, "profile": profile, "status": "skipped", "reason": skip, "tables": 0})
            continue
        try:
            if engine == "clickhouse":
                refreshed = refresh_clickhouse(cfg, profile, output_dir, args.limit_tables, args.include_system)
            elif engine == "mysql":
                refreshed = refresh_mysql(cfg, profile, output_dir, args.limit_tables)
            elif engine == "odps":
                refreshed = refresh_odps(cfg, profile, output_dir, args.limit_tables)
            elif engine == "metabase":
                refreshed = refresh_metabase(cfg, profile, args.limit_tables)
            else:
                continue
            data["tables"].setdefault(engine, {})
            data["tables"][engine].update(refreshed)
            report.append({"engine": engine, "profile": profile, "status": "ok", "tables": len(refreshed)})
        except Exception as exc:
            report.append({"engine": engine, "profile": profile, "status": "failed", "reason": str(exc), "tables": 0})

    index_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {"schema_index": str(index_path), "profiles": report}
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"schema_index: {index_path}")
        for row in report:
            detail = f" ({row.get('reason')})" if row.get("reason") else ""
            print(f"- {row['engine']}/{row['profile']}: {row['status']} tables={row['tables']}{detail}")
    return 1 if any(row["status"] == "failed" for row in report) else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        raise SystemExit(exit_with_error(exc))
