#!/usr/bin/env python3
"""Capture low-risk query knowledge candidates from query artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from lib_workspace import warn_if_needed, writable_knowledge_root


SENSITIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"[a-z]+://[^\s:/]+:[^\s@/]{6,}@[^\s]+", re.I),
    re.compile(r"(?i)(password|passwd|pwd|secret|token|api[_-]?key)\s*[:=]\s*['\"]?[^'\"\s]{6,}"),
    re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
]

SECTION_RE = re.compile(r"^#{1,3}\s+(.+?)\s*$", re.M)
TABLE_RE = re.compile(r"(?i)\b(?:from|join)\s+([a-zA-Z_][\w.]*)(?:\s|$)")
METRIC_RE = re.compile(r"(?im)^-\s*Metric:\s*(.+)$")
STATUS_RE = re.compile(r"(?im)^-\s*Status:\s*`?([^`\n]+)`?")


@dataclass
class Candidate:
    candidate_id: str
    operation_date: str
    domain: str
    topic: str
    status: str
    maturity: str
    capture_trigger: str
    source_interaction: str
    source_type: str
    title: str
    summary: str
    evidence: list[str]
    risk: list[str]


def has_sensitive_value(text: str) -> bool:
    return any(pattern.search(text) for pattern in SENSITIVE_PATTERNS)


def clean_line(line: str) -> str:
    line = line.strip()
    for pattern in SENSITIVE_PATTERNS:
        line = pattern.sub("[REDACTED]", line)
    return line


def extract_bullets(text: str, headings: tuple[str, ...]) -> list[str]:
    lines = text.splitlines()
    wanted = {heading.lower() for heading in headings}
    active = False
    found: list[str] = []
    for line in lines:
        heading_match = SECTION_RE.match(line)
        if heading_match:
            active = heading_match.group(1).strip().lower() in wanted
            continue
        if not active:
            continue
        stripped = clean_line(line)
        if stripped.startswith("-") and stripped not in {"-", "- [ ]"}:
            found.append(stripped.lstrip("- ").strip())
    return found


def source_interaction_for(source_type: str, path: Path | None) -> str:
    if path:
        return f"{source_type}:{path.name}"
    return source_type


def maturity_for(source_type: str, text: str) -> str:
    if source_type == "user-assertion":
        return "user_asserted"
    status_match = STATUS_RE.search(text)
    if status_match and "verified" in status_match.group(1).lower():
        return "query_verified"
    return "observed"


def trigger_for(source_type: str, text: str) -> str:
    lowered = text.lower()
    if source_type == "user-assertion" or any(phrase in text for phrase in ("记一下", "记住", "以后按这个口径")):
        return "user_confirmation_signal"
    if "verified" in lowered:
        return "verified_result_summary"
    if TABLE_RE.search(text):
        return "structured_query_artifact"
    return "query_artifact_observation"


def summarize(source_type: str, text: str) -> tuple[str, str, list[str], list[str]]:
    metric = ""
    metric_match = METRIC_RE.search(text)
    if metric_match:
        metric = clean_line(metric_match.group(1))
    tables = sorted(set(TABLE_RE.findall(text)))
    assumptions = extract_bullets(text, ("Assumptions", "Risks", "Risks / Caveats", "Verification"))

    parts = []
    if metric:
        parts.append(f"metric={metric}")
    if tables:
        parts.append("tables=" + ", ".join(tables[:5]))
    title = "Query knowledge observation"
    if metric:
        title = f"Metric observation: {metric[:80]}"
    elif tables:
        title = f"Source observation: {tables[0]}"

    evidence = []
    if metric:
        evidence.append(f"Metric: {metric}")
    for table in tables[:5]:
        evidence.append(f"Source table/card: {table}")
    for item in assumptions[:5]:
        if item and not has_sensitive_value(item):
            evidence.append(item)

    if not evidence:
        for line in text.splitlines():
            cleaned = clean_line(line)
            if cleaned and not cleaned.startswith("#") and not has_sensitive_value(line):
                evidence.append(cleaned[:180])
            if len(evidence) >= 3:
                break

    summary = "; ".join(parts) if parts else f"Observed reusable knowledge from {source_type}."
    risks = []
    if source_type in {"query-brief", "sql-review"}:
        risks.append("May be pre-execution or partially verified; keep candidate until reviewed.")
    if not tables and "metabase" not in source_type:
        risks.append("No concrete source table/card extracted.")
    return title, summary, evidence, risks


def slugify(value: str, *, fallback: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or fallback


def infer_domain(text: str) -> str:
    lowered = text.lower()
    for key in ("refund", "gmv", "cashflow", "cost", "handover", "renewal", "order", "user-relationship"):
        if key in lowered:
            return key
    return "general"


def infer_topic(title: str, summary: str, evidence: list[str]) -> str:
    source = " ".join([title, summary, " ".join(evidence[:3])])
    topic = re.sub(r"(?i)\b(metric|source|observation|tables?|card|query|knowledge)\b", " ", source)
    return slugify(topic, fallback="query-knowledge")


def make_candidate(text: str, source_type: str, source_path: Path | None) -> Candidate:
    if has_sensitive_value(text):
        text = "\n".join(clean_line(line) for line in text.splitlines())
    title, summary, evidence, risks = summarize(source_type, text)
    digest = hashlib.sha1((source_type + "\n" + summary + "\n" + "\n".join(evidence)).encode("utf-8")).hexdigest()[:12]
    operation_date = datetime.now(timezone.utc).date().isoformat()
    domain = infer_domain("\n".join([title, summary, "\n".join(evidence)]))
    topic = infer_topic(title, summary, evidence)
    return Candidate(
        candidate_id=f"kcap-{digest}",
        operation_date=operation_date,
        domain=domain,
        topic=topic,
        status="candidate",
        maturity=maturity_for(source_type, text),
        capture_trigger=trigger_for(source_type, text),
        source_interaction=source_interaction_for(source_type, source_path),
        source_type=source_type,
        title=title,
        summary=summary,
        evidence=evidence,
        risk=risks,
    )


def source_status_for(candidate: Candidate) -> str:
    if candidate.source_type == "user-assertion":
        return "user_asserted"
    if candidate.maturity == "query_verified":
        return "observed"
    return "observed"


def frontmatter_for(candidate: Candidate) -> dict[str, Any]:
    return {
        "id": candidate.candidate_id,
        "schema_version": "1.0",
        "status": "candidate",
        "created_by": "capture_query_knowledge",
        "reviewed_by": [],
        "approved_by": [],
        "domain": candidate.domain,
        "metric": [],
        "grain": "",
        "source": [],
        "source_status": source_status_for(candidate),
        "confidence": "low",
        "risk_level": "medium",
        "expires_at": None,
        "supersedes": [],
        "conflicts_with": [],
        "validation_evidence": [],
        "last_verified_at": None,
        "sync_notes": [
            "Captured automatically as candidate only; not approved truth.",
        ],
        "maturity": candidate.maturity,
        "capture_trigger": candidate.capture_trigger,
        "source_interaction": [candidate.source_interaction],
    }


def render_candidate(candidate: Candidate) -> str:
    evidence = "\n".join(f"- {item}" for item in candidate.evidence) or "- TBD"
    risks = "\n".join(f"- {item}" for item in candidate.risk) or "- Not reviewed."
    frontmatter = yaml.safe_dump(frontmatter_for(candidate), allow_unicode=True, sort_keys=False).strip()
    return f"""---
{frontmatter}
---

