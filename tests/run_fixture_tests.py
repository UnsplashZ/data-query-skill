#!/usr/bin/env python3
"""Offline fixture smoke tests for data-query-skill scripts."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
FIXTURES = REPO / "tests" / "fixtures"
PYTHON = sys.executable
SUBPROCESS_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}
SUBPROCESS_ENV.pop("INTERNAL_DATA_QUERY_SCHEMA_INDEX", None)

sys.path.insert(0, str(SCRIPTS))

from lib_masking import mask_row, residual_scan_text  # noqa: E402
from lib_table_list import parse_table_list  # noqa: E402
from query_static_check import check_sql  # noqa: E402


def run(args: list[str], *, cwd: Path = REPO, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    proc_env = {**SUBPROCESS_ENV, **(env or {})}
    proc = subprocess.run([PYTHON, *args], cwd=cwd, text=True, encoding="utf-8", capture_output=True, check=False, env=proc_env)
    if proc.returncode != 0:
        raise AssertionError(f"command failed: {' '.join(args)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    return proc


def write_candidate(root: Path, item_id: str = "kcap-fixture", body: str = "- fixture only") -> Path:
    knowledge = root / "data-query-work" / "knowledge" / "candidates"
    knowledge.mkdir(parents=True, exist_ok=True)
    path = knowledge / f"2026-06-02__fixture__metric__candidate-{item_id}.md"
    path.write_text(
        f"""---
id: {item_id}
schema_version: "1.0"
status: candidate
created_by: fixture
reviewed_by: []
approved_by: []
domain: fixture
metric: []
grain: ""
source: []
source_status: observed
confidence: low
risk_level: medium
expires_at: null
supersedes: []
conflicts_with: []
validation_evidence: []
last_verified_at: null
sync_notes: []
maturity: observed
capture_trigger: manual
source_interaction: []
---

# fixture candidate

## Evidence

