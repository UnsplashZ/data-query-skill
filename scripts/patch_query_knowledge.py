#!/usr/bin/env python3
"""Batch patch, deprecate, promote, and verify query knowledge files."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from lib_query_knowledge import (
    append_log,
    append_unique,
    apply_promotion_plan,
    as_list,
    build_promotion_plan,
    dump_markdown,
    dump_yaml,
    find_item,
    iter_items,
)


ACTIVE_STATUSES = {"draft", "candidate", "reviewed", "approved"}


def load_patch(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8", errors="ignore")) or {}
    if not isinstance(loaded, dict):
        raise SystemExit("FAIL: patch file must be a YAML mapping.")
    return loaded


def item_id_from(entry: dict[str, Any], section: str) -> str:
    item_id = str(entry.get("id", "")).strip()
    if not item_id:
        raise SystemExit(f"FAIL: {section} entry missing id.")
    return item_id


def entries(value: Any, section: str) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise SystemExit(f"FAIL: {section} must be a list.")
    out: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise SystemExit(f"FAIL: {section} entries must be mappings.")
        out.append(item)
    return out


def write_item(path: Path, data: dict[str, Any], body: str | None) -> None:
    if path.suffix.lower() == ".md":
        dump_markdown(path, data, body or "")
    else:
        dump_yaml(path, data)


def apply_updates(root: Path, updates: list[dict[str, Any]], *, dry_run: bool) -> None:
    for entry in updates:
        item_id = item_id_from(entry, "updates")
        set_values = entry.get("set") or {}
        if not isinstance(set_values, dict):
            raise SystemExit(f"FAIL: updates entry for {item_id} has non-mapping set.")
        item = find_item(root, item_id)
        rel = item.path.relative_to(root).as_posix() if item.path.is_relative_to(root) else str(item.path)
        fields = ", ".join(sorted(str(key) for key in set_values)) or "(none)"
        print(f"{'DRY-RUN ' if dry_run else ''}UPDATE: {item_id} {rel} set={fields}")
        if dry_run:
            continue
        data = dict(item.data)
        data.update(set_values)
        write_item(item.path, data, item.body)


def deprecated_notes(entry: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    reason = str(entry.get("reason", "")).strip()
    superseded_by = str(entry.get("superseded_by", "")).strip()
    if reason:
        notes.append(f"Deprecated: {reason}")
    if superseded_by:
        notes.append(f"Superseded by: {superseded_by}")
    return notes


def apply_deprecated(root: Path, deprecated: list[dict[str, Any]], *, actor: str, dry_run: bool) -> set[str]:
    planned_ids: set[str] = set()
    for entry in deprecated:
        item_id = item_id_from(entry, "deprecated")
        reason = str(entry.get("reason", "")).strip()
        superseded_by = str(entry.get("superseded_by", "")).strip()
        plan = build_promotion_plan(root, item_id, "deprecated")
        planned_ids.add(plan.item_id)
        source_rel = plan.source_path.relative_to(root).as_posix() if plan.source_path.is_relative_to(root) else str(plan.source_path)
        target_rel = plan.target_path.relative_to(root).as_posix() if plan.target_path.is_relative_to(root) else str(plan.target_path)
        print(f"{'DRY-RUN ' if dry_run else ''}DEPRECATED: {plan.item_id} {source_rel} -> {target_rel}")
        if dry_run:
            continue
        if reason:
            plan.data["deprecated_reason"] = reason
        if superseded_by:
            plan.data["superseded_by"] = superseded_by
        plan.data["sync_notes"] = append_unique(as_list(plan.data.get("sync_notes")), deprecated_notes(entry))
        apply_promotion_plan(plan)
        append_log(root, plan.item_id, plan.old_status, plan.new_status, actor, "", "", reason)
    return planned_ids


def promote_reviewers(entry: dict[str, Any]) -> list[str]:
    return as_list(entry.get("reviewer")) + as_list(entry.get("reviewers"))


def promote_approvers(entry: dict[str, Any]) -> list[str]:
    return as_list(entry.get("approver")) + as_list(entry.get("approvers"))


def apply_promotions(root: Path, promotions: list[dict[str, Any]], *, actor: str, dry_run: bool) -> None:
    for entry in promotions:
        item_id = item_id_from(entry, "promote")
        target = str(entry.get("to", "")).strip().lower()
        if not target:
            raise SystemExit(f"FAIL: promote entry for {item_id} missing to.")
        reviewers = promote_reviewers(entry)
        approvers = promote_approvers(entry)
        evidence = as_list(entry.get("evidence"))
        notes = str(entry.get("notes", "") or "")
        plan = build_promotion_plan(root, item_id, target, reviewers=reviewers, approvers=approvers, evidence=evidence)
        source_rel = plan.source_path.relative_to(root).as_posix() if plan.source_path.is_relative_to(root) else str(plan.source_path)
        target_rel = plan.target_path.relative_to(root).as_posix() if plan.target_path.is_relative_to(root) else str(plan.target_path)
        print(f"{'DRY-RUN ' if dry_run else ''}PROMOTE: {plan.item_id} {plan.old_status} -> {plan.new_status}")
        print(f"{'DRY-RUN ' if dry_run else ''}MOVE: {source_rel} -> {target_rel}")
        if dry_run:
            continue
        apply_promotion_plan(plan)
        append_log(
            root,
            plan.item_id,
            plan.old_status,
            plan.new_status,
            actor,
            ",".join(as_list(plan.data.get("reviewed_by"))),
            "; ".join(as_list(plan.data.get("validation_evidence"))),
            notes,
        )


def verify_absent_keywords(root: Path, keywords: list[str], *, exclude_ids: set[str] | None = None) -> bool:
    exclude_ids = exclude_ids or set()
    ok = True
    lowered_keywords = [keyword.lower() for keyword in keywords if keyword]
    for keyword, lowered in zip(keywords, lowered_keywords):
        hits: list[str] = []
        for item in iter_items(root):
            item_id = str(item.data.get("id", ""))
            status = str(item.data.get("status", "")).lower()
            if item_id in exclude_ids or status not in ACTIVE_STATUSES:
                continue
            haystack = yaml.safe_dump({k: v for k, v in item.data.items() if not k.startswith("_")}, allow_unicode=True)
            if item.body:
                haystack += item.body
            if lowered in haystack.lower():
                rel = item.path.relative_to(root).as_posix() if item.path.is_relative_to(root) else str(item.path)
                hits.append(f"{item_id}:{rel}")
        if hits:
            ok = False
            print(f"FAIL VERIFY_ABSENT: {keyword} still appears in active knowledge: {', '.join(hits)}")
        else:
            print(f"PASS VERIFY_ABSENT: {keyword}")
    return ok


def run_validate(root: Path) -> int:
    script = Path(__file__).resolve().parent / "validate_query_knowledge.py"
    sys.stdout.flush()
    return subprocess.run([sys.executable, str(script), "--root", str(root)], check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch patch data-query-work/knowledge lifecycle files.")
    parser.add_argument("--patch-file", required=True, type=Path, help="YAML corrections file.")
    parser.add_argument("--actor", default="patch_query_knowledge", help="Actor name for promotion-log rows.")
    parser.add_argument("--dry-run", action="store_true", help="Report planned changes without writing files.")
    parser.add_argument("--validate", action="store_true", help="Run validation even during dry-run.")
    parser.add_argument("--no-validate", action="store_true", help="Skip automatic validation after applying changes.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Skill root directory.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    patch = load_patch(args.patch_file)
    apply_updates(root, entries(patch.get("updates"), "updates"), dry_run=args.dry_run)
    planned_deprecated_ids = apply_deprecated(
        root,
        entries(patch.get("deprecated"), "deprecated"),
        actor=args.actor,
        dry_run=args.dry_run,
    )
    apply_promotions(root, entries(patch.get("promote"), "promote"), actor=args.actor, dry_run=args.dry_run)

    keywords = [str(value) for value in (patch.get("verify_absent_keywords") or []) if str(value)]
    if keywords:
        verify_ok = verify_absent_keywords(root, keywords, exclude_ids=planned_deprecated_ids if args.dry_run else set())
        if not verify_ok and not args.dry_run:
            return 1

    should_validate = args.validate or (not args.dry_run and not args.no_validate)
    if should_validate:
        return run_validate(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
