
WITH
    toDate('2025-04-01') AS start_date,
    toStartOfMonth(today()) AS current_month,
    months AS (
        SELECT addMonths(toDate('2025-04-01'), number) AS month_start
        FROM system.numbers
        LIMIT dateDiff('month', toDate('2025-04-01'), addMonths(toStartOfMonth(today()), 1))
    ),
    gmv AS (
        SELECT
            toStartOfMonth(pay_time) AS month_start,
            toFloat64(sum(pay_amount)) AS gmv_amount,
            uniqExact(flow_no) AS paid_order_cnt
        FROM dwd_order_flow_df
        WHERE pay_time >= toDateTime('2025-04-01 00:00:00')
          AND pay_time < addMonths(toStartOfMonth(today()), 1)
          AND pay_status_name = '支付成功'
        GROUP BY month_start
    ),
    refund AS (
        SELECT
            toStartOfMonth(refund_time) AS month_start,
            toFloat64(sum(refund_amount)) AS refund_amount,
            uniqExact(flow_no) AS refund_order_cnt
        FROM tock_dwd_order_refund_df
        WHERE refund_time >= toDateTime('2025-04-01 00:00:00')
          AND refund_time < addMonths(toStartOfMonth(today()), 1)
        GROUP BY month_start
    )
SELECT
    formatDateTime(m.month_start, '%Y-%m') AS month_str,
    round(ifNull(g.gmv_amount, 0), 2) AS gmv_amount,
    round(ifNull(r.refund_amount, 0), 2) AS refund_amount,
    round(if(ifNull(g.gmv_amount, 0) = 0, 0, ifNull(r.refund_amount, 0) / g.gmv_amount), 4) AS refund_rate,
    ifNull(g.paid_order_cnt, 0) AS paid_order_cnt,
    ifNull(r.refund_order_cnt, 0) AS refund_order_cnt
FROM months m
LEFT JOIN gmv g ON m.month_start = g.month_start
LEFT JOIN refund r ON m.month_start = r.month_start
ORDER BY m.month_start
