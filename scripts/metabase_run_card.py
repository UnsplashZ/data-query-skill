#!/usr/bin/env python3
"""Run a Metabase card and export CSV/XLSX."""

from __future__ import annotations

import argparse
import json
import time
import zipfile
from html import escape
from pathlib import Path
from typing import Any

from lib_data_sources import exit_with_error, export_rows, load_profile, metabase_request, metabase_result_to_rows, now_stem


def load_parameters(raw: str, path: Path | None) -> list[dict[str, Any]]:
    if path:
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = json.loads(raw)
    if not isinstance(data, list):
        raise RuntimeError("Metabase parameters must be a JSON array.")
    return [dict(item) for item in data]


def load_mock(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(fixture, list):
        return {"query_result": fixture}
    if not isinstance(fixture, dict):
        raise RuntimeError("--mock-file must contain a JSON object or result row array.")
    if "query_result" not in fixture and "result" not in fixture:
        raise RuntimeError("--mock-file must contain query_result or result.")
    return fixture


def supplied_parameter_names(parameters: list[dict[str, Any]]) -> set[str]:
    names: set[str] = set()
    for param in parameters:
        if param.get("id"):
            names.add(str(param["id"]))
        if param.get("name"):
            names.add(str(param["name"]))
        target = param.get("target")
        if isinstance(target, list):
            for item in target:
                if isinstance(item, list) and len(item) >= 2 and item[0] in {"template-tag", "dimension"}:
                    names.add(str(item[1]))
    return names


def required_parameter_names(card: dict[str, Any]) -> list[str]:
    required: list[str] = []
    for param in card.get("parameters") or []:
        if isinstance(param, dict) and param.get("required"):
            name = param.get("id") or param.get("slug") or param.get("name")
            if name:
                required.append(str(name))
    native = ((card.get("dataset_query") or {}).get("native") or {})
    for tag_name, tag in (native.get("template-tags") or native.get("template_tags") or {}).items():
        if isinstance(tag, dict) and tag.get("required"):
            required.append(str(tag.get("id") or tag.get("name") or tag_name))
    seen: set[str] = set()
    ordered: list[str] = []
    for name in required:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def assert_required_parameters(card: dict[str, Any], parameters: list[dict[str, Any]]) -> None:
    if not card:
        return
    supplied = supplied_parameter_names(parameters)
    missing = [name for name in required_parameter_names(card) if name not in supplied]
    if missing:
        raise RuntimeError(
            "Missing required Metabase parameters: "
            + ", ".join(missing)
            + ". Pass --parameters JSON like "
            + json.dumps([{"type": "category", "target": ["variable", ["template-tag", missing[0]]], "value": "<value>"}])
            + " or pass --parameters-file path/to/parameters.json."
        )


def run_from_mock(fixture: dict[str, Any], parameters: list[dict[str, Any]]) -> tuple[Any, float, str]:
    card = fixture.get("card") if isinstance(fixture.get("card"), dict) else {}
    assert_required_parameters(card, parameters)
    return fixture.get("query_result") or fixture.get("result"), 0.0, "mock_file"


def column_name(index: int) -> str:
    name = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def cell_xml(row_index: int, col_index: int, value: Any) -> str:
    ref = f"{column_name(col_index)}{row_index}"
    if isinstance(value, bool):
        return f'<c r="{ref}" t="b"><v>{1 if value else 0}</v></c>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{ref}"><v>{value}</v></c>'
    text = "" if value is None else str(value)
    return f'<c r="{ref}" t="inlineStr"><is><t>{escape(text)}</t></is></c>'


def write_minimal_xlsx(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    sheet_rows = [columns] + [[row.get(col) for col in columns] for row in rows]
    row_xml = []
    for row_index, values in enumerate(sheet_rows, start=1):
        cells = "".join(cell_xml(row_index, col_index, value) for col_index, value in enumerate(values))
        row_xml.append(f'<row r="{row_index}">{cells}</row>')
    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(row_xml)}</sheetData>"
        "</worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="result" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/worksheets/sheet1.xml", worksheet)


def export_card_rows(output_dir: Path, stem: str, fmt: str, rows: list[dict[str, Any]], columns: list[str]) -> Path:
    if fmt == "xlsx":
        path = output_dir / f"{stem}.xlsx"
        write_minimal_xlsx(path, columns, rows)
        return path
    return export_rows(output_dir, stem, fmt, rows, columns)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a Metabase card and export the result.")
    parser.add_argument("card_id", type=int)
    parser.add_argument("--profile", default="default")
    parser.add_argument(
        "--config",
        type=Path,
        help="YAML config. Defaults: $INTERNAL_DATA_QUERY_CONFIG, data-query-work/config/data-sources.yaml, local/data-sources.yaml, ~/.internal-data-query/data-sources.yaml.",
    )
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--parameters", default="[]", help="Metabase parameters JSON array.")
    parser.add_argument("--parameters-file", type=Path, help="Read Metabase parameters JSON array from file.")
    parser.add_argument("--output-dir", type=Path, default=Path("data-query-work/exports"))
    parser.add_argument("--output-format", choices=["csv", "xlsx"], default="csv")
    parser.add_argument("--mock-file", type=Path, help="Read a local mock fixture instead of calling Metabase.")
    args = parser.parse_args()

    params = load_parameters(args.parameters, args.parameters_file)
    if args.mock_file:
        result, elapsed, source = run_from_mock(load_mock(args.mock_file), params)
    else:
        cfg = load_profile("metabase", args.profile, args.config, args.env_file)
        card = metabase_request(cfg, "GET", f"/api/card/{args.card_id}")
        assert_required_parameters(card, params)
        started = time.perf_counter()
        result = metabase_request(cfg, "POST", f"/api/card/{args.card_id}/query/json", {"parameters": params})
        elapsed = time.perf_counter() - started
        source = "metabase_api"
    columns, rows = metabase_result_to_rows(result)
    out = export_card_rows(args.output_dir, now_stem(f"metabase-card-{args.card_id}"), args.output_format, rows, columns)
    print(json.dumps({
        "source": source,
        "card_id": args.card_id,
        "evidence_type": "dashboard",
        "dashboard_evidence": {
            "source": "metabase",
            "card_id": args.card_id,
            "risk": "Dashboard/card result evidence; confirm owner, updated_at, parameter values, and metric authority before final use.",
        },
        "row_count": len(rows),
        "elapsed_seconds": round(elapsed, 3),
        "output_path": str(out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        raise SystemExit(exit_with_error(exc))
