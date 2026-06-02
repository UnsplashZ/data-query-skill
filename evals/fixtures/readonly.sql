-- Eval fixture: readonly ClickHouse query with explicit time range, grain, and limit.
SELECT
  toDate(refund_created_at) AS refund_date,
  sku_name,
  count() AS refund_order_count,
  sum(refund_amount) AS refund_amount
FROM analytics.refund_order_daily
WHERE refund_created_at >= toDate('2026-05-01')
  AND refund_created_at < toDate('2026-06-01')
  AND refund_status = 'approved'
GROUP BY
  refund_date,
  sku_name
ORDER BY refund_date ASC, sku_name ASC
LIMIT 100;
