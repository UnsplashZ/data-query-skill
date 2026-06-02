
SELECT
  formatDateTime(toStartOfMonth(pay_time),'%Y-%m') AS pay_month,
  formatDateTime(toStartOfMonth(refund_time),'%Y-%m') AS refund_month,
  dateDiff('month', toStartOfMonth(pay_time), toStartOfMonth(refund_time)) AS refund_lag_m,
  front_end_name,
  new_front_end_name,
  flow_no,
  union_id,
  main_goods_name,
  main_goods_sku,
  camp_name,
  camp_sku,
  pay_type_name,
  pay_amount,
  pay_time,
  refund_amount,
  refund_time,
  refund_student,
  refund_reason,
  refund_reason_detail,
  order_source_name
FROM tock_dwd_order_refund_df
WHERE cci3_name='钢琴'
  AND pay_status_name='支付成功'
  AND pay_time>=toDateTime('2026-01-01 00:00:00')
  AND pay_time<toDateTime('2027-01-01 00:00:00')
  AND refund_amount>0
ORDER BY pay_time, refund_time
