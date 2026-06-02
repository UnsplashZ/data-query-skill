#!/usr/bin/env python3
"""Create a local connection profile for internal-data-query."""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path
from typing import Any


SOURCE_FIELDS: dict[str, list[dict[str, Any]]] = {
    "metabase": [
        {"key": "base_url", "label": "Base URL", "default": "https://metabase.example.invalid"},
        {"key": "api_key", "label": "API key", "secret": True},
        {"key": "session_id", "label": "Session id", "secret": True},
        {"key": "username", "label": "Username"},
        {"key": "password", "label": "Password", "secret": True},
    ],
    "clickhouse": [
        {"key": "host", "label": "Host", "default": "clickhouse.example.invalid"},
        {"key": "port", "label": "Port", "default": "9000"},
        {"key": "database", "label": "Database", "default": "analytics"},
        {"key": "username", "label": "Username", "default": "readonly_user"},
        {"key": "password", "label": "Password", "secret": True},
        {"key": "secure", "label": "Use TLS/secure connection", "default": "false", "bool": True},
    ],
    "odps": [
        {"key": "endpoint", "label": "Endpoint", "default": "https://maxcompute-endpoint.example.invalid/api"},
        {"key": "project", "label": "Project"},
        {"key": "access_id", "label": "Access ID"},
        {"key": "access_key", "label": "Access key", "secret": True},
        {"key": "tunnel_endpoint", "label": "Tunnel endpoint"},
    ],
    "mysql": [
        {"key": "host", "label": "Host", "default": "mysql.example.invalid"},
        {"key": "port", "label": "Port", "default": "3306"},
        {"key": "database", "label": "Database", "default": "app_readonly"},
        {"key": "username", "label": "Username", "default": "readonly_user"},
        {"key": "password", "label": "Password", "secret": True},
        {"key": "charset", "label": "Charset", "default": "utf8mb4"},
        {"key": "ssl_disabled", "label": "Disable SSL", "default": "true", "bool": True},
    ],
}


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def prompt_text(label: str, default: str = "", secret: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    message = f"{label}{suffix}: "
    value = getpass.getpass(message) if secret else input(message)
    return value.strip() or default


def prompt_yes_no(label: str, default: bool = True) -> bool:
    suffix = "Y/n" if default else "y/N"
    raw = input(f"{label} [{suffix}]: ").strip()
    if not raw:
        return default
    return raw.lower() in {"y", "yes", "1", "true"}


def scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    text = str(value)
    if not text:
        return ""
    if any(ch in text for ch in [":", "#", "{", "}", "[", "]", ",", "&", "*", "!", "|", ">", "'", '"', "%", "@", "`"]):
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    lowered = text.lower()
    if lowered in {"true", "false", "null", "yes", "no", "on", "off"}:
        return '"' + text + '"'
    return text


def yaml_dump(data: dict[str, Any]) -> str:
    lines = [
        "# Local connection profile for internal-data-query.",
        "# Keep this file on the user's machine. Do not commit it or put it back into the shared skill zip.",
        "# File permissions should be 0600 where the operating system supports chmod.",
        "profiles:",
    ]
    profiles = data.get("profiles", {})
    for engine, engine_profiles in profiles.items():
        lines.append(f"  {engine}:")
        for profile, values in engine_profiles.items():
            lines.append(f"    {profile}:")
            for key, value in values.items():
                lines.append(f"      {key}: {scalar(value)}")
    lines.append("")
    return "\n".join(lines)


def build_placeholder(sources: list[str], profile: str) -> dict[str, Any]:
    data: dict[str, Any] = {"profiles": {}}
    for source in sources:
        values: dict[str, Any] = {}
        for field in SOURCE_FIELDS[source]:
            value = field.get("default", "")
            if field.get("bool"):
                values[field["key"]] = parse_bool(value)
            else:
                values[field["key"]] = value
        values["readonly"] = True
        data["profiles"][source] = {profile: values}
    return data


def build_interactive(sources: list[str], profile: str) -> dict[str, Any]:
    data: dict[str, Any] = {"profiles": {}}
    print("internal-data-query connection setup")
    print("This writes a local config only. It does not edit the skill package, repository docs, manifest, or generated SQL.")
    print("Configure readonly data sources. Press Enter to keep defaults or leave optional fields empty.")
    print("Metabase can use API key, session id, or username/password. Configure only the method your team uses.")
    for source in sources:
        if not prompt_yes_no(f"Configure {source}", default=True):
            continue
        values: dict[str, Any] = {}
        for field in SOURCE_FIELDS[source]:
            raw = prompt_text(
                f"{source}.{field['key']} - {field['label']}",
                str(field.get("default", "")),
                bool(field.get("secret")),
            )
            if field.get("bool"):
                values[field["key"]] = parse_bool(raw)
            else:
                values[field["key"]] = raw
        values["readonly"] = True
        data["profiles"][source] = {profile: values}
    return data


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create a local data-sources.yaml for internal-data-query. "
            "Credentials stay on this machine; the script does not write to the repository by default."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.home() / ".internal-data-query" / "data-sources.yaml",
        help="Output YAML path. Default: ~/.internal-data-query/data-sources.yaml",
    )
    parser.add_argument("--profile", default="default")
    parser.add_argument(
        "--sources",
        default="metabase,clickhouse,odps,mysql",
        help="Comma-separated sources: metabase,clickhouse,odps,mysql",
    )
    parser.add_argument("--non-interactive", action="store_true", help="Write placeholder profiles without prompting.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output file.")
    args = parser.parse_args()

    output = args.output.expanduser()
    sources = [item.strip().lower() for item in args.sources.split(",") if item.strip()]
    unknown = [item for item in sources if item not in SOURCE_FIELDS]
    if unknown:
        raise RuntimeError(f"Unknown source(s): {', '.join(unknown)}")
    if output.exists() and not args.overwrite:
        raise RuntimeError(f"Output already exists: {output}. Pass --overwrite to replace it.")

    if args.non_interactive:
        data = build_placeholder(sources, args.profile)
    elif not sys.stdin.isatty():
        raise RuntimeError(
            "Interactive setup requires a TTY. Re-run in a terminal, or use "
            "--non-interactive to create placeholders, then edit the YAML locally."
        )
    else:
        data = build_interactive(sources, args.profile)
    wrote_placeholder = bool(args.non_interactive)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml_dump(data), encoding="utf-8")
    chmod_applied = False
    try:
        os.chmod(output, 0o600)
        chmod_applied = True
    except OSError:
        pass

    configured_sources = sorted(data.get("profiles", {}).keys())
    mode = "placeholder" if wrote_placeholder else "interactive"
    print(f"OK: wrote local connection config: {output}")
    print(f"Mode: {mode}")
    print(f"Configured source sections: {', '.join(configured_sources) if configured_sources else 'none'}")
    print(f"Permissions: {'0600 applied' if chmod_applied else '0600 not confirmed; set it manually if required'}")
    print("")
    print("Status report:")
    print("  - This file is local to the user machine.")
    print("  - Do not commit it, copy it into the skill zip, paste it into chat, or include it in generated SQL.")
    print("  - Scripts read ~/.internal-data-query/data-sources.yaml automatically when --config is omitted.")
    print("  - You can also set INTERNAL_DATA_QUERY_CONFIG or pass --config explicitly.")
    if wrote_placeholder:
        print("  - Placeholder values were written; edit the YAML locally before real queries.")
    print("")
    print("Next smoke checks:")
    print("  python scripts/setup_connections.py --help")
    print(f"  python scripts/check_connections.py --config {output} --offline-ok")
    print(f"  python scripts/discover_data_sources.py --config {output}")
    print("  python scripts/metabase_search.py refund --mock-file evals/fixtures/metabase-mock/search.json --json")
    print("  python scripts/metabase_get_card.py 321 --mock-file evals/fixtures/metabase-mock/card-321.json --json")
    print("  python scripts/run_query.py --help")
    if wrote_placeholder:
        print("  Placeholder config is not a real connectivity smoke target; replace it before Metabase/search/query calls.")
    print("")
    print("After setup, you can trigger this skill with natural language such as:")
    print("  帮我查一下数据 / 写个 SQL / 看一下 Metabase 里有没有这个指标 / 验证这个报表口径")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)
