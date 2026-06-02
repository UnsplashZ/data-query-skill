
WITH base AS
(
    SELECT
        toStartOfMonth(pay_time) AS pay_month,
        front_end_name,
        pay_amount,
        refund_amount,
        refund_time,
        if(refund_amount > 0 AND refund_time >= toDateTime('2026-01-01 00:00:00'), dateDiff('month', toStartOfMonth(pay_time), toStartOfMonth(refund_time)), -1) AS refund_lag_m
    FROM dwd_order_flow_df
    WHERE 
pay_status_name='支付成功'
AND cci3_name='钢琴'
AND pay_time >= toDateTime('2026-01-01 00:00:00')
AND pay_time < toDateTime('2027-01-01 00:00:00')

)
SELECT
    formatDateTime(pay_month, '%Y-%m') AS pay_month,
    front_end_name,
    count() AS pay_order_cnt,
    round(sum(pay_amount), 2) AS pay_gmv,
    round(sumIf(refund_amount, refund_lag_m = 0), 2) AS refund_m0,
    round(sumIf(refund_amount, refund_lag_m = 1), 2) AS refund_m1,
    round(sumIf(refund_amount, refund_lag_m = 2), 2) AS refund_m2,
    round(sumIf(refund_amount, refund_lag_m >= 3), 2) AS refund_m3_plus,
    round(sumIf(refund_amount, refund_lag_m >= 0), 2) AS refund_cum,
    round(refund_m0 / nullIf(pay_gmv,0), 6) AS rate_m0,
    round((refund_m0 + refund_m1) / nullIf(pay_gmv,0), 6) AS rate_m0_m1,
    round((refund_m0 + refund_m1 + refund_m2) / nullIf(pay_gmv,0), 6) AS rate_m0_m2,
    round(refund_cum / nullIf(pay_gmv,0), 6) AS rate_cum
FROM base
GROUP BY pay_month, front_end_name
ORDER BY pay_month, front_end_name
