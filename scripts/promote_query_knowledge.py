#!/usr/bin/env python3
"""Promote a query knowledge item and append the promotion log."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


KNOWLEDGE_DIR = "data-query-knowledge"
VALID_TARGETS = {"reviewed", "approved", "deprecated"}
SKIP_NAMES = {"manifest.yaml", "OWNERS.yaml", "promotion-log.md", "README.md", ".gitkeep"}


def knowledge_root_for(root: Path) -> Path:
    if (root / "manifest.yaml").exists() and (root / "OWNERS.yaml").exists():
        return root
    return root / KNOWLEDGE_DIR


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v not in (None, "")]
    return [str(value)] if str(value) else []


def load_markdown(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    loaded = yaml.safe_load(text[4:end]) or {}
    body = text[end + 4 :]
    return (loaded if isinstance(loaded, dict) else {}), body


def dump_markdown(path: Path, data: dict[str, Any], body: str) -> None:
    clean = {k: v for k, v in data.items() if not k.startswith("_")}
    frontmatter = yaml.safe_dump(clean, allow_unicode=True, sort_keys=False).strip()
    path.write_text(f"---\n{frontmatter}\n---{body}", encoding="utf-8")


def load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8", errors="ignore")) or {}
    return loaded if isinstance(loaded, dict) else {}


def dump_yaml(path: Path, data: dict[str, Any]) -> None:
    clean = {k: v for k, v in data.items() if not k.startswith("_")}
    path.write_text(yaml.safe_dump(clean, allow_unicode=True, sort_keys=False), encoding="utf-8")


def find_item(root: Path, item_or_path: str) -> tuple[Path, dict[str, Any], str | None]:
    candidate_path = root / item_or_path
    if candidate_path.exists() and candidate_path.is_file():
        paths = [candidate_path]
    else:
        paths = [p for p in sorted(knowledge_root_for(root).rglob("*")) if p.is_file() and p.name not in SKIP_NAMES]
    for path in paths:
        if path.suffix.lower() == ".md":
            data, body = load_markdown(path)
        elif path.suffix.lower() in {".yaml", ".yml"}:
            data, body = load_yaml(path), None
        else:
            continue
        if path == candidate_path or str(data.get("id")) == item_or_path:
            data["_path"] = path
            return path, data, body
    raise SystemExit(f"FAIL: knowledge item not found: {item_or_path}")


def append_unique(values: list[str], additions: list[str]) -> list[str]:
    out = list(values)
    for value in additions:
        if value and value not in out:
            out.append(value)
    return out


def append_log(root: Path, item_id: str, old_status: str, new_status: str, actor: str, reviewer: str, evidence: str, notes: str) -> None:
    log_path = knowledge_root_for(root) / "promotion-log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if not log_path.exists():
        log_path.write_text(
            "# Query Knowledge Promotion Log\n\n"
            "| timestamp | id | from_status | to_status | actor | reviewer | evidence | notes |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- |\n",
            encoding="utf-8",
        )
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    row = f"| {timestamp} | {item_id} | {old_status} | {new_status} | {actor} | {reviewer} | {evidence} | {notes} |\n"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote one data-query-knowledge item.")
    parser.add_argument("item", help="Knowledge id or file path.")
    parser.add_argument("--to", required=True, choices=sorted(VALID_TARGETS), help="Target status.")
    parser.add_argument("--actor", required=True, help="Person or agent requesting the promotion.")
    parser.add_argument("--reviewer", action="append", default=[], help="Reviewer identity. Can repeat.")
    parser.add_argument("--approver", action="append", default=[], help="Approver identity. Can repeat.")
    parser.add_argument("--evidence", action="append", default=[], help="Review or validation evidence. Can repeat.")
    parser.add_argument("--notes", default="", help="Promotion notes.")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing files.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Skill root directory.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    path, data, body = find_item(root, args.item)
    old_status = str(data.get("status", ""))
    item_id = str(data.get("id", ""))

    evidence = append_unique(as_list(data.get("validation_evidence")), args.evidence)
    reviewers = append_unique(as_list(data.get("reviewed_by")), args.reviewer)
    approvers = append_unique(as_list(data.get("approved_by")), args.approver)

    if args.to in {"reviewed", "approved"} and not reviewers:
        print("FAIL: reviewed/approved promotion requires --reviewer or existing reviewed_by.")
        return 1
    if args.to == "approved" and not approvers:
        print("FAIL: approved promotion requires --approver or existing approved_by.")
        return 1
    if args.to in {"reviewed", "approved"} and not evidence:
        print("FAIL: reviewed/approved promotion requires review evidence.")
        return 1
    if args.to == "approved" and old_status not in {"candidate", "reviewed", "approved"}:
        print(f"FAIL: approved promotion is only allowed from candidate/reviewed/approved, got {old_status}.")
        return 1

    data["status"] = args.to
    data["reviewed_by"] = reviewers
    data["approved_by"] = approvers
    data["validation_evidence"] = evidence
    if args.to == "approved" and not data.get("last_verified_at"):
        data["last_verified_at"] = datetime.now(timezone.utc).date().isoformat()

    rel = path.relative_to(root).as_posix()
    print(f"{'DRY-RUN ' if args.dry_run else ''}PROMOTE: {item_id} {old_status} -> {args.to} ({rel})")
    if args.dry_run:
        return 0

    if path.suffix.lower() == ".md":
        dump_markdown(path, data, body or "")
    else:
        dump_yaml(path, data)
    append_log(root, item_id, old_status, args.to, args.actor, ",".join(reviewers), "; ".join(args.evidence), args.notes)
    print("PASS: promotion applied and promotion-log updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
