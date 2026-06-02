#!/usr/bin/env python3
"""Fetch Metabase card metadata and native SQL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from lib_data_sources import exit_with_error, load_profile, metabase_request


def load_card(args: argparse.Namespace) -> tuple[dict[str, Any], str]:
    if args.mock_file:
        fixture = json.loads(args.mock_file.read_text(encoding="utf-8"))
        card = fixture.get("card") if isinstance(fixture, dict) and isinstance(fixture.get("card"), dict) else fixture
        if not isinstance(card, dict):
            raise RuntimeError("--mock-file must contain a card object or {\"card\": {...}}")
        return card, "mock_file"
    cfg = load_profile("metabase", args.profile, args.config, args.env_file)
    return metabase_request(cfg, "GET", f"/api/card/{args.card_id}"), "metabase_api"


def owner_hint(card: dict[str, Any]) -> dict[str, Any]:
    creator = card.get("creator") or {}
    return {
        "creator_id": creator.get("id") or card.get("creator_id"),
        "creator_name": creator.get("common_name") or creator.get("name"),
        "creator_email": creator.get("email"),
    }


def collection_hint(card: dict[str, Any]) -> dict[str, Any]:
    collection = card.get("collection") or {}
    return {
        "collection_id": card.get("collection_id") or collection.get("id"),
        "collection_name": card.get("collection_name") or collection.get("name"),
    }


def dashboard_evidence_risk(card: dict[str, Any]) -> dict[str, Any]:
    dashboards = card.get("dashboards") or card.get("dashboard_cards") or []
    dashboard_ids: list[Any] = []
    if isinstance(dashboards, list):
        for item in dashboards:
            if isinstance(item, dict):
                dashboard = item.get("dashboard") or item
                dashboard_ids.append(dashboard.get("id") or item.get("dashboard_id"))
    dashboard_ids = [item for item in dashboard_ids if item is not None]
    return {
        "evidence_type": "dashboard",
        "source": "metabase",
        "card_id": card.get("id"),
        "dashboard_ids": dashboard_ids,
        "risk": (
            "Metabase card/dashboard evidence is not final truth by itself; confirm owner, updated_at, "
            "parameter defaults, permissions, and authoritative metric definition."
        ),
    }


def summarize_card(card: dict[str, Any], source: str) -> dict[str, Any]:
    dataset_query = card.get("dataset_query") or {}
    native = dataset_query.get("native") or {}
    return {
        "source": source,
        "card_id": card.get("id"),
        "name": card.get("name"),
        "description": card.get("description"),
        "display": card.get("display"),
        "database_id": dataset_query.get("database") or card.get("database_id"),
        "query_type": dataset_query.get("type"),
        "native_sql": native.get("query") or "",
        "parameters": card.get("parameters") or [],
        "template_tags": native.get("template-tags") or native.get("template_tags") or {},
        "updated_at": card.get("updated_at"),
        "created_at": card.get("created_at"),
        "collection": collection_hint(card),
        "owner": owner_hint(card),
        "dashboard_evidence": dashboard_evidence_risk(card),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Get a Metabase card and print SQL.")
    parser.add_argument("card_id", type=int)
    parser.add_argument("--profile", default="default")
    parser.add_argument(
        "--config",
        type=Path,
        help="YAML config. Defaults: $INTERNAL_DATA_QUERY_CONFIG, data-query-work/config/data-sources.yaml, local/data-sources.yaml, ~/.internal-data-query/data-sources.yaml.",
    )
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--mock-file", type=Path, help="Read a local mock fixture instead of calling Metabase.")
    args = parser.parse_args()

    card, source = load_card(args)
    summary = summarize_card(card, source)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"source: {summary['source']}")
        print(f"id: {summary['card_id']}")
        print(f"name: {summary['name']}")
        print(f"database_id: {summary['database_id']}")
        print(f"updated_at: {summary['updated_at']}")
        print(f"collection: {summary['collection'].get('collection_name')} ({summary['collection'].get('collection_id')})")
        print(f"owner: {summary['owner'].get('creator_name')} <{summary['owner'].get('creator_email')}>")
        print(f"parameters: {json.dumps(summary['parameters'], ensure_ascii=False)}")
        print(f"template_tags: {json.dumps(summary['template_tags'], ensure_ascii=False)}")
        print(f"dashboard_evidence: {json.dumps(summary['dashboard_evidence'], ensure_ascii=False)}")
        print("sql:")
        print(summary["native_sql"])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        raise SystemExit(exit_with_error(exc))
