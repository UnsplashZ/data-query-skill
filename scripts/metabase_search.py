#!/usr/bin/env python3
"""Search Metabase cards/dashboards before writing new SQL."""

from __future__ import annotations

import argparse
import json
import urllib.parse
from pathlib import Path
from typing import Any

from lib_data_sources import exit_with_error, load_profile, metabase_request


def load_search_result(path: Path) -> Any:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(fixture, dict) and isinstance(fixture.get("data"), list):
        return fixture
    if isinstance(fixture, list):
        return {"data": fixture}
    raise RuntimeError("--mock-file must contain a Metabase search object with data[] or a JSON array.")


def evidence_for_item(item: dict[str, Any]) -> dict[str, Any]:
    model = item.get("model") or item.get("type")
    item_id = item.get("id")
    collection = item.get("collection") if isinstance(item.get("collection"), dict) else {}
    evidence_type = "dashboard" if model == "dashboard" else "card" if model == "card" else "metabase_object"
    return {
        "evidence_type": evidence_type,
        "source": "metabase",
        "object_model": model,
        "object_id": item_id,
        "object_name": item.get("name"),
        "collection": item.get("collection_name") or collection.get("name"),
        "dashboard_id": item_id if model == "dashboard" else item.get("dashboard_id"),
        "card_id": item_id if model == "card" else item.get("card_id"),
        "risk": (
            "dashboard evidence only; confirm owner, updated_at, filters, and authoritative metric definition "
            "before using as final truth"
        ),
    }


def with_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for item in items:
        next_item = dict(item)
        evidence = evidence_for_item(next_item)
        next_item["dashboard_evidence"] = evidence if evidence["evidence_type"] == "dashboard" else None
        next_item["card_evidence"] = evidence if evidence["evidence_type"] == "card" else None
        enriched.append(next_item)
    return enriched


def main() -> int:
    parser = argparse.ArgumentParser(description="Search Metabase objects.")
    parser.add_argument("query")
    parser.add_argument("--profile", default="default")
    parser.add_argument(
        "--config",
        type=Path,
        help="YAML config. Defaults: $INTERNAL_DATA_QUERY_CONFIG, data-query-work/config/data-sources.yaml, local/data-sources.yaml, ~/.internal-data-query/data-sources.yaml.",
    )
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--type", choices=["card", "dashboard", "collection"])
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--mock-file", type=Path, help="Read a local mock fixture instead of calling Metabase.")
    args = parser.parse_args()

    if args.mock_file:
        result = load_search_result(args.mock_file)
    else:
        cfg = load_profile("metabase", args.profile, args.config, args.env_file)
        qs = {"q": args.query}
        if args.type:
            qs["models"] = args.type
        result = metabase_request(cfg, "GET", "/api/search?" + urllib.parse.urlencode(qs))
    items = result.get("data") if isinstance(result, dict) else result
    items = with_evidence((items or [])[: args.limit])
    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return 0
    for item in items:
        evidence = item.get("dashboard_evidence") or item.get("card_evidence") or {}
        print(
            f"{item.get('model') or item.get('type')} | {item.get('id')} | {item.get('name')} | "
            f"{item.get('collection_name','')} | evidence={evidence.get('evidence_type')} "
            f"dashboard_id={evidence.get('dashboard_id')} card_id={evidence.get('card_id')}"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        raise SystemExit(exit_with_error(exc))
