---
id: golden_query.refund_rate.monthly.v1
schema_version: "1.0"
status: reviewed
created_by: data-query-eval
reviewed_by: data-query-reviewer
approved_by: ""
source_status: mock_fixture
confidence: medium
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
maturity: query_verified
capture_trigger: verified_result_summary
source_interaction:
  - evals/fixtures/readonly.sql
---

# Monthly refund query pattern

```sql
SELECT toStartOfMonth(refund_created_at) AS refund_month, sku_name, sum(refund_amount)
FROM analytics.refund_order_daily
WHERE refund_created_at >= toDate('2026-05-01')
  AND refund_created_at < toDate('2026-06-01')
GROUP BY refund_month, sku_name
LIMIT 100;
```
