---
id: legacy.refund_rate.monthly
schema_version: 0
status: reviewed
owner: data-query-eval
reviewer: data-query-reviewer
domain: refund
metric: refund_rate
grain: month
evidence:
  - path: references/old-sql/sql/legacy-sql-0011-refund-renewal.sql
supersedes: []
conflicts_with:
  - candidate.refund_rate.order_count.v1
---

# Legacy refund rate definition

Migration eval must preserve this evidence and the conflict relationship.
