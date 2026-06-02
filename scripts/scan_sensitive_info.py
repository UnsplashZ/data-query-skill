#!/usr/bin/env python3
"""Scan files for high-confidence credential and sensitive-value leaks."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("jdbc-url-with-password", re.compile(r"jdbc:[^\s]+(?:password|passwd|pwd)=[^\s&]+", re.I)),
    ("url-with-basic-auth", re.compile(r"[a-z]+://[^\s:/]+:[^\s@/]{6,}@[^\s]+", re.I)),
    ("access-key-secret", re.compile(r"(?i)access[_-]?key[_-]?secret\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{16,}")),
    ("api-token-assignment", re.compile(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{24,}")),
    ("feishu-token-assignment", re.compile(r"(?i)(spreadsheet[_-]?token|resolved spreadsheet token|wiki[_-]?token|app[_-]?token|base[_-]?token)\s*[:：=]\s*`?[A-Za-z0-9_-]{8,}`?")),
    ("feishu-url", re.compile(r"https?://[A-Za-z0-9.-]*feishu\.cn/(?:wiki|docx|base|sheets?)/[A-Za-z0-9_-]+", re.I)),
    ("phone-number", re.compile(r"(?<![A-Za-z0-9])1[3-9]\d{9}(?![A-Za-z0-9])")),
]

TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".sql",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".sh",
    ".csv",
    ".tsv",
}
TEXT_FILENAMES = {
    ".env",
    ".env.example",
}
DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXCLUDED_PREFIXES: set[tuple[str, ...]] = set()


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
    args = parser.parse_args()

    root = args.path.resolve()
    files = [root] if root.is_file() else list(iter_files(root))
    findings: list[str] = []

    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for name, pattern in PATTERNS:
                if pattern.search(line):
                    rel = path.relative_to(root) if root.is_dir() else path.name
                    findings.append(f"{rel}:{lineno}: {name}")
                    if len(findings) >= args.max_findings:
                        break
            if len(findings) >= args.max_findings:
                break
        if len(findings) >= args.max_findings:
            break

    if findings:
        print("FINDINGS:")
        for item in findings:
            print(f"- {item}")
        return 1

    print(f"PASS: no high-confidence sensitive findings in {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
