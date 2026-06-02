---
id: candidate.refund_rate.order_count.v1
schema_version: "1.0"
status: candidate
created_by: data-query-eval
reviewed_by: ""
approved_by: ""
source_status: mock_fixture
confidence: medium
risk_level: medium
domain: refund
metric: refund_rate
grain: month, sku
expires_at: 2026-09-30
supersedes: []
conflicts_with:
  - metric.refund_rate.monthly.v1
validation_evidence:
  - type: observation
    path: evals/fixtures/query-session.json
last_verified_at: ""
sync_notes: []
maturity: observed
capture_trigger: structured_query_artifact
source_interaction:
  - eval-query-session-refund-2026-05
---

# Candidate refund rate by order count

This candidate intentionally conflicts with the approved amount-based definition.
Default search must not return it unless candidate status is explicitly requested.
