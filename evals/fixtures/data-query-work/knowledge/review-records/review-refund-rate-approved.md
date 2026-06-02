---
id: review.metric.refund_rate.monthly.v1
schema_version: "1.0"
status: reviewed
created_by: data-query-eval
reviewed_by: data-query-reviewer
approved_by: ""
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
  - type: reviewer_note
    path: evals/fixtures/query-case.md
last_verified_at: 2026-06-01
sync_notes: []
maturity: ready_for_review
capture_trigger: review_record
source_interaction:
  - query-case-refund-rate-2026-05
---

# Review record

Reviewer confirmed the fixture has explicit time range, grain, and validation evidence.