# {candidate.operation_date} / {candidate.domain} / {candidate.topic} / query knowledge candidate

- Candidate ID: {candidate.candidate_id}
- Status: candidate
- Owner:
- Source: {candidate.source_interaction}
- Related files:
- Validation:
- Risk: medium
- Maturity: {candidate.maturity}
- Capture trigger: {candidate.capture_trigger}
- Source interaction: {candidate.source_interaction}
- Source type: {candidate.source_type}
- Created at: {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}

## Candidate Summary

{candidate.summary}

## Evidence

{evidence}

## Review Notes

- Default capture is not approved truth.
- Reviewer:
- Review status: pending

## Risks

{risks}
"""


def read_inputs(paths: list[Path], inline_text: str | None) -> list[tuple[Path | None, str]]:
    items: list[tuple[Path | None, str]] = []
    if inline_text:
        items.append((None, inline_text))
    for path in paths:
        items.append((path, path.read_text(encoding="utf-8", errors="ignore")))
    return items


def output_subdir(root: Path, candidate: Candidate) -> Path:
    selection = writable_knowledge_root(root)
    warn_if_needed(selection)
    knowledge_root = selection.path
    mapping = {
        "observed": knowledge_root / "candidates" / "observations",
        "user_asserted": knowledge_root / "candidates" / "user-assertions",
        "query_verified": knowledge_root / "candidates" / "query-verified",
        "reused": knowledge_root / "candidates" / "reusable-patterns",
    }
    return mapping.get(candidate.maturity, mapping["observed"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture query knowledge candidates without approving them.")
    parser.add_argument("inputs", nargs="*", type=Path, help="Query brief, SQL review, result summary, Metabase note, or assertion files.")
    parser.add_argument("--input", dest="input_files", action="append", type=Path, default=[], help="Input file alias; can repeat.")
    parser.add_argument("--text", help="Inline text to capture.")
    parser.add_argument(
        "--source-type",
        default="query-brief",
        choices=["query-brief", "sql-review", "result-summary", "metabase", "user-assertion"],
        help="Type of source interaction.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print candidates as JSON and do not write files.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="Skill root directory.")
    args = parser.parse_args()

    all_inputs = list(args.inputs) + list(args.input_files)
    if not all_inputs and not args.text:
        parser.error("provide at least one input file or --text")

    root = args.root.resolve()
    candidates = [make_candidate(text, args.source_type, path) for path, text in read_inputs(all_inputs, args.text)]

    if args.dry_run:
        print(json.dumps([asdict(candidate) for candidate in candidates], ensure_ascii=False, indent=2))
        return 0

    written: list[Path] = []
    for candidate in candidates:
        directory = output_subdir(root, candidate)
        directory.mkdir(parents=True, exist_ok=True)
        filename = f"{candidate.operation_date}__{candidate.domain}__{candidate.topic}__candidate-{candidate.candidate_id}.md"
        path = directory / filename
        path.write_text(render_candidate(candidate), encoding="utf-8")
        written.append(path)

    for path in written:
        print(path.relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
