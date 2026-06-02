-- Eval fixture: readonly but risky because no explicit time range is present.
SELECT
  sku_name,
  sum(refund_amount) AS refund_amount
FROM analytics.refund_order_daily
GROUP BY sku_name
LIMIT 20;
