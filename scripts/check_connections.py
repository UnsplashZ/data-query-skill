#!/usr/bin/env python3
"""Smoke check configured data source profiles without hiding offline placeholders."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

from lib_data_sources import (
    SUPPORTED_ENGINES,
    bool_value,
    iter_profile_configs,
    load_config_with_path,
    metabase_request,
    profile_missing_fields,
    profile_placeholder_fields,
)

DRIVER_MODULES = {
    "clickhouse": "clickhouse_driver",
    "mysql": "pymysql",
    "odps": "odps",
    "metabase": None,
}


def driver_available(engine: str) -> bool:
    module = DRIVER_MODULES.get(engine)
    return True if module is None else importlib.util.find_spec(module) is not None


def smoke_clickhouse(cfg: dict[str, Any]) -> None:
    from clickhouse_driver import Client  # type: ignore

    client = Client(
        host=cfg.get("host"),
        port=int(cfg.get("port") or 9000),
        database=cfg.get("database"),
        user=cfg.get("username") or cfg.get("user"),
        password=cfg.get("password"),
        secure=bool_value(cfg.get("secure")),
        send_receive_timeout=20,
        connect_timeout=10,
    )
    client.execute("SELECT 1")


def smoke_mysql(cfg: dict[str, Any]) -> None:
    import pymysql  # type: ignore

    conn = pymysql.connect(
        host=cfg.get("host"),
        port=int(cfg.get("port") or 3306),
        database=cfg.get("database"),
        user=cfg.get("username") or cfg.get("user"),
        password=cfg.get("password"),
        charset=cfg.get("charset") or "utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
        read_timeout=20,
        write_timeout=20,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    finally:
        conn.close()


def smoke_odps(cfg: dict[str, Any]) -> None:
    from odps import ODPS  # type: ignore

    odps = ODPS(
        cfg.get("access_id"),
        cfg.get("access_key"),
        cfg.get("project"),
        endpoint=cfg.get("endpoint"),
    )
    instance = odps.execute_sql("SELECT 1")
    with instance.open_reader(tunnel=True) as reader:
        for _ in reader:
            break


def smoke_metabase(cfg: dict[str, Any]) -> None:
    metabase_request(cfg, "GET", "/api/user/current")


def check_profile(engine: str, profile: str, cfg: dict[str, Any], smoke: bool) -> dict[str, Any]:
    row: dict[str, Any] = {
        "engine": engine,
        "profile": profile,
        "status": "unknown",
        "message": "",
        "next_action": "",
    }
    missing = profile_missing_fields(engine, cfg)
    placeholders = profile_placeholder_fields(engine, cfg)
    if missing:
        row.update(
            {
                "status": "missing",
                "message": f"missing fields: {', '.join(missing)}",
                "next_action": "补齐本机只读连接配置后重试。",
            }
        )
        return row
    if placeholders:
        row.update(
            {
                "status": "offline_placeholder",
                "message": f"placeholder fields: {', '.join(placeholders)}",
                "next_action": "把示例 host/user/secret 替换为本机真实只读配置；不要提交到仓库。",
            }
        )
        return row
    if not driver_available(engine):
        row.update(
            {
                "status": "missing_driver",
                "message": f"missing Python driver: {DRIVER_MODULES[engine]}",
                "next_action": "安装 requirements.txt 中对应依赖，或仅在离线模式下做静态检查。",
            }
        )
        return row
    if not smoke:
        row.update({"status": "configured", "message": "profile parsed; smoke disabled", "next_action": "运行时再做真实 smoke check。"})
        return row
    try:
        if engine == "clickhouse":
            smoke_clickhouse(cfg)
        elif engine == "mysql":
            smoke_mysql(cfg)
        elif engine == "odps":
            smoke_odps(cfg)
        elif engine == "metabase":
            smoke_metabase(cfg)
        row.update({"status": "ok", "message": "smoke check passed", "next_action": ""})
    except Exception as exc:
        row.update(
            {
                "status": "failed",
                "message": str(exc),
                "next_action": "检查网络/VPN、只读账号权限、数据库名、profile 字段和驱动版本。",
            }
        )
    return row


def print_table(rows: list[dict[str, Any]]) -> None:
    headers = ["engine", "profile", "status", "message", "next_action"]
    print(" | ".join(headers))
    print(" | ".join(["---"] * len(headers)))
    for row in rows:
        print(" | ".join(str(row.get(h, "")).replace("\n", " ")[:220] for h in headers))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check ClickHouse/ODPS/MySQL/Metabase profile parsing and smoke connectivity.")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--engine", choices=list(SUPPORTED_ENGINES))
    parser.add_argument("--profile", help="Only check one profile name.")
    parser.add_argument("--offline-ok", action="store_true", help="Exit 0 for missing/offline placeholder/driver/connection failures.")
    parser.add_argument("--no-smoke", action="store_true", help="Only parse profile configuration; do not connect.")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--json", action="store_true", help="Alias for --format json.")
    args = parser.parse_args()

    config_path, config = load_config_with_path(args.config, args.env_file)
    rows = []
    profiles = iter_profile_configs(config, args.engine)
    if args.profile:
        profiles = [item for item in profiles if item[1] == args.profile]
    if not profiles:
        engines = [args.engine] if args.engine else list(SUPPORTED_ENGINES)
        for engine in engines:
            rows.append(
                {
                    "engine": engine,
                    "profile": args.profile or "default",
                    "status": "missing",
                    "message": f"no profile found; config={config_path or 'not found'}",
                    "next_action": "运行 scripts/setup_connections.py 生成本机占位配置，再填入只读连接信息。",
                }
            )
    else:
        for engine, profile, cfg in profiles:
            rows.append(check_profile(engine, profile, cfg, smoke=not args.no_smoke))

    output = {"config_path": str(config_path) if config_path else None, "profiles": rows}
    if args.json or args.format == "json":
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"config_path: {output['config_path'] or 'not found'}")
        print_table(rows)
    ok = all(row["status"] in {"ok", "configured"} for row in rows)
    return 0 if ok or args.offline_ok else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "failed", "message": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
