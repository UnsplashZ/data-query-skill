#!/usr/bin/env python3
"""Validate the skill manifest against current files."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

IGNORED_DIRS = {".git", ".github", "__pycache__", "data-query-work", "dist", "docs"}
IGNORED_NAMES = {".DS_Store", ".gitignore"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate manifest.json for this skill.")
    parser.add_argument(
        "root",
        nargs="?",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="Skill root directory. Defaults to the parent of scripts/.",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        print(f"FAIL: manifest not found: {manifest_path}")
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {entry["path"]: entry for entry in manifest.get("files", [])}
    actual_paths = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel_path = p.relative_to(root)
        rel = rel_path.as_posix()
        if rel == "manifest.json":
            continue
        if p.name in IGNORED_NAMES:
            continue
        if p.suffix in IGNORED_SUFFIXES:
            continue
        if any(part in IGNORED_DIRS for part in rel_path.parts):
            continue
        actual_paths.append(rel)
    actual_paths = sorted(actual_paths)
    actual = set(actual_paths)
    expected_paths = set(expected)

    ok = True
    for rel in sorted(expected_paths - actual):
        ok = False
        print(f"FAIL missing: {rel}")
    for rel in sorted(actual - expected_paths):
        ok = False
        print(f"FAIL untracked: {rel}")
    for rel in sorted(actual & expected_paths):
        path = root / rel
        entry = expected[rel]
        size = path.stat().st_size
        digest = sha256(path)
        if size != entry.get("bytes"):
            ok = False
            print(f"FAIL size: {rel}: manifest={entry.get('bytes')} actual={size}")
        if digest != entry.get("sha256"):
            ok = False
            print(f"FAIL sha256: {rel}")

    if manifest.get("file_count") != len(actual):
        ok = False
        print(f"FAIL file_count: manifest={manifest.get('file_count')} actual={len(actual)}")

    if ok:
        print(f"PASS: manifest valid ({len(actual)} files).")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
