#!/usr/bin/env python3
"""Shared helpers for repo-native query knowledge lifecycle scripts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from lib_workspace import resolve_knowledge_root, warn_if_needed, writable_knowledge_root


VALID_TARGETS = {"reviewed", "approved", "deprecated"}
SKIP_NAMES = {"OWNERS.yaml", "promotion-log.md", "README.md", ".gitkeep"}
STATUS_DIRS = {
    "candidate": "candidates",
    "reviewed": "reviewed",
    "approved": "approved",
    "deprecated": "deprecated",
}
STATUS_SUFFIX_RE = re.compile(r"__(candidate|reviewed|approved|deprecated)(?:-[A-Za-z0-9_.-]+)?$")
SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class LoadedKnowledgeItem:
    path: Path
    data: dict[str, Any]
    body: str | None


@dataclass(frozen=True)
class PromotionPlan:
    item_id: str
    old_status: str
    new_status: str
    source_path: Path
    target_path: Path
    data: dict[str, Any]
    body: str | None


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v not in (None, "")]
    return [str(value)] if str(value) else []


def append_unique(values: list[str], additions: list[str]) -> list[str]:
    out = list(values)
    for value in additions:
        if value and value not in out:
            out.append(value)
    return out


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
    atomic_write_text(path, f"---\n{frontmatter}\n---{body}")


def load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8", errors="ignore")) or {}
    return loaded if isinstance(loaded, dict) else {}


def dump_yaml(path: Path, data: dict[str, Any]) -> None:
    clean = {k: v for k, v in data.items() if not k.startswith("_")}
    atomic_write_text(path, yaml.safe_dump(clean, allow_unicode=True, sort_keys=False))


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def load_item_file(path: Path) -> LoadedKnowledgeItem | None:
    if path.name in SKIP_NAMES:
        return None
    if path.suffix.lower() == ".md":
        data, body = load_markdown(path)
    elif path.suffix.lower() in {".yaml", ".yml"}:
        data, body = load_yaml(path), None
    else:
        return None
    if not data:
        return None
    data["_path"] = path
    return LoadedKnowledgeItem(path=path, data=data, body=body)


def iter_items(root: Path) -> list[LoadedKnowledgeItem]:
    selection = resolve_knowledge_root(root, mode="read")
    warn_if_needed(selection)
    knowledge_root = selection.path
    if not knowledge_root.exists():
        return []
    items: list[LoadedKnowledgeItem] = []
    for path in sorted(knowledge_root.rglob("*")):
        if not path.is_file():
            continue
        item = load_item_file(path)
        if item:
            items.append(item)
    return items


def find_item(root: Path, item_or_path: str) -> LoadedKnowledgeItem:
    raw_path = Path(item_or_path).expanduser()
    candidate_path = raw_path if raw_path.is_absolute() else root / raw_path
    if candidate_path.exists() and candidate_path.is_file():
        item = load_item_file(candidate_path)
        if item:
            return item
        raise SystemExit(f"FAIL: unsupported or empty knowledge item: {candidate_path}")

    for item in iter_items(root):
        if str(item.data.get("id")) == item_or_path:
            return item
    raise SystemExit(f"FAIL: knowledge item not found: {item_or_path}")


def safe_filename_component(value: str) -> str:
    cleaned = SAFE_FILENAME_RE.sub("-", value).strip("-._")
    return cleaned or "item"


def filename_for_status(path: Path, target_status: str, item_id: str) -> str:
    safe_id = safe_filename_component(item_id)
    status_suffix = f"__{target_status}-{safe_id}"
    stem = path.stem
    if STATUS_SUFFIX_RE.search(stem):
        stem = STATUS_SUFFIX_RE.sub(status_suffix, stem)
    else:
        stem = f"{stem}{status_suffix}"
    return f"{stem}{path.suffix}"


def target_path_for(root: Path, source_path: Path, target_status: str, item_id: str) -> Path:
    selection = resolve_knowledge_root(root, mode="read")
    warn_if_needed(selection)
    directory_name = STATUS_DIRS[target_status]
    target_dir = selection.path / directory_name
    filename = filename_for_status(source_path, target_status, item_id)
    return target_dir / filename


def validate_promotion_requirements(
    target_status: str,
    old_status: str,
    reviewers: list[str],
    approvers: list[str],
    evidence: list[str],
) -> list[str]:
    errors: list[str] = []
    if target_status not in VALID_TARGETS:
        errors.append(f"unsupported target status: {target_status}")
    if target_status in {"reviewed", "approved"} and not reviewers:
        errors.append("reviewed/approved promotion requires reviewer.")
    if target_status == "approved" and not approvers:
        errors.append("approved promotion requires approver.")
    if target_status in {"reviewed", "approved"} and not evidence:
        errors.append("reviewed/approved promotion requires review evidence.")
    if target_status == "approved" and old_status not in {"candidate", "reviewed", "approved"}:
        errors.append(f"approved promotion is only allowed from candidate/reviewed/approved, got {old_status}.")
    return errors


def build_promotion_plan(
    root: Path,
    item_or_path: str,
    target_status: str,
    *,
    reviewers: list[str] | None = None,
    approvers: list[str] | None = None,
    evidence: list[str] | None = None,
) -> PromotionPlan:
    item = find_item(root, item_or_path)
    data = dict(item.data)
    old_status = str(data.get("status", "")).lower()
    item_id = str(data.get("id", "")).strip()
    if not item_id:
        raise SystemExit(f"FAIL: knowledge item has no stable id: {item.path}")

    merged_reviewers = append_unique(as_list(data.get("reviewed_by")), reviewers or [])
    merged_approvers = append_unique(as_list(data.get("approved_by")), approvers or [])
    merged_evidence = append_unique(as_list(data.get("validation_evidence")), evidence or [])
    errors = validate_promotion_requirements(target_status, old_status, merged_reviewers, merged_approvers, merged_evidence)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        raise SystemExit(1)

    data["status"] = target_status
    data["reviewed_by"] = merged_reviewers
    data["approved_by"] = merged_approvers
    data["validation_evidence"] = merged_evidence
    if target_status == "approved" and not data.get("last_verified_at"):
        data["last_verified_at"] = datetime.now(timezone.utc).date().isoformat()

    target_path = target_path_for(root, item.path, target_status, item_id)
    return PromotionPlan(
        item_id=item_id,
        old_status=old_status,
        new_status=target_status,
        source_path=item.path,
        target_path=target_path,
        data=data,
        body=item.body,
    )


def apply_promotion_plan(plan: PromotionPlan) -> None:
    plan.target_path.parent.mkdir(parents=True, exist_ok=True)
    source_resolved = plan.source_path.resolve()
    target_resolved = plan.target_path.resolve()
    same_path = source_resolved == target_resolved
    if plan.target_path.exists() and not same_path:
        raise SystemExit(f"FAIL: target already exists: {plan.target_path}")

    if plan.target_path.suffix.lower() == ".md":
        dump_markdown(plan.target_path, plan.data, plan.body or "")
    else:
        dump_yaml(plan.target_path, plan.data)
    if not same_path:
        plan.source_path.unlink()


def append_log(root: Path, item_id: str, old_status: str, new_status: str, actor: str, reviewer: str, evidence: str, notes: str) -> None:
    selection = writable_knowledge_root(root)
    warn_if_needed(selection)
    log_path = selection.path / "promotion-log.md"
    if not log_path.exists():
        atomic_write_text(
            log_path,
            "# Query Knowledge Promotion Log\n\n"
            "| timestamp | id | from_status | to_status | actor | reviewer | evidence | notes |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- |\n",
        )
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    row = f"| {timestamp} | {item_id} | {old_status} | {new_status} | {actor} | {reviewer} | {evidence} | {notes} |\n"
    existing = log_path.read_text(encoding="utf-8", errors="ignore") if log_path.exists() else ""
    atomic_write_text(log_path, existing + row)
