---
id: metric.refund_rate.monthly.v0
schema_version: "1.0"
status: deprecated
created_by: data-query-eval
reviewed_by: data-query-reviewer
approved_by: data-query-approver
source_status: mock_fixture
confidence: low
risk_level: high
domain: refund
metric: refund_rate
grain: month
expires_at: 2026-01-31
supersedes: []
conflicts_with:
  - metric.refund_rate.monthly.v1
validation_evidence:
  - type: migration_fixture
    path: evals/fixtures/data-query-knowledge-old/data-query-knowledge/metrics/refund-rate-legacy.md
last_verified_at: 2025-12-31
sync_notes: []
maturity: deprecated
capture_trigger: migration
source_interaction:
  - legacy.refund_rate.monthly
deprecation_reason: Replaced by metric.refund_rate.monthly.v1.
---

# Deprecated refund rate fixture

Default search must exclude this deprecated item.
