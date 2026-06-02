#!/usr/bin/env python3
"""Promote a query knowledge item, move it by status, and append the promotion log."""

from __future__ import annotations

import argparse
from pathlib import Path

from lib_query_knowledge import append_log, apply_promotion_plan, as_list, build_promotion_plan


VALID_TARGETS = {"reviewed", "approved", "deprecated"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote one data-query-work/knowledge item.")
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
    plan = build_promotion_plan(
        root,
        args.item,
        args.to,
        reviewers=args.reviewer,
        approvers=args.approver,
        evidence=args.evidence,
    )
    source_rel = plan.source_path.relative_to(root).as_posix() if plan.source_path.is_relative_to(root) else str(plan.source_path)
    target_rel = plan.target_path.relative_to(root).as_posix() if plan.target_path.is_relative_to(root) else str(plan.target_path)
    prefix = "DRY-RUN " if args.dry_run else ""
    print(f"{prefix}PROMOTE: {plan.item_id} {plan.old_status} -> {plan.new_status}")
    print(f"{prefix}MOVE: {source_rel} -> {target_rel}")

    if args.dry_run:
        return 0

    apply_promotion_plan(plan)
    append_log(
        root,
        plan.item_id,
        plan.old_status,
        plan.new_status,
        args.actor,
        ",".join(as_list(plan.data.get("reviewed_by"))),
        "; ".join(as_list(plan.data.get("validation_evidence"))),
        args.notes,
    )
    print("PASS: promotion applied, file moved, and promotion-log updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
