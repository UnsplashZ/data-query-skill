#!/usr/bin/env python3
"""Offline eval pack for the internal data query skill.

The harness intentionally does not connect to real data sources. It executes
available local checks, reports missing in-flight scripts as BLOCKED, and uses
JSON fixtures for Metabase coverage.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"


@dataclass
class EvalResult:
    name: str
    status: str
    detail: str
    command: list[str] | None = None


def rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def run_command(
    root: Path,
    name: str,
    command: list[str],
    *,
    expect_code: int | None = 0,
    missing_script_blocks: bool = True,
    output_must_contain: str | None = None,
    output_must_not_contain: str | None = None,
) -> EvalResult:
    script = root / command[1] if len(command) > 1 and command[0] == sys.executable else None
    if missing_script_blocks and script and not script.exists():
        return EvalResult(name, BLOCKED, f"依赖脚本不存在: {rel(root, script)}", command)

    proc = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    output = (proc.stdout + proc.stderr).strip()
    if expect_code is not None and proc.returncode != expect_code:
        return EvalResult(
            name,
            FAIL,
            f"退出码 {proc.returncode}，期望 {expect_code}: {shorten(output)}",
            command,
        )
    if output_must_contain and output_must_contain.lower() not in output.lower():
        return EvalResult(name, FAIL, f"输出缺少 `{output_must_contain}`: {shorten(output)}", command)
    if output_must_not_contain and output_must_not_contain.lower() in output.lower():
        return EvalResult(name, FAIL, f"输出不应包含 `{output_must_not_contain}`: {shorten(output)}", command)
    return EvalResult(name, PASS, shorten(output) or "命令成功", command)


def shorten(text: str, limit: int = 500) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def eval_metabase_mock(root: Path) -> EvalResult:
    mock_dir = root / "evals" / "fixtures" / "metabase-mock"
    required = ["search.json", "card-321.json", "run-card-321.json", "config.yaml"]
    missing = [name for name in required if not (mock_dir / name).exists()]
    if missing:
        return EvalResult("metabase_mock", FAIL, "缺少 mock fixture: " + ", ".join(missing))

    py = sys.executable
    params = json.dumps(
        [
            {"type": "date/single", "target": ["variable", ["template-tag", "start_date"]], "value": "2026-05-01"},
            {"type": "date/single", "target": ["variable", ["template-tag", "end_date"]], "value": "2026-06-01"},
        ]
    )
    with tempfile.TemporaryDirectory(prefix="internal-data-query-metabase-eval-") as output_dir:
        checks = [
            run_command(
                root,
                "metabase_mock",
                [py, "scripts/metabase_search.py", "refund", "--mock-file", "evals/fixtures/metabase-mock/search.json", "--json"],
                output_must_contain="Refund Daily KPI Mock",
            ),
            run_command(
                root,
                "metabase_mock",
                [py, "scripts/metabase_get_card.py", "321", "--mock-file", "evals/fixtures/metabase-mock/card-321.json", "--json"],
                output_must_contain="native_sql",
            ),
            run_command(
                root,
                "metabase_mock",
                [
                    py,
                    "scripts/metabase_run_card.py",
                    "321",
                    "--mock-file",
                    "evals/fixtures/metabase-mock/run-card-321.json",
                    "--parameters",
                    params,
                    "--output-dir",
                    output_dir,
                    "--output-format",
                    "csv",
                ],
                output_must_contain="row_count",
            ),
        ]
    failed = [item for item in checks if item.status != PASS]
    if failed:
        first = failed[0]
        return EvalResult("metabase_mock", first.status, first.detail, first.command)
    return EvalResult("metabase_mock", PASS, "search/get/run mock scripts 可离线校验", checks[-1].command)


def eval_lightweight_boundary(root: Path) -> EvalResult:
    requirements = (root / "requirements.txt").read_text(encoding="utf-8", errors="ignore")
    req_lower = requirements.lower()
    heavy = [
        "wrenai",
        "vanna",
        "dbt",
        "airflow",
        "great-expectations",
        "superset",
        "uvicorn",
        "fastapi",
        "flask",
        "django",
    ]
    found_heavy = [pkg for pkg in heavy if re.search(rf"(^|\n)\s*{re.escape(pkg)}([<=>\[]|$)", req_lower)]
    if found_heavy:
        return EvalResult("lightweight_boundary", FAIL, "requirements 包含重型平台依赖: " + ", ".join(found_heavy))

    script_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore").lower()
        for path in (root / "scripts").glob("*.py")
        if path.name != "eval_skill_pack.py"
    )
    forbidden_runtime_terms = ["from mcp", "import mcp", "uvicorn.run", "app.run(", "serve_forever("]
    found_terms = [term for term in forbidden_runtime_terms if term in script_text]
    if found_terms:
        return EvalResult("lightweight_boundary", FAIL, "脚本疑似依赖 MCP/server/runtime: " + ", ".join(found_terms))
    return EvalResult("lightweight_boundary", PASS, "不依赖 MCP server、不启动常驻服务、不要求安装重型平台")


def eval_fixture_sensitivity(root: Path) -> EvalResult:
    evals_dir = root / "evals"
    text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in evals_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".md", ".sql", ".json", ".yaml", ".yml"}
    )
    forbidden = [
        r"https?://(?!metabase\.example\.invalid)[A-Za-z0-9.-]*\.(?:corp|internal|local|lan)(?:[:/]|$)",
        r"(?i)(password|secret|token|api_key)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{16,}",
        r"(?<!\d)1[3-9]\d{9}(?!\d)",
    ]
    for pattern in forbidden:
        if re.search(pattern, text):
            return EvalResult("fixture_sensitivity", FAIL, f"eval fixture 命中敏感模式: {pattern}")
    return EvalResult("fixture_sensitivity", PASS, "eval fixtures 未包含真实凭证、真实内部 URL 或手机号")


def eval_sensitive_sample_detection(root: Path) -> EvalResult:
    with tempfile.TemporaryDirectory(prefix="dq-sensitive-eval-") as tmp:
        sample = Path(tmp) / "sensitive-sample.env.example"
        token_key = "API_" + "TOKEN"
        jdbc_password_key = "pass" + "word"
        feishu_host = "opensplendid." + "feishu.cn"
        feishu_token_key = "spreadsheet_" + "token"
        sample.write_text(
            f"{token_key}=abcdefghijklmnopqrstuvwxyz123456\n"
            f"JDBC_URL=jdbc:mysql://db.example.invalid/app?{jdbc_password_key}=abcdefghijklmnopqrstuvwxyz\n"
            f"{feishu_token_key}: ABCDEFGHIJKLMNOPQRSTUVWX\n"
            f"URL: https://{feishu_host}/wiki/ABCDEFGHIJKLMNOPQRSTUVWX\n",
            encoding="utf-8",
        )
        proc = subprocess.run(
            [sys.executable, "scripts/scan_sensitive_info.py", str(sample), "--max-findings", "10"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
    output = proc.stdout + proc.stderr
    required = ["api-token-assignment", "jdbc-url-with-password", "feishu-token-assignment", "feishu-url"]
    missing = [item for item in required if item not in output]
    if proc.returncode != 1 or missing:
        return EvalResult("sensitive_sample_detection", FAIL, f"敏感样例未按预期命中 {missing}: {shorten(output)}")
    return EvalResult("sensitive_sample_detection", PASS, "scanner 命中 token/JDBC/Feishu URL 样例")


def eval_install_config_flow(root: Path) -> EvalResult:
    with tempfile.TemporaryDirectory(prefix="dq-install-eval-") as tmp:
        config = Path(tmp) / "data-sources.yaml"
        setup = subprocess.run(
            [
                sys.executable,
                "scripts/setup_connections.py",
                "--non-interactive",
                "--output",
                str(config),
                "--overwrite",
            ],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        if setup.returncode != 0 or not config.exists():
            return EvalResult("install_config_flow", FAIL, f"setup non-interactive 失败: {shorten(setup.stdout + setup.stderr)}")
        checks = [
            run_command(root, "install_config_flow", [sys.executable, "scripts/setup_connections.py", "--help"], output_must_contain="non-interactive"),
            run_command(
                root,
                "install_config_flow",
                [sys.executable, "scripts/check_connections.py", "--config", str(config), "--offline-ok"],
                output_must_contain="missing",
            ),
            run_command(
                root,
                "install_config_flow",
                [sys.executable, "scripts/discover_data_sources.py", "--config", str(config)],
                output_must_contain="offline_knowledge",
            ),
        ]
        failed = [item for item in checks if item.status != PASS]
        if failed:
            first = failed[0]
            return EvalResult("install_config_flow", first.status, first.detail, first.command)
    return EvalResult("install_config_flow", PASS, "setup/check/discover 安装配置链路离线通过")


def eval_knowledge_capture_write_validate_search(root: Path) -> EvalResult:
    with tempfile.TemporaryDirectory(prefix="dqk-capture-eval-") as tmp:
        tmp_root = Path(tmp)
        shutil.copytree(root / "evals" / "fixtures" / "data-query-knowledge", tmp_root / "data-query-knowledge")
        text = (
            "- Metric: refund_capture_eval\n"
            "SELECT count(*) FROM refund_order_daily "
            "WHERE refund_created_at >= '2026-05-01' LIMIT 10"
        )
        capture = subprocess.run(
            [
                sys.executable,
                str(root / "scripts" / "capture_query_knowledge.py"),
                "--root",
                str(tmp_root),
                "--text",
                text,
            ],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        if capture.returncode != 0:
            return EvalResult("knowledge_capture_write_validate_search", FAIL, f"capture 写入失败: {shorten(capture.stdout + capture.stderr)}")
        written = capture.stdout.strip().splitlines()[-1] if capture.stdout.strip() else ""
        written_path = tmp_root / written
        if not written or not written_path.exists() or not written_path.read_text(encoding="utf-8").startswith("---\n"):
            return EvalResult("knowledge_capture_write_validate_search", FAIL, f"写入 candidate 缺少 YAML frontmatter: {written}")

        validate = subprocess.run(
            [sys.executable, str(root / "scripts" / "validate_query_knowledge.py"), "--root", str(tmp_root)],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        if validate.returncode != 0:
            return EvalResult("knowledge_capture_write_validate_search", FAIL, f"validate 未识别写入 candidate: {shorten(validate.stdout + validate.stderr)}")

        search = subprocess.run(
            [
                sys.executable,
                str(root / "scripts" / "search_query_knowledge.py"),
                "refund_capture_eval",
                "--root",
                str(tmp_root),
                "--include-candidate",
            ],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        output = search.stdout + search.stderr
        if search.returncode != 0 or "kcap-" not in output or "candidate" not in output:
            return EvalResult("knowledge_capture_write_validate_search", FAIL, f"search 未识别写入 candidate: {shorten(output)}")
    return EvalResult("knowledge_capture_write_validate_search", PASS, "candidate 非 dry-run 写入后可被 validate/search 识别")


def eval_knowledge_conflict_search(root: Path) -> EvalResult:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/search_query_knowledge.py",
            "refund",
            "--root",
            "evals/fixtures",
            "--include-candidate",
            "--status",
            "candidate",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    output = proc.stdout + proc.stderr
    required = [
        "candidate.refund_rate.order_count.v1",
        "effective_confidence=low",
        "conflicts_with=metric.refund_rate.monthly.v1",
    ]
    missing = [item for item in required if item not in output]
    if proc.returncode != 0 or missing:
        return EvalResult("knowledge_conflict_search", FAIL, f"冲突降级输出缺少 {missing}: {shorten(output)}")
    return EvalResult("knowledge_conflict_search", PASS, "search 输出 conflicts_with 线索与降级 effective_confidence")


def eval_run_query_help(root: Path) -> EvalResult:
    help_result = run_command(
        root,
        "run_query_help_contract",
        [sys.executable, "scripts/run_query.py", "--help"],
        output_must_contain="execution-stage",
    )
    if help_result.status != PASS:
        return help_result
    with tempfile.TemporaryDirectory(prefix="dq-run-query-eval-") as tmp:
        proc = subprocess.run(
            [
                sys.executable,
                "scripts/run_query.py",
                "--engine",
                "clickhouse",
                "--sql-file",
                "evals/fixtures/readonly.sql",
                "--mock-result-file",
                "evals/fixtures/run-query-mock-result.json",
                "--execution-stage",
                "sample",
                "--sample-limit",
                "100",
                "--validation-note",
                "offline mock execution validates report contract",
                "--output-dir",
                tmp,
            ],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        output = proc.stdout + proc.stderr
        required = ["static_check", "execution_stage", "sample", "confidence", "validation_notes", "row_count", "output_path"]
        missing = [item for item in required if item not in output]
        if proc.returncode != 0 or missing:
            return EvalResult("run_query_help_contract", FAIL, f"run_query mock 输出契约缺失 {missing}: {shorten(output)}")
    return EvalResult("run_query_help_contract", PASS, "run_query help 与 mock 成功输出契约均通过")


def build_results(root: Path) -> list[EvalResult]:
    py = sys.executable
    results = [
        run_command(root, "manifest", [py, "scripts/validate_manifest.py"]),
        run_command(root, "sensitive_scan", [py, "scripts/scan_sensitive_info.py"]),
        eval_sensitive_sample_detection(root),
        eval_install_config_flow(root),
        run_command(
            root,
            "sql_readonly",
            [py, "scripts/query_static_check.py", "--sql-file", "evals/fixtures/readonly.sql", "--engine", "clickhouse"],
        ),
        run_command(
            root,
            "sql_reject_dml",
            [py, "scripts/query_static_check.py", "--sql-file", "evals/fixtures/reject-dml.sql", "--engine", "mysql"],
            expect_code=1,
        ),
        run_command(
            root,
            "sql_reject_security_risk",
            [py, "scripts/query_static_check.py", "--sql-file", "evals/fixtures/security-risk.sql", "--engine", "clickhouse"],
            expect_code=1,
            output_must_contain="dangerous",
        ),
        run_command(
            root,
            "sql_missing_time_range",
            [
                py,
                "scripts/query_static_check.py",
                "--sql-file",
                "evals/fixtures/missing-time-range.sql",
                "--engine",
                "clickhouse",
            ],
            expect_code=None,
            output_must_contain="time",
        ),
        run_command(root, "schema_search", [py, "scripts/search_schema.py", "refund", "--limit", "3"]),
        run_command(root, "old_sql_search", [py, "scripts/search_old_sql.py", "退款", "--limit", "3"]),
        run_command(
            root,
            "knowledge_validate",
            [py, "scripts/validate_query_knowledge.py", "--root", "evals/fixtures"],
        ),
        run_command(
            root,
            "knowledge_search_approved",
            [
                py,
                "scripts/search_query_knowledge.py",
                "refund",
                "--root",
                "evals/fixtures",
                "--status",
                "approved",
            ],
            output_must_not_contain="candidate.refund_rate.order_count.v1",
        ),
        run_command(
            root,
            "knowledge_sync_report",
            [py, "scripts/report_query_knowledge_sync.py", "--root", "evals/fixtures"],
        ),
        run_command(
            root,
            "knowledge_migrate_dry_run",
            [py, "scripts/migrate_query_knowledge.py", "--root", "evals/fixtures/data-query-knowledge-old", "--dry-run"],
            output_must_contain="MIGRATE",
        ),
        run_command(
            root,
            "knowledge_capture_dry_run",
            [
                py,
                "scripts/capture_query_knowledge.py",
                "evals/fixtures/query-case.md",
                "--root",
                "evals/fixtures",
                "--dry-run",
            ],
            output_must_contain="candidate",
        ),
        eval_knowledge_capture_write_validate_search(root),
        eval_knowledge_conflict_search(root),
        eval_run_query_help(root),
        run_command(
            root,
            "knowledge_suggest_capture",
            [
                py,
                "scripts/suggest_knowledge_capture.py",
                "--session",
                "evals/fixtures/query-session.json",
                "--case",
                "stable_prompt",
            ],
            output_must_contain="candidate",
        ),
        eval_metabase_mock(root),
        eval_lightweight_boundary(root),
        eval_fixture_sensitivity(root),
    ]
    return results


def print_text(results: list[EvalResult]) -> None:
    for item in results:
        cmd = " ".join(item.command) if item.command else ""
        cmd_suffix = f" | {cmd}" if cmd else ""
        print(f"{item.status}: {item.name}{cmd_suffix}")
        print(f"  {item.detail}")
    counts = {status: sum(1 for item in results if item.status == status) for status in [PASS, FAIL, BLOCKED]}
    print(f"\nSUMMARY: pass={counts[PASS]} fail={counts[FAIL]} blocked={counts[BLOCKED]}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the offline eval pack for this skill.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Skill root. Defaults to the parent of scripts/.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument(
        "--allow-blocked",
        action="store_true",
        help="Return 0 when only BLOCKED checks remain. FAIL still returns non-zero.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    results = build_results(root)
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "name": item.name,
                        "status": item.status,
                        "detail": item.detail,
                        "command": item.command,
                    }
                    for item in results
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print_text(results)

    has_fail = any(item.status == FAIL for item in results)
    has_blocked = any(item.status == BLOCKED for item in results)
    if has_fail or (has_blocked and not args.allow_blocked):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
