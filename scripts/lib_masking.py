#!/usr/bin/env python3
"""Shared masking and residual sensitive-data scanning."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


FIELD_NAME_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("phone", re.compile(r"(phone|mobile|tel)", re.I)),
    ("email", re.compile(r"email", re.I)),
    ("token", re.compile(r"(token|access_token|refresh_token|api[_-]?key|session|cookie)", re.I)),
    ("password", re.compile(r"(password|passwd|pwd)", re.I)),
    ("secret", re.compile(r"(secret|app_secret|access_key|access_key_secret)", re.I)),
    ("identity", re.compile(r"(openid|unionid|user_id|id_card|identity)", re.I)),
    ("address", re.compile(r"(address|receiver_address|shipping_address)", re.I)),
    ("response_body", re.compile(r"(callback_response|response_body|raw_response|payload)", re.I)),
]

VALUE_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.S), "[MASKED_PRIVATE_KEY]"),
    ("url_basic_auth", re.compile(r"([a-z]+://)[^\s:/]+:[^\s@/]{6,}@([^\s]+)", re.I), r"\1[MASKED]@\2"),
    ("access_key_secret", re.compile(r"(?i)(access[_-]?key[_-]?secret\s*[:=]\s*['\"]?)[A-Za-z0-9/+=]{8,}"), r"\1[MASKED_SECRET]"),
    ("api_token_assignment", re.compile(r"(?i)((?:api[_-]?key|token|secret|password|passwd|pwd)\s*[:=]\s*['\"]?)[A-Za-z0-9_./+=-]{8,}"), r"\1[MASKED_SECRET]"),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"), "[MASKED_JWT]"),
    ("phone", re.compile(r"(?<![A-Za-z0-9])1[3-9]\d{9}(?![A-Za-z0-9])"), "[MASKED_PHONE]"),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[MASKED_EMAIL]"),
    (
        "token_like",
        re.compile(r"\b(?=[A-Za-z0-9_+=-]{48,}\b)(?=[A-Za-z0-9_+=-]*[A-Z])(?=[A-Za-z0-9_+=-]*[a-z])(?=[A-Za-z0-9_+=-]*\d)[A-Za-z0-9_+=-]+\b"),
        "[MASKED_TOKEN]",
    ),
]

RESPONSE_BODY_FIELDS = {"callback_response", "response_body", "raw_response", "payload"}


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    category: str
    matched_kind: str
    hint: str
    path: str | None = None
    line: int | None = None
    field: str | None = None
    sample: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def field_risk_kind(field_name: str) -> str | None:
    for kind, pattern in FIELD_NAME_PATTERNS:
        if pattern.search(field_name or ""):
            return kind
    return None


def is_response_body_field(field_name: str) -> bool:
    lowered = (field_name or "").lower()
    return any(name in lowered for name in RESPONSE_BODY_FIELDS)


def _mask_string(text: str) -> str:
    masked = text
    for _kind, pattern, replacement in VALUE_PATTERNS:
        masked = pattern.sub(replacement, masked)
    if len(masked) > 800 and (masked.lstrip().startswith(("{", "[", "<")) or re.search(r"(?i)<html|</|\\\"|\\n", masked)):
        return "[MASKED_RESPONSE_BODY]"
    return masked


def _mask_nested_response(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return value
    try:
        parsed = json.loads(stripped)
    except Exception:
        return _mask_string(value)
    masked = mask_value("response_body", parsed)
    return json.dumps(masked, ensure_ascii=False, sort_keys=True)


def mask_value(field_name: str, value: Any) -> Any:
    kind = field_risk_kind(field_name)
    if value is None:
        return None
    if isinstance(value, dict):
        return mask_row(value)
    if isinstance(value, list):
        return [mask_value(field_name, item) for item in value]
    if isinstance(value, (int, float, bool)):
        if kind in {"phone", "identity", "token", "password", "secret"}:
            return f"[MASKED_{kind.upper()}]"
        return value
    text = str(value)
    if is_response_body_field(field_name):
        return _mask_nested_response(text)
    if kind in {"token", "password", "secret"} and text:
        return f"[MASKED_{kind.upper()}]"
    if kind in {"phone", "email", "identity", "address"} and text:
        return f"[MASKED_{kind.upper()}]"
    return _mask_string(text)


def mask_row(row: dict[str, Any]) -> dict[str, Any]:
    return {str(key): mask_value(str(key), value) for key, value in row.items()}


def mask_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [mask_row(row) for row in rows]


def field_name_findings(row: dict[str, Any], *, path: str | None = None) -> list[Finding]:
    findings: list[Finding] = []
    for field, value in row.items():
        kind = field_risk_kind(str(field))
        if kind:
            findings.append(
                Finding(
                    level="warning",
                    code="sensitive_field_name",
                    category="sensitive_field_name_risk",
                    matched_kind=kind,
                    field=str(field),
                    path=path,
                    sample="" if value in (None, "") else None,
                    hint="Field name suggests sensitive data; masked values before writing.",
                )
            )
    return findings


def residual_scan_text(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for kind, pattern, _replacement in VALUE_PATTERNS:
            if pattern.search(line):
                findings.append(
                    Finding(
                        level="error",
                        code="secret_leak",
                        category="secret_leak",
                        matched_kind=kind,
                        line=lineno,
                        sample=line.strip()[:120],
                        hint="Credential-like or personal data remained after masking; block write or mask earlier.",
                    )
                )
    return findings


def residual_scan_file(path: Path) -> list[Finding]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    findings = residual_scan_text(text)
    return [
        Finding(
            level=item.level,
            code=item.code,
            category=item.category,
            matched_kind=item.matched_kind,
            hint=item.hint,
            path=str(path),
            line=item.line,
            field=item.field,
            sample=item.sample,
        )
        for item in findings
    ]


def assert_no_high_risk_text(text: str, *, context: str) -> None:
    findings = residual_scan_text(text)
    if findings:
        first = findings[0]
        location = f" line={first.line}" if first.line else ""
        raise RuntimeError(f"High-risk residual sensitive value in {context}:{location} kind={first.matched_kind}")