{body}
""",
        encoding="utf-8",
    )
    return path


def write_schema_fixture(root: Path, name: str) -> Path:
    schema_dir = root / "data-query-work" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    target = schema_dir / name
    shutil.copyfile(FIXTURES / "schema-index" / "unified_schema_index.json", target)
    return target


def test_table_list() -> None:
    txt = parse_table_list(FIXTURES / "table-list" / "tables.txt", default_database="dm")
    assert len(txt["requested"]) == 4
    assert txt["duplicate_aliases"], "txt duplicate alias should be detected"
    csv_plan = parse_table_list(FIXTURES / "table-list" / "tables.csv", table_column="table_name", default_database="dm")
    assert "dm.orders" in csv_plan["canonical"]
    xlsx_plan = parse_table_list(FIXTURES / "table-list" / "tables.xlsx", table_column="table_name", default_database="dm")
    assert "dm.drh_users" in xlsx_plan["canonical"]


def test_masking() -> None:
    phone = "138" + "0013" + "8000"
    email = "a" + "@example.com"
    row = {
        "phone": phone,
        "callback_response": json.dumps({"email": email, "token": "abcdefghijklmnopqrstuvwxyz1234567890"}),
        "safe": "ok",
    }
    masked = mask_row(row)
    text = json.dumps(masked, ensure_ascii=False)
    assert phone not in text
    assert email not in text
    assert not residual_scan_text(text)


def test_refresh_and_sample_dry_run() -> None:
    with tempfile.TemporaryDirectory(prefix="dq fixture ") as tmp:
        root = Path(tmp)
        run(
            [
                "scripts/refresh_schema.py",
                "--engine",
                "clickhouse",
                "--profile",
                "default",
                "--table-list",
                str(FIXTURES / "table-list" / "tables.txt"),
                "--default-database",
                "dm",
                "--root",
                str(root),
                "--dry-run",
            ]
        )
        assert list((root / "data-query-work" / "discovery-reports").glob("*schema-refresh*.md"))
        run(
            [
                "scripts/refresh_schema.py",
                "--engine",
                "clickhouse",
                "--profile",
                "default",
                "--table-list",
                str(FIXTURES / "table-list" / "tables.xlsx"),
                "--table-column",
                "table_name",
                "--default-database",
                "dm",
                "--root",
                str(root),
                "--dry-run",
            ]
        )
        config_result = run(
            [
                "scripts/refresh_schema.py",
                "--engine",
                "clickhouse",
                "--profile",
                "default",
                "--config",
                str(FIXTURES / "config" / "data-sources.yaml"),
                "--table-list",
                str(FIXTURES / "table-list" / "tables.csv"),
                "--table-column",
                "table_name",
                "--root",
                str(root),
                "--dry-run",
                "--json",
            ]
        )
        config_summary = json.loads(config_result.stdout)
        assert any(item["canonical"] == "dm.orders" for item in config_summary["requested"])
        scoped_list = root / "scoped tables.txt"
        scoped_list.write_text("dm.orders\ndm.drh_users\ndm.events_local\ndm.missing_table\n", encoding="utf-8")
        run(
            [
                "scripts/sample_tables.py",
                "--engine",
                "clickhouse",
                "--profile",
                "default",
                "--from-schema-index",
                str(FIXTURES / "schema-index" / "unified_schema_index.json"),
                "--table-list",
                str(scoped_list),
                "--rows",
                "2",
                "--root",
                str(root),
                "--dry-run",
            ]
        )
        status_files = list((root / "data-query-work" / "exports").glob("*sample-tables*status.csv"))
        assert status_files
        status_text = status_files[-1].read_text(encoding="utf-8-sig")
        assert "drh_final" in status_text
        assert "sign_positive" in status_text
        assert "events_local" in status_text
        assert "skipped" in status_text
        report_text = list((root / "data-query-work" / "discovery-reports").glob("*sample-tables*report.md"))[-1].read_text(encoding="utf-8")
        assert "dm.missing_table" in report_text
        assert "Residual Scan" in report_text


def test_schema_index_discovery() -> None:
    clean_env = {"INTERNAL_DATA_QUERY_SCHEMA_INDEX": ""}
    with tempfile.TemporaryDirectory(prefix="dq schema unified ") as tmp:
        root = Path(tmp)
        write_schema_fixture(root, "unified_schema_index.json")
        search = run(["scripts/search_schema.py", "orders", "--root", str(root), "--json"], env=clean_env)
        rows = json.loads(search.stdout)
        assert rows and rows[0]["source_file"] == "unified_schema_index.json"
        discover = run(["scripts/discover_data_sources.py", "--root", str(root), "--json"], env=clean_env)
        status = json.loads(discover.stdout)["offline_knowledge"]["schema_kb"]
        assert status["exists"] is True
        assert status["path"].endswith("unified_schema_index.json")

    with tempfile.TemporaryDirectory(prefix="dq schema all sources ") as tmp:
        root = Path(tmp)
        write_schema_fixture(root, "all_sources_schema_index.json")
        search = run(["scripts/search_schema.py", "orders", "--root", str(root), "--json"], env=clean_env)
        rows = json.loads(search.stdout)
        assert rows and rows[0]["source_file"] == "all_sources_schema_index.json"
        discover = run(["scripts/discover_data_sources.py", "--root", str(root), "--json"], env=clean_env)
        status = json.loads(discover.stdout)["offline_knowledge"]["schema_kb"]
        assert status["exists"] is True
        assert status["path"].endswith("all_sources_schema_index.json")

    with tempfile.TemporaryDirectory(prefix="dq schema repo priority ") as tmp:
        root = Path(tmp)
        write_schema_fixture(root, "all_sources_schema_index.json")
        reference_dir = root / "references" / "schema-kb"
        reference_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIXTURES / "schema-index" / "unified_schema_index.json", reference_dir / "unified_schema_index.json")
        search = run(["scripts/search_schema.py", "orders", "--root", str(root), "--json"], env=clean_env)
        rows = json.loads(search.stdout)
        assert rows and rows[0]["source_file"] == "all_sources_schema_index.json"
        discover = run(["scripts/discover_data_sources.py", "--root", str(root), "--json"], env=clean_env)
        status = json.loads(discover.stdout)["offline_knowledge"]["schema_kb"]
        assert "/data-query-work/schema/all_sources_schema_index.json" in status["path"]

    with tempfile.TemporaryDirectory(prefix="dq schema multi ") as tmp:
        root = Path(tmp)
        write_schema_fixture(root, "all_sources_schema_index.json")
        write_schema_fixture(root, "unified_schema_index.json")
        search = run(["scripts/search_schema.py", "orders", "--root", str(root), "--json"], env=clean_env)
        rows = json.loads(search.stdout)
        assert rows and rows[0]["source_file"] == "unified_schema_index.json"

    with tempfile.TemporaryDirectory(prefix="dq schema override ") as tmp:
        root = Path(tmp)
        write_schema_fixture(root, "unified_schema_index.json")
        explicit = write_schema_fixture(root, "all_sources_schema_index.json")
        search = run(["scripts/search_schema.py", "orders", "--root", str(root), "--file", str(explicit), "--json"], env=clean_env)
        rows = json.loads(search.stdout)
        assert rows and rows[0]["source_file"] == "all_sources_schema_index.json"

    with tempfile.TemporaryDirectory(prefix="dq schema env ") as tmp:
        root = Path(tmp)
        write_schema_fixture(root, "unified_schema_index.json")
        env_index = write_schema_fixture(root, "all_sources_schema_index.json")
        env = {"INTERNAL_DATA_QUERY_SCHEMA_INDEX": str(env_index)}
        search = run(["scripts/search_schema.py", "orders", "--root", str(root), "--json"], env=env)
        rows = json.loads(search.stdout)
        assert rows and rows[0]["source_file"] == "all_sources_schema_index.json"
        discover = run(["scripts/discover_data_sources.py", "--root", str(root), "--json"], env=env)
        status = json.loads(discover.stdout)["offline_knowledge"]["schema_kb"]
        assert status["configured_by"] == "env"
        assert status["path"].endswith("all_sources_schema_index.json")

    with tempfile.TemporaryDirectory(prefix="dq schema config ") as tmp:
        root = Path(tmp)
        write_schema_fixture(root, "all_sources_schema_index.json")
        config = root / "data-query-work" / "schema" / "schema-index.config.json"
        config.write_text(json.dumps({"schema_index": "all_sources_schema_index.json"}), encoding="utf-8")
        discover = run(["scripts/discover_data_sources.py", "--root", str(root), "--json"], env=clean_env)
        status = json.loads(discover.stdout)["offline_knowledge"]["schema_kb"]
        assert status["configured_by"] == "config"
        assert status["path"].endswith("all_sources_schema_index.json")

    with tempfile.TemporaryDirectory(prefix="dq schema config missing ") as tmp:
        root = Path(tmp)
        config_dir = root / "data-query-work" / "schema"
        config_dir.mkdir(parents=True, exist_ok=True)
        config = config_dir / "schema-index.config.json"
        config.write_text(json.dumps({"schema_index": "missing_schema_index.json"}), encoding="utf-8")
        proc = subprocess.run(
            [PYTHON, "scripts/search_schema.py", "orders", "--root", str(root), "--json"],
            cwd=REPO,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
            env={**SUBPROCESS_ENV, **clean_env},
        )
        assert proc.returncode == 2
        payload = json.loads(proc.stdout)
        assert payload["schema_index_candidates"] == [str((config_dir / "missing_schema_index.json").resolve())]

    with tempfile.TemporaryDirectory(prefix="dq schema ambiguous ") as tmp:
        root = Path(tmp)
        write_schema_fixture(root, "foo_schema_index.json")
        write_schema_fixture(root, "bar_schema_index.json")
        proc = subprocess.run(
            [PYTHON, "scripts/search_schema.py", "orders", "--root", str(root)],
            cwd=REPO,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
            env={**SUBPROCESS_ENV, **clean_env},
        )
        assert proc.returncode == 2
        assert "multiple schema indexes found" in proc.stdout
        json_proc = subprocess.run(
            [PYTHON, "scripts/search_schema.py", "orders", "--root", str(root), "--json"],
            cwd=REPO,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
            env={**SUBPROCESS_ENV, **clean_env},
        )
        assert json_proc.returncode == 2
        ambiguous_payload = json.loads(json_proc.stdout)
        assert "multiple schema indexes found" in ambiguous_payload["error"]
        assert len(ambiguous_payload["schema_index_candidates"]) == 2

    with tempfile.TemporaryDirectory(prefix="dq schema missing explicit ") as tmp:
        root = Path(tmp)
        missing = root / "data-query-work" / "schema" / "missing_schema_index.json"
        proc = subprocess.run(
            [PYTHON, "scripts/search_schema.py", "orders", "--root", str(root), "--file", str(missing), "--json"],
            cwd=REPO,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
            env={**SUBPROCESS_ENV, **clean_env},
        )
        assert proc.returncode == 2
        missing_payload = json.loads(proc.stdout)
        assert "schema index not found" in missing_payload["error"]
        assert missing_payload["schema_index_candidates"] == [str(missing)]

    with tempfile.TemporaryDirectory(prefix="dq schema missing env ") as tmp:
        root = Path(tmp)
        missing = root / "data-query-work" / "schema" / "missing_schema_index.json"
        proc = subprocess.run(
            [PYTHON, "scripts/search_schema.py", "orders", "--root", str(root), "--json"],
            cwd=REPO,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
            env={**SUBPROCESS_ENV, "INTERNAL_DATA_QUERY_SCHEMA_INDEX": str(missing)},
        )
        assert proc.returncode == 2
        missing_payload = json.loads(proc.stdout)
        assert "INTERNAL_DATA_QUERY_SCHEMA_INDEX" in missing_payload["error"]

    with tempfile.TemporaryDirectory(prefix="dq schema sample ") as tmp:
        root = Path(tmp)
        write_schema_fixture(root, "all_sources_schema_index.json")
        sample = run(
            [
                "scripts/sample_tables.py",
                "--engine",
                "clickhouse",
                "--rows",
                "1",
                "--root",
                str(root),
                "--dry-run",
                "--json",
            ],
            env=clean_env,
        )
        result = json.loads(sample.stdout)
        assert result["schema_index"].endswith("all_sources_schema_index.json")


def test_static_check_warnings() -> None:
    result = check_sql("SELECT * FROM dm.drh_users FINAL u WHERE dt >= '20260601' LIMIT 2", "clickhouse")
    codes = {item["code"] for item in result["findings"]}
    assert "clickhouse_old_final_alias" in codes
    assert "clickhouse_string_date_compare" in codes


def test_knowledge_promotion_and_validate() -> None:
    with tempfile.TemporaryDirectory(prefix="dq knowledge ") as tmp:
        root = Path(tmp)
        candidate = write_candidate(root)
        evidence = root / "review.md"
        shutil.copyfile(FIXTURES / "review.md", evidence)
        run(
            [
                "scripts/promote_query_knowledge.py",
                "kcap-fixture",
                "--to",
                "approved",
                "--actor",
                "fixture",
                "--reviewer",
                "fixture",
                "--approver",
                "fixture",
                "--evidence",
                str(evidence),
                "--root",
                str(root),
                "--dry-run",
            ]
        )
        run(
            [
                "scripts/promote_query_knowledge.py",
                "kcap-fixture",
                "--to",
                "approved",
                "--actor",
                "fixture",
                "--reviewer",
                "fixture",
                "--approver",
                "fixture",
                "--evidence",
                str(evidence),
                "--root",
                str(root),
            ]
        )
        assert not candidate.exists(), "promotion should move the old candidate file"
        approved = list((root / "data-query-work" / "knowledge" / "approved").glob("*approved-kcap-fixture.md"))
        assert approved, "approved file should exist after promotion"
        run(["scripts/validate_query_knowledge.py", "--root", str(root)])


def test_patch_query_knowledge() -> None:
    with tempfile.TemporaryDirectory(prefix="dq patch ") as tmp:
        root = Path(tmp)
        write_candidate(root, "kcap-old", "- old table")
        write_candidate(root, "kcap-new", "- current metric")
        evidence = root / "review.md"
        shutil.copyfile(FIXTURES / "review.md", evidence)
        patch_file = root / "corrections.yaml"
        patch_file.write_text(
            f"""
