---
id: source.analytics.refund_order_daily.v1
schema_version: "1.0"
status: reviewed
created_by: data-query-eval
reviewed_by: data-query-reviewer
approved_by: ""
source_status: mock_fixture
confidence: medium
risk_level: medium
domain: refund
metric: refund_amount
grain: day, sku
expires_at: 2026-12-31
supersedes: []
conflicts_with: []
validation_evidence:
  - type: schema_kb
    path: evals/fixtures/readonly.sql
last_verified_at: 2026-06-01
sync_notes: []
maturity: query_verified
capture_trigger: structured_query_artifact
source_interaction:
  - schema_kb
---

# Refund order daily source

Mock source profile for static evals. It contains no real schema endpoint or credential.
