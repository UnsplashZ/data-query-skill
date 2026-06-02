#!/usr/bin/env python3
"""Static checks for readonly SQL before execution."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

READONLY_START_RE = re.compile(r"^\s*(?:with\b|select\b|explain\s+select\b|explain\s+with\b)", re.IGNORECASE)
DANGEROUS_RE = re.compile(
    r"\b("
    r"insert|update|delete|merge|replace|upsert|drop|truncate|alter|create|rename|"
    r"grant|revoke|call|exec|execute|load|unload|outfile|attach|detach|optimize|"
    r"kill|set\s+password"
    r")\b",
    re.IGNORECASE,
)
DANGEROUS_FUNCTION_RE = re.compile(
    r"\b("
    r"load_file|benchmark|sleep|system|file|url|s3|mysql|postgresql"
    r")\s*\(",
    re.IGNORECASE,
)
DANGEROUS_CLAUSE_RE = re.compile(
    r"\binto\s+(?:out|dump)file\b|\bload\s+(?:data|xml)\b",
    re.IGNORECASE,
)
CLICKHOUSE_TABLE_FUNCTION_RE = re.compile(
    r"\b(?:from|join)\s+(?:file|url|s3|mysql|postgresql)\s*\(",
    re.IGNORECASE,
)
CLICKHOUSE_SYSTEM_TABLE_RE = re.compile(
    r"\b(?:from|join)\s+system(?:\.[A-Za-z_][A-Za-z0-9_]*)?\b",
    re.IGNORECASE,
)
CLICKHOUSE_QUOTED_TABLE_FUNCTION_RE = re.compile(
    r'''\b(?:from|join)\s+["`](file|url|s3|mysql|postgresql)["`]\s*\(''',
    re.IGNORECASE,
)
CLICKHOUSE_QUOTED_SYSTEM_TABLE_RE = re.compile(
    r'''\b(?:from|join)\s+["`]system["`]\s*\.''',
    re.IGNORECASE,
)
TIME_FIELD_RE = re.compile(
    r"\b("
    r"dt|ds|date|day|month|biz_date|stat_date|pay_time|paid_at|created_at|updated_at|"
    r"create_time|update_time|order_time|event_time|timestamp|time"
    r")\b",
    re.IGNORECASE,
)
TIME_FIELD_SUFFIX_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?:_date|_day|_month|_time|_at)\b", re.IGNORECASE)
TIME_RANGE_RE = re.compile(
    r"(?:\b(?:between|date_sub|date_add|toDate|to_date|date_format|interval|partition)\b|>=|<=|>|<)",
    re.IGNORECASE,
)
LIMIT_RE = re.compile(r"\blimit\s+\d+\b", re.IGNORECASE)
WHERE_RE = re.compile(r"\bwhere\b", re.IGNORECASE)
AGG_RE = re.compile(r"\b(count|sum|avg|min|max|uniq|distinct)\s*\(", re.IGNORECASE)


def strip_sql_noise(sql: str) -> str:
    """Remove comments and string literals while preserving statement shape."""
    out: list[str] = []
    i = 0
    in_single = False
    in_double = False
    in_line_comment = False
    in_block_comment = False
    while i < len(sql):
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < len(sql) else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
                out.append("\n")
            else:
                out.append(" ")
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                out.extend("  ")
                i += 2
            else:
                out.append("\n" if ch == "\n" else " ")
                i += 1
            continue
        if in_single:
            if ch == "\\" and nxt:
                out.extend("  ")
                i += 2
                continue
            if ch == "'":
                in_single = False
            out.append(" ")
            i += 1
            continue
        if in_double:
            if ch == "\\" and nxt:
                out.extend("  ")
                i += 2
                continue
            if ch == '"':
                in_double = False
            out.append(" ")
            i += 1
            continue
        if ch == "-" and nxt == "-":
            in_line_comment = True
            out.extend("  ")
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            out.extend("  ")
            i += 2
            continue
        if ch == "'":
            in_single = True
            out.append(" ")
            i += 1
            continue
        if ch == '"':
            in_double = True
            out.append(" ")
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def split_statements(clean_sql: str) -> list[str]:
    return [part.strip() for part in clean_sql.split(";") if part.strip()]


def normalize_identifiers(clean_sql: str) -> str:
    return re.sub(r'[`"]([A-Za-z_][A-Za-z0-9_]*)[`"]', r"\1", clean_sql)


def finding(level: str, code: str, message: str, hint: str) -> dict[str, str]:
    return {"level": level, "code": code, "message": message, "hint": hint}


def engine_warnings(engine: str, clean_sql: str) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    if engine == "clickhouse":
        if re.search(r"\bdate_format\s*\(", clean_sql, re.IGNORECASE):
            warnings.append(finding("warning", "dialect_clickhouse_date_format", "ClickHouse 通常使用 formatDateTime/toDate 系列函数。", "复核日期函数是否为 ClickHouse 方言。"))
        if re.search(r"\bnow\s*\(\s*\)\s*-\s*interval\b", clean_sql, re.IGNORECASE):
            warnings.append(finding("warning", "dialect_clickhouse_interval", "ClickHouse interval 写法可能需要 INTERVAL n DAY。", "执行前用 sample SQL 验证方言。"))
    elif engine == "odps":
        if re.search(r"\btoDate\s*\(|\bformatDateTime\s*\(", clean_sql):
            warnings.append(finding("warning", "dialect_odps_clickhouse_func", "SQL 中疑似出现 ClickHouse 日期函数。", "ODPS/MaxCompute 需改用 to_date/dateadd 等团队约定方言。"))
        if re.search(r"\blimit\s+\d+\s*,\s*\d+", clean_sql, re.IGNORECASE):
            warnings.append(finding("warning", "dialect_odps_limit_offset", "ODPS 对 LIMIT offset 写法支持可能受版本影响。", "优先使用单个 LIMIT 做采样。"))
    elif engine == "mysql":
        if re.search(r"\btoDate\s*\(|\bformatDateTime\s*\(", clean_sql):
            warnings.append(finding("warning", "dialect_mysql_clickhouse_func", "SQL 中疑似出现 ClickHouse 函数。", "MySQL 需改用 DATE/DATE_FORMAT 等函数。"))
    elif engine == "metabase":
        if "{{" in clean_sql or "}}" in clean_sql:
            warnings.append(finding("warning", "metabase_template_tags", "Metabase 模板变量需要在 card/database 参数中显式传参。", "确认 --parameters 与模板变量一致。"))
    return warnings


def check_sql(sql: str, engine: str = "clickhouse") -> dict[str, Any]:
    clean = strip_sql_noise(sql)
    normalized = normalize_identifiers(clean)
    quoted_identifier_normalized = normalize_identifiers(re.sub(r"--.*?$|/\*.*?\*/", " ", sql, flags=re.M | re.S))
    statements = split_statements(clean)
    findings: list[dict[str, str]] = []

    if not statements:
        findings.append(finding("error", "empty_sql", "SQL 为空。", "提供 --sql、--sql-file 或 stdin。"))
    elif len(statements) > 1:
        findings.append(finding("error", "multi_statement", "禁止多语句执行。", "拆成单条只读 SELECT 后分别执行。"))

    first = statements[0] if statements else clean
    if first and not READONLY_START_RE.search(first):
        findings.append(finding("error", "not_readonly_select", "SQL 必须以 SELECT/WITH/EXPLAIN SELECT 开始。", "只允许只读查询，不允许维护语句或过程调用。"))

    dangerous = sorted({m.group(1).lower() for m in DANGEROUS_RE.finditer(normalized)})
    if dangerous:
        findings.append(finding("error", "dangerous_keyword", f"检测到危险关键字: {', '.join(dangerous)}。", "禁止 DDL/DML/权限/导出/执行类语句。"))

    dangerous_functions = sorted({m.group(1).lower() for m in DANGEROUS_FUNCTION_RE.finditer(normalized)})
    if dangerous_functions:
        findings.append(
            finding(
                "error",
                "dangerous_function",
                f"检测到危险函数: {', '.join(dangerous_functions)}。",
                "禁止文件、外部 URL、跨库拉取、延时和压测类函数。",
            )
        )

    if DANGEROUS_CLAUSE_RE.search(normalized):
        findings.append(
            finding(
                "error",
                "dangerous_clause",
                "检测到危险导入/导出子句。",
                "禁止 LOAD DATA/XML、INTO OUTFILE 和 INTO DUMPFILE。",
            )
        )

    if engine == "clickhouse" and (
        CLICKHOUSE_TABLE_FUNCTION_RE.search(normalized)
        or CLICKHOUSE_TABLE_FUNCTION_RE.search(quoted_identifier_normalized)
        or CLICKHOUSE_QUOTED_TABLE_FUNCTION_RE.search(sql)
    ):
        findings.append(
            finding(
                "error",
                "dangerous_clickhouse_table_function",
                "检测到 ClickHouse 外部 table function。",
                "禁止通过 file/url/s3/mysql/postgresql table function 读取本地、外部或跨库数据。",
            )
        )

    if engine == "clickhouse" and (
        CLICKHOUSE_SYSTEM_TABLE_RE.search(normalized)
        or CLICKHOUSE_SYSTEM_TABLE_RE.search(quoted_identifier_normalized)
        or CLICKHOUSE_QUOTED_SYSTEM_TABLE_RE.search(sql)
    ):
        findings.append(
            finding(
                "error",
                "dangerous_clickhouse_system_table",
                "检测到 ClickHouse system 表访问。",
                "只允许业务只读 SELECT，不允许查询系统表暴露运行时或环境信息。",
            )
        )

    has_time_field = bool(TIME_FIELD_RE.search(first) or TIME_FIELD_SUFFIX_RE.search(first))
    if first and not (has_time_field and TIME_RANGE_RE.search(first)):
        findings.append(finding("warning", "missing_time_range", "未检测到明确时间字段与时间范围。", "补充时间字段、起止范围和业务日期口径；无法补充时在结果中标记风险。"))

    if first and not LIMIT_RE.search(first):
        findings.append(finding("warning", "missing_limit", "未检测到 LIMIT。", "首次执行应先用 LIMIT 或小日期范围采样，再扩大范围。"))

    if first and not WHERE_RE.search(first):
        findings.append(finding("warning", "missing_scope", "未检测到 WHERE/scope 过滤。", "补充业务 scope，例如状态、渠道、SKU、人群或分区过滤。"))

    if first and re.search(r"\bjoin\b", first, re.IGNORECASE) and not AGG_RE.search(first):
        findings.append(finding("warning", "join_cardinality_risk", "JOIN 查询未检测到聚合或去重校验。", "先做 join cardinality sample，避免一对多膨胀。"))

    findings.extend(engine_warnings(engine, normalized))
    error_count = sum(1 for item in findings if item["level"] == "error")
    warning_count = sum(1 for item in findings if item["level"] == "warning")
    return {
        "ok": error_count == 0,
        "engine": engine,
        "error_count": error_count,
        "warning_count": warning_count,
        "findings": findings,
    }


def read_sql_arg(sql: str | None, sql_file: Path | None) -> str:
    if sql:
        return sql
    if sql_file:
        return sql_file.read_text(encoding="utf-8")
    data = sys.stdin.read()
    if data.strip():
        return data
    raise RuntimeError("Provide --sql, --sql-file, or SQL on stdin.")


def print_text(result: dict[str, Any]) -> None:
    status = "PASS" if result["ok"] else "FAIL"
    print(f"{status}: engine={result['engine']} errors={result['error_count']} warnings={result['warning_count']}")
    for item in result["findings"]:
        print(f"- [{item['level']}] {item['code']}: {item['message']} {item['hint']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check SQL readonly safety and query reliability risks.")
    parser.add_argument("--engine", default="clickhouse", choices=["clickhouse", "odps", "mysql", "metabase"])
    parser.add_argument("--sql")
    parser.add_argument("--sql-file", type=Path)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--json", action="store_true", help="Alias for --format json.")
    args = parser.parse_args()

    sql = read_sql_arg(args.sql, args.sql_file)
    result = check_sql(sql, args.engine)
    if args.json or args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_text(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
