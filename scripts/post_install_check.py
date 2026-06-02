#!/usr/bin/env python3
"""Post-install smoke report for internal-data-query."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from lib_data_sources import (
    SUPPORTED_ENGINES,
    iter_profile_configs,
    load_config_with_path,
    profile_missing_fields,
    profile_placeholder_fields,
)


REQUIRED_FILES = ("SKILL.md", "manifest.json", "scripts/setup_connections.py")


def run(root: Path, command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    return {
        "command": command,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "output": " ".join((proc.stdout + proc.stderr).split())[:600],
    }


def profile_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for engine, profile, cfg in iter_profile_configs(config):
        missing = profile_missing_fields(engine, cfg)
        placeholders = profile_placeholder_fields(engine, cfg)
        if missing:
            status = "missing_fields"
        elif placeholders:
            status = "placeholder"
        else:
            status = "configured"
        rows.append(
            {
                "engine": engine,
                "profile": profile,
                "status": status,
                "missing_fields": missing,
                "placeholder_fields": placeholders,
            }
        )
    return rows


def build_report(root: Path, config_path: Path | None, env_file: Path | None, real_smoke: bool) -> dict[str, Any]:
    required = {rel: (root / rel).exists() for rel in REQUIRED_FILES}
    manifest = run(root, [sys.executable, "scripts/validate_manifest.py"])
    sensitive = run(root, [sys.executable, "scripts/scan_sensitive_info.py", "."])
    setup_help = run(root, [sys.executable, "scripts/setup_connections.py", "--help"])
    schema_smoke = run(root, [sys.executable, "scripts/search_schema.py", "refund", "--limit", "1"])

    config_error = None
    try:
        resolved_config, config = load_config_with_path(config_path, env_file)
    except (FileNotFoundError, RuntimeError) as exc:
        resolved_config = config_path.expanduser() if config_path else None
        config = {}
        config_error = str(exc)
    profiles = profile_rows(config)
    configured_engines = {row["engine"] for row in profiles if row["status"] == "configured"}
    present_engines = {row["engine"] for row in profiles}
    missing_sources = [engine for engine in SUPPORTED_ENGINES if engine not in present_engines]
    incomplete_sources = sorted({row["engine"] for row in profiles if row["status"] != "configured"})

    connection_smoke: dict[str, Any] = {"status": "skipped", "reason": "pass --real-smoke to connect to real data sources"}
    if real_smoke and config_error:
        connection_smoke = {"status": "missing_config", "reason": config_error}
    elif real_smoke and resolved_config:
        connection_smoke = run(root, [sys.executable, "scripts/check_connections.py", "--config", str(resolved_config)])
        connection_smoke["status"] = "ok" if connection_smoke["ok"] else "failed"
    elif real_smoke:
        connection_smoke = {"status": "missing_config", "reason": "no config file found"}

    installed_ok = all(required.values()) and manifest["ok"] and sensitive["ok"]
    configured_ok = bool(configured_engines)
    connected_ok = connection_smoke.get("status") == "ok"
    query_verified = "skipped"

    return {
        "package": {
            "root": str(root),
            "required_files": required,
            "installed": installed_ok,
        },
        "checks": {
            "manifest": manifest,
            "sensitive_scan": sensitive,
            "setup_help": setup_help,
            "schema_offline_smoke": schema_smoke,
        },
        "config": {
            "path": str(resolved_config) if resolved_config else None,
            "error": config_error,
            "profiles": profiles,
            "configured_sources": sorted(configured_engines),
            "missing_sources": missing_sources,
            "incomplete_sources": incomplete_sources,
        },
        "status": {
            "installed": "ok" if installed_ok else "failed",
            "configured": "ok" if configured_ok else "missing",
            "connected": connection_smoke.get("status", "skipped"),
            "query_verified": query_verified,
        },
        "connection_smoke": connection_smoke,
        "next_actions": [
            "Use scripts/setup_connections.py --add-sources <sources> to add missing local profiles without overwriting existing profiles.",
            "Run scripts/post_install_check.py --real-smoke only when VPN/network and readonly accounts are available.",
            "Restart Codex to pick up new skills.",
        ],
    }


def print_text(report: dict[str, Any]) -> None:
    print("# internal-data-query post-install check")
    print(f"root: {report['package']['root']}")
    print("required_files:")
    for rel, exists in report["package"]["required_files"].items():
        print(f"- {rel}: {'yes' if exists else 'missing'}")
    print("status:")
    for key, value in report["status"].items():
        print(f"- {key}: {value}")
    print(f"config_path: {report['config']['path'] or 'not found'}")
    if report["config"].get("error"):
        print(f"config_error: {report['config']['error']}")
    print(f"configured_sources: {', '.join(report['config']['configured_sources']) or 'none'}")
    print(f"missing_sources: {', '.join(report['config']['missing_sources']) or 'none'}")
    print(f"incomplete_sources: {', '.join(report['config']['incomplete_sources']) or 'none'}")
    print("checks:")
    for name, row in report["checks"].items():
        print(f"- {name}: {'PASS' if row['ok'] else 'FAIL'}")
    print(f"real_connection_smoke: {report['connection_smoke'].get('status')}")
    print("next_actions:")
    for action in report["next_actions"]:
        print(f"- {action}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run post-install checks for internal-data-query.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--config", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--real-smoke", action="store_true", help="Attempt real source connectivity checks.")
    parser.add_argument("--offline-ok", action="store_true", help="Return 0 when install checks pass even if config/real smoke is missing.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    report = build_report(root, args.config, args.env_file, args.real_smoke)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text(report)

    install_ok = report["status"]["installed"] == "ok" and all(row["ok"] for row in report["checks"].values())
    config_ok = report["status"]["configured"] == "ok"
    connected_ok = report["status"]["connected"] in {"ok", "skipped"}
    if args.real_smoke and report["status"]["connected"] != "ok":
        return 1
    if install_ok and (args.offline_ok or (config_ok and connected_ok)):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
