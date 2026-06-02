---
id: candidate.refund_status.approved_filter.v1
schema_version: "1.0"
status: candidate
created_by: data-query-eval
reviewed_by: ""
approved_by: ""
source_status: mock_fixture
confidence: medium
risk_level: low
domain: refund
metric: refund_status_filter
grain: order
expires_at: 2026-09-30
supersedes: []
conflicts_with: []
validation_evidence:
  - type: query_session
    path: evals/fixtures/query-session.json
last_verified_at: ""
sync_notes: []
maturity: observed
capture_trigger: query_artifact_observation
source_interaction:
  - eval-query-session-refund-2026-05
---

# Approved refund status filter candidate

This fixture must not be promoted to approved because review fields are missing.
