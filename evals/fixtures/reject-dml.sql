-- Eval fixture: must be rejected by SQL static check.
UPDATE analytics.refund_order_daily
SET refund_status = 'approved'
WHERE refund_created_at >= '2026-05-01';
