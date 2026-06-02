#!/usr/bin/env python3
"""Build a release zip for the internal data query skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE_DIR = "internal-data-query"

INCLUDE_FILES = (
    "SKILL.md",
    "README.md",
    "CHANGELOG.md",
    "requirements.txt",
    "version.txt",
)

INCLUDE_DIRS = (
    "scripts",
    "references",
    "templates",
)

EXCLUDE_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
}

EXCLUDE_SUFFIXES = {
    ".pyc",
    ".pyo",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def add_to_zip(zipf: zipfile.ZipFile, source: Path, arcname: Path) -> None:
    info = zipfile.ZipInfo.from_file(source, arcname.as_posix())
    info.compress_type = zipfile.ZIP_DEFLATED
    with source.open("rb") as f:
        zipf.writestr(info, f.read())


def iter_package_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for rel in INCLUDE_FILES:
        path = root / rel
        if path.is_file():
            files.append(path)
    for dirname in INCLUDE_DIRS:
        base = root / dirname
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            rel_parts = path.relative_to(root).parts
            if any(part in EXCLUDE_DIR_NAMES for part in rel_parts):
                continue
            if path.suffix in EXCLUDE_SUFFIXES:
                continue
            files.append(path)
    return sorted(set(files), key=lambda p: p.relative_to(root).as_posix())


def main() -> int:
    parser = argparse.ArgumentParser(description="Package the skill as a GitHub Release zip.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Skill repo root.")
    parser.add_argument("--dist-dir", type=Path, default=None, help="Output directory. Defaults to <root>/dist.")
    parser.add_argument("--package-dir", default=DEFAULT_PACKAGE_DIR, help="Top-level directory inside the zip.")
    parser.add_argument("--zip-name", default="internal-data-query-skill.zip")
    parser.add_argument("--keep-staging", action="store_true", help="Keep the staged package directory in dist/.")
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable summary.")
    args = parser.parse_args()

    root = args.root.resolve()
    package_dir = args.package_dir
    dist_dir = (args.dist_dir or root / "dist").resolve()
    staging_root = dist_dir / package_dir
    zip_path = dist_dir / args.zip_name
    sha_path = zip_path.with_suffix(zip_path.suffix + ".sha256")

    if staging_root.exists():
        shutil.rmtree(staging_root)
    dist_dir.mkdir(parents=True, exist_ok=True)

    files = iter_package_files(root)
    if not files:
        print("FAIL: no package files found", file=sys.stderr)
        return 1
    for src in files:
        copy_file(src, staging_root / src.relative_to(root))

    if zip_path.exists():
        zip_path.unlink()
    if sha_path.exists():
        sha_path.unlink()

    with zipfile.ZipFile(zip_path, "w") as zipf:
        for path in sorted(staging_root.rglob("*")):
            if path.is_file():
                add_to_zip(zipf, path, path.relative_to(dist_dir))

    digest = sha256(zip_path)
    sha_path.write_text(f"{digest}  {zip_path.name}\n", encoding="utf-8")

    summary = {
        "package_dir": package_dir,
        "file_count": len(files),
        "zip": zip_path.as_posix(),
        "sha256_file": sha_path.as_posix(),
        "sha256": digest,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"PASS: packaged {len(files)} files into {zip_path}")
        print(f"SHA256: {digest}")

    if not args.keep_staging:
        shutil.rmtree(staging_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
