---
id: join.refund_order_daily.to.gmv_daily.v1
schema_version: "1.0"
status: reviewed
created_by: data-query-eval
reviewed_by: data-query-reviewer
approved_by: ""
source_status: mock_fixture
confidence: medium
risk_level: medium
domain: refund
metric: refund_rate
grain: day, sku
expires_at: 2026-12-31
supersedes: []
conflicts_with: []
validation_evidence:
  - type: review_record
    path: evals/fixtures/data-query-work/knowledge/review-records/review-refund-rate-approved.md
last_verified_at: 2026-06-01
sync_notes: []
maturity: query_verified
capture_trigger: review_record
source_interaction:
  - review.metric.refund_rate.monthly.v1
---

# Refund to GMV join

Join refund and GMV facts on SKU and metric date after aligning date grain.
