#!/usr/bin/env python3
"""Suggest low-interruption query knowledge capture moments."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


VERIFIED_STATUSES = {"verified", "query_verified", "pass", "pass_with_risks", "partially_verified"}
CONFIRMATION_SIGNALS = ("记一下", "记住", "以后按这个口径", "这个表你记住", "confirmed", "reuse this")


@dataclass
class Signal:
    query_round: int
    reuse_count: int
    verification_status: str
    user_confirmed: bool
    high_value_observation: bool
    candidate_count: int


def load_signal(args: argparse.Namespace) -> Signal:
    session_path = args.session or args.input
    if session_path:
        data = json.loads(session_path.read_text(encoding="utf-8"))
        if args.case:
            cases = data.get("cases", {})
            if args.case not in cases:
                raise SystemExit(f"unknown case: {args.case}")
            data = cases[args.case]
        interactions = data.get("interactions", [])
        text = "\n".join(str(item.get("text", "")) for item in interactions)
        user_confirmed = bool(data.get("user_confirmed")) or any(signal in text for signal in CONFIRMATION_SIGNALS)
        return Signal(
            query_round=int(data.get("query_round", len(interactions) or 1)),
            reuse_count=int(data.get("reuse_count", 0)),
            verification_status=str(data.get("verification_status", "unverified")),
            user_confirmed=user_confirmed,
            high_value_observation=bool(data.get("high_value_observation", False)),
            candidate_count=int(data.get("candidate_count", 0)),
        )
    return Signal(
        query_round=args.query_round,
        reuse_count=args.reuse_count,
        verification_status=args.verification_status,
        user_confirmed=args.user_confirmed,
        high_value_observation=args.high_value_observation,
        candidate_count=args.candidate_count,
    )


def should_suggest(signal: Signal) -> tuple[bool, str]:
    if signal.user_confirmed:
        return True, "用户已经给出明确记忆/口径确认信号，可生成 candidate 但仍需 review。"
    if signal.query_round < 3 and signal.reuse_count < 2:
        return False, "查询仍处早期对齐阶段，暂不打扰。"
    if signal.verification_status not in VERIFIED_STATUSES:
        return False, "结果尚未验证，继续隐性记录候选，不提示沉淀。"
    if signal.reuse_count >= 2:
        return True, "同一知识已多次复用且结果稳定，适合低打扰提示沉淀。"
    if signal.query_round >= 4 and signal.high_value_observation:
        return True, "查询已多轮推进并出现高价值结构化认知，适合提示沉淀。"
    return False, "尚未达到稳定复用或明确确认阈值。"


def main() -> int:
    parser = argparse.ArgumentParser(description="Decide whether to suggest query knowledge capture.")
    parser.add_argument("--session", type=Path, help="Mock/offline query session JSON.")
    parser.add_argument("--input", type=Path, help="Alias for --session.")
    parser.add_argument("--case", help="Case name inside a session fixture.")
    parser.add_argument("--query-round", type=int, default=1)
    parser.add_argument("--reuse-count", type=int, default=0)
    parser.add_argument("--verification-status", default="unverified")
    parser.add_argument("--user-confirmed", action="store_true")
    parser.add_argument("--high-value-observation", action="store_true")
    parser.add_argument("--candidate-count", type=int, default=0)
    args = parser.parse_args()

    signal = load_signal(args)
    suggest, reason = should_suggest(signal)
    result = {
        "suggest_capture": suggest,
        "reason": reason,
        "low_interruption_prompt": (
            "这条口径已经复用并验证过。我可以把它写成 data-query-work/knowledge candidate，等待 review 后再进入共享知识库。"
            if suggest
            else ""
        ),
        "status_to_write": "candidate" if suggest else "",
        "maturity_hint": "ready_for_candidate" if suggest else signal.verification_status,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