deprecated:
  - id: kcap-old
    reason: table no longer used
    superseded_by: kcap-new
updates:
  - id: kcap-new
    set:
      confidence: high
promote:
  - id: kcap-new
    to: approved
    reviewer: fixture
    approver: fixture
    evidence:
      - {evidence}
verify_absent_keywords:
  - old table
""",
            encoding="utf-8",
        )
        run(["scripts/patch_query_knowledge.py", "--root", str(root), "--patch-file", str(patch_file), "--dry-run"])
        run(["scripts/patch_query_knowledge.py", "--root", str(root), "--patch-file", str(patch_file)])
        assert list((root / "data-query-work" / "knowledge" / "deprecated").glob("*deprecated-kcap-old.md"))
        assert list((root / "data-query-work" / "knowledge" / "approved").glob("*approved-kcap-new.md"))


def test_scan_field_risk_flags() -> None:
    ok = run(["scripts/scan_sensitive_info.py", str(FIXTURES / "schema-index" / "unified_schema_index.json"), "--include-field-name-risks"])
    assert "sensitive_field_name_risks" in ok.stdout
    fail = subprocess.run(
        [PYTHON, "scripts/scan_sensitive_info.py", str(FIXTURES / "schema-index" / "unified_schema_index.json"), "--fail-on-sensitive-field-name"],
        cwd=REPO,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        env=SUBPROCESS_ENV,
    )
    assert fail.returncode == 1


def test_dependency_degrade_config_path() -> None:
    proc = subprocess.run(
        [
            PYTHON,
            "-S",
            "scripts/discover_data_sources.py",
            "--config",
            str(FIXTURES / "config" / "data-sources.yaml"),
            "--root",
            str(FIXTURES / "workspace"),
            "--json",
        ],
        cwd=REPO,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        env=SUBPROCESS_ENV,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["local_config"]["exists"] is True
    assert result["local_config"]["profile_parsing_skipped"] is True
    post = subprocess.run(
        [
            PYTHON,
            "-S",
            "scripts/post_install_check.py",
            "--config",
            str(FIXTURES / "config" / "data-sources.yaml"),
            "--root",
            str(REPO),
            "--offline-ok",
            "--json",
        ],
        cwd=REPO,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        env=SUBPROCESS_ENV,
    )
    assert post.returncode == 0, post.stderr
    post_result = json.loads(post.stdout)
    assert post_result["config"]["exists"] is True
    assert post_result["config"]["profile_parsing_skipped"] is True


def test_run_query_masked_export() -> None:
    with tempfile.TemporaryDirectory(prefix="dq runquery ") as tmp:
        root = Path(tmp)
        phone = "138" + "0013" + "8000"
        mock = root / "mock.json"
        mock.write_text(json.dumps([{"phone": phone, "safe": "ok"}]), encoding="utf-8")
        proc = run(
            [
                "scripts/run_query.py",
                "--engine",
                "clickhouse",
                "--profile",
                "default",
                "--mock-result-file",
                str(mock),
                "--sql",
                "SELECT phone, safe FROM dm.orders WHERE dt >= '2026-06-01' LIMIT 1",
                "--output-dir",
                str(root / "exports"),
            ]
        )
        result = json.loads(proc.stdout)
        output = Path(result["output_path"])
        assert result["masked_export"] is True
        assert phone not in output.read_text(encoding="utf-8-sig")


def main() -> int:
    tests = [
        test_table_list,
        test_masking,
        test_refresh_and_sample_dry_run,
        test_schema_index_discovery,
        test_static_check_warnings,
        test_knowledge_promotion_and_validate,
        test_patch_query_knowledge,
        test_scan_field_risk_flags,
        test_dependency_degrade_config_path,
        test_run_query_masked_export,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
