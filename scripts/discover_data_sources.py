#!/usr/bin/env python3
"""Summarize installed drivers, local profiles, bundled knowledge, and next actions."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

from lib_data_sources import (
    SUPPORTED_ENGINES,
    iter_profile_configs,
    load_config_with_path,
    profile_missing_fields,
    profile_placeholder_fields,
)
from lib_workspace import resolve_knowledge_root

DRIVERS = {
    "clickhouse": "clickhouse_driver",
    "mysql": "pymysql",
    "odps": "odps",
    "metabase": None,
    "yaml": "yaml",
    "xlsx": "openpyxl",
}


def driver_status() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for name, module in DRIVERS.items():
        rows[name] = {
            "module": module,
            "installed": True if module is None else importlib.util.find_spec(module) is not None,
        }
    return rows


def profile_status(engine: str, profile: str, cfg: dict[str, Any]) -> dict[str, Any]:
    missing = profile_missing_fields(engine, cfg)
    placeholders = profile_placeholder_fields(engine, cfg)
    if missing:
        status = "missing"
    elif placeholders:
        status = "offline_placeholder"
    else:
        status = "configured"
    return {
        "engine": engine,
        "profile": profile,
        "status": status,
        "missing_fields": missing,
        "placeholder_fields": placeholders,
        "readonly": bool(cfg.get("readonly", True)),
    }


def schema_kb_status(root: Path) -> dict[str, Any]:
    kb = root / "references" / "sql-query-method-internal" / "references" / "schema-kb"
    unified = kb / "unified_schema_index.json"
    status: dict[str, Any] = {"path": str(kb), "exists": kb.exists(), "tables": {}, "files": []}
    if kb.exists():
        status["files"] = sorted(path.name for path in kb.iterdir() if path.is_file())
    if unified.exists():
        data = json.loads(unified.read_text(encoding="utf-8"))
        tables = data.get("tables") or {}
        status["tables"] = {engine: len(items or {}) for engine, items in tables.items()}
    return status


def historical_sql_status(root: Path) -> dict[str, Any]:
    csv_path = root / "references" / "old-sql" / "historical-sql-index.csv"
    sql_dir = root / "references" / "old-sql" / "sql"
    count = 0
    domains: dict[str, int] = {}
    if csv_path.exists():
        with csv_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                count += 1
                tags = [
                    tag.strip()
                    for tag in (row.get("domain_tags") or row.get("domain") or row.get("topic") or "").split(",")
                    if tag.strip()
                ]
                for key in tags or ["unknown"]:
                    domains[key] = domains.get(key, 0) + 1
    return {
        "index_path": str(csv_path),
        "index_exists": csv_path.exists(),
        "sql_dir": str(sql_dir),
        "sql_file_count": len(list(sql_dir.glob("*.sql"))) if sql_dir.exists() else 0,
        "index_count": count,
        "domains": dict(sorted(domains.items())[:20]),
    }


def query_knowledge_status(root: Path) -> dict[str, Any]:
    selection = resolve_knowledge_root(root, mode="read")
    kb = selection.path
    status: dict[str, Any] = {
        "path": str(kb),
        "exists": kb.exists(),
        "path_kind": "legacy" if selection.is_legacy else "workspace",
        "warning": selection.warning,
        "file_count": 0,
        "status_counts": {},
        "confidence_counts": {},
    }
    if not kb.exists():
        return status
    files = [path for path in kb.rglob("*") if path.is_file() and path.suffix.lower() in {".json", ".md", ".yaml", ".yml"}]
    status["file_count"] = len(files)
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for key, bucket in [("status", "status_counts"), ("confidence", "confidence_counts")]:
            match = None
            if path.suffix.lower() == ".json":
                try:
                    value = json.loads(text).get(key)
                    match = str(value) if value else None
                except json.JSONDecodeError:
                    match = None
            if match is None:
                found = re.search(rf"(?im)^\s*{key}\s*[:=]\s*([A-Za-z0-9_-]+)", text)
                match = found.group(1) if found else None
            if match:
                counts = status[bucket]
                counts[match] = counts.get(match, 0) + 1
    return status


def build_next_actions(local_config: dict[str, Any], available_sources: list[dict[str, Any]], offline_knowledge: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    if not local_config.get("path"):
        actions.append("运行 scripts/setup_connections.py --non-interactive 生成本机配置模板，然后填入只读连接。")
    if any(item["status"] in {"missing", "offline_placeholder"} for item in available_sources):
        actions.append("补齐 missing/offline_placeholder profile；占位配置不能作为 verified 查询来源。")
    if not offline_knowledge["schema_kb"].get("exists"):
        actions.append("缺少 schema KB，写 SQL 前需要从业务文档或用户确认表字段。")
    if not offline_knowledge["data_query_knowledge"].get("exists"):
        actions.append("未发现 data-query-work/knowledge；只能使用 schema KB/历史 SQL/当前用户证据，不能标记共享知识 verified。")
    elif offline_knowledge["data_query_knowledge"].get("path_kind") == "legacy":
        actions.append("当前只发现旧 data-query-knowledge；它只作为只读兼容来源，写入前先迁到 data-query-work/knowledge。")
    if not actions:
        actions.append("复杂查询前先运行 search_schema/search_old_sql，再执行 query_static_check 与 sample 查询。")
    return actions


def print_text(result: dict[str, Any]) -> None:
    print(f"config_path: {result['local_config']['path'] or 'not found'}")
    print("installed:")
    for name, row in result["installed"].items():
        print(f"- {name}: {'yes' if row['installed'] else 'no'}")
    print("available_sources:")
    for row in result["available_sources"]:
        print(f"- {row['engine']}/{row['profile']}: {row['status']}")
    print("offline_knowledge:")
    schema = result["offline_knowledge"]["schema_kb"]
    hist = result["offline_knowledge"]["historical_sql"]
    dqk = result["offline_knowledge"]["data_query_knowledge"]
    print(f"- schema_kb: exists={schema['exists']} tables={schema.get('tables', {})}")
    print(f"- historical_sql: index_count={hist['index_count']} sql_file_count={hist['sql_file_count']}")
    print(
        f"- data_query_knowledge: exists={dqk['exists']} "
        f"path_kind={dqk.get('path_kind')} file_count={dqk['file_count']}"
    )
    print("next_actions:")
    for action in result["next_actions"]:
        print(f"- {action}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover configured and offline data sources for internal-data-query.")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--json", action="store_true", help="Alias for --format json.")
    args = parser.parse_args()

    root = args.root.resolve()
    config_path, config = load_config_with_path(args.config, args.env_file)
    profiles = [profile_status(engine, profile, cfg) for engine, profile, cfg in iter_profile_configs(config)]
    configured_engines = {row["engine"] for row in profiles}
    for engine in SUPPORTED_ENGINES:
        if engine not in configured_engines:
            profiles.append(
                {
                    "engine": engine,
                    "profile": "default",
                    "status": "missing",
                    "missing_fields": ["profile"],
                    "placeholder_fields": [],
                    "readonly": True,
                }
            )
    offline_knowledge = {
        "schema_kb": schema_kb_status(root),
        "historical_sql": historical_sql_status(root),
        "data_query_knowledge": query_knowledge_status(root),
    }
    local_config = {
        "path": str(config_path) if config_path else None,
        "exists": bool(config_path and config_path.exists()),
    }
    result = {
        "installed": driver_status(),
        "local_config": local_config,
        "available_sources": profiles,
        "offline_knowledge": offline_knowledge,
        "next_actions": build_next_actions(local_config, profiles, offline_knowledge),
    }
    if args.json or args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_text(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
