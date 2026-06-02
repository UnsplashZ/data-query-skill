-- Eval fixture: readonly-looking SQL that must be rejected for external read and delay risks.
SELECT
  user_id,
  url('https://example.invalid/export.csv', 'CSV', 'user_id UInt64') AS external_rows,
  sleep(1) AS delay_probe,
  quoted_file.payload
FROM analytics.refund_order_daily
LEFT JOIN `file`('/tmp/probe.csv', 'CSV', 'payload String') AS quoted_file ON 1 = 0
LEFT JOIN `system`.tables AS quoted_system ON 1 = 0
LEFT JOIN "file"('/tmp/probe.csv', 'CSV', 'payload String') AS double_quoted_file ON 1 = 0
LEFT JOIN "system".tables AS double_quoted_system ON 1 = 0
WHERE refund_created_at >= toDate('2026-05-01')
  AND refund_created_at < toDate('2026-06-01')
LIMIT 10;
