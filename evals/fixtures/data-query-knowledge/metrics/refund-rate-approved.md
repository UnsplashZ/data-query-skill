---
id: metric.refund_rate.monthly.v1
schema_version: "1.0"
status: approved
created_by: data-query-eval
reviewed_by: data-query-reviewer
approved_by: data-query-approver
source_status: mock_fixture
confidence: high
risk_level: low
domain: refund
metric: refund_rate
grain: month, sku
expires_at: 2026-12-31
supersedes: []
conflicts_with: []
validation_evidence:
  - type: sql_static_check
    path: evals/fixtures/readonly.sql
last_verified_at: 2026-06-01
sync_notes: []
maturity: ready_for_review
capture_trigger: verified_result_summary
source_interaction:
  - query-case-refund-rate-2026-05
---

# Monthly refund rate

Use approved refund amount divided by paid GMV for the same SKU and month.
This fixture is approved only for offline eval behavior and does not represent a real internal metric.
