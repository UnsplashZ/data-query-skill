#!/usr/bin/env python3
"""Scan files for high-confidence credential leaks and sensitive field-name risks."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from lib_masking import Finding, FIELD_NAME_PATTERNS, residual_scan_text


TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".sql",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".csv",
    ".tsv",
}
TEXT_FILENAMES = {
    ".env",
    ".env.example",
}
DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXCLUDED_PREFIXES: set[tuple[str, ...]] = {("dist",)}

FIELD_DECL_RE = re.compile(r"(?i)\b([A-Za-z_][A-Za-z0-9_]*(?:password|passwd|pwd|secret|token|api_key|access_key|session|cookie|phone|mobile|email|id_card|openid|unionid|address)[A-Za-z0-9_]*)\b")


def is_default_excluded(path: Path, root: Path) -> bool:
    if root != DEFAULT_ROOT:
        return False
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        return False
    return any(rel_parts[: len(prefix)] == prefix for prefix in DEFAULT_EXCLUDED_PREFIXES)


def iter_files(root: Path):
    for path in root.rglob("*"):
        if is_default_excluded(path, root):
            continue
        if path.is_file() and (path.suffix.lower() in TEXT_SUFFIXES or path.name.lower() in TEXT_FILENAMES):
            yield path


def rel_for(path: Path, root: Path) -> str:
    if root.is_dir():
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            return str(path)
    return path.name


def field_name_risks(text: str, path: Path, root: Path) -> list[Finding]:
    risks: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in FIELD_DECL_RE.finditer(line):
            field = match.group(1)
            for kind, pattern in FIELD_NAME_PATTERNS:
                if pattern.search(field):
                    risks.append(
                        Finding(
                            level="warning",
                            code="sensitive_field_name",
                            category="sensitive_field_name_risk",
                            matched_kind=kind,
                            path=rel_for(path, root),
                            line=lineno,
                            field=field,
                            hint="Field name suggests sensitive data; verify it is metadata only and mask values before export.",
                        )
                    )
                    break
    return risks


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan a path for likely leaked secrets.")
    parser.add_argument(
        "path",
        nargs="?",
        default=DEFAULT_ROOT,
        type=Path,
        help="File or directory to scan. Defaults to the skill root.",
    )
    parser.add_argument("--max-findings", type=int, default=100)
    parser.add_argument("--include-field-name-risks", action="store_true", help="Report schema/DDL sensitive field-name risks as warnings.")
    parser.add_argument("--fail-on-sensitive-field-name", action="store_true", help="Return non-zero when field-name risks are found.")
    args = parser.parse_args()

    root = args.path.resolve()
    files = [root] if root.is_file() else list(iter_files(root))
    secret_leaks: list[Finding] = []
    field_risks: list[Finding] = []

    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for finding in residual_scan_text(text):
            secret_leaks.append(
                Finding(
                    level=finding.level,
                    code=finding.code,
                    category=finding.category,
                    matched_kind=finding.matched_kind,
                    path=rel_for(path, root),
                    line=finding.line,
                    field=finding.field,
                    sample=finding.sample,
                    hint=finding.hint,
                )
            )
        if args.include_field_name_risks or args.fail_on_sensitive_field_name:
            field_risks.extend(field_name_risks(text, path, root))
        if len(secret_leaks) + len(field_risks) >= args.max_findings:
            break

    if secret_leaks:
        print("secret_leak_findings:")
        for item in secret_leaks[: args.max_findings]:
            print(f"- {item.path}:{item.line}: {item.matched_kind}: {item.hint}")
    else:
        print("secret_leak_findings: none")

    if args.include_field_name_risks or args.fail_on_sensitive_field_name:
        if field_risks:
            print("sensitive_field_name_risks:")
            for item in field_risks[: args.max_findings]:
                print(f"- {item.path}:{item.line}: {item.field} ({item.matched_kind}): {item.hint}")
        else:
            print("sensitive_field_name_risks: none")

    if secret_leaks:
        return 1
    if field_risks and args.fail_on_sensitive_field_name:
        return 1
    print(f"PASS: no high-confidence sensitive findings in {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
