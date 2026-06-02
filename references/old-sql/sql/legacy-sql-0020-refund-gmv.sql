
/*
口径：
- 时间：2025-04-01 <= pay_time < 2026-05-01，即 2025-04 到 2026-04
- 不限制 SKU / 声乐 / 前端 / 核心课 / 课程 / 价格 / 支付类型
- 支付：pay_status_name = '支付成功'
- 支付GMV：当月支付成功订单 pay_amount 汇总
- 当月退费GMV：这些当月支付订单，在同一自然月内实际发生退款的 refund_amount 汇总
- 退款发生日：tock_dwd_order_refund_df.refund_time
*/
WITH pay_monthly AS (
    SELECT
        toStartOfMonth(pay_time) AS pay_month_start,
        count() AS pay_order_rows,
        uniqExact(flow_no) AS pay_flow_cnt,
        sum(toFloat64(pay_amount)) AS pay_gmv
    FROM dwd_order_flow_df
    WHERE pay_status_name = '支付成功'
      AND pay_time >= toDateTime('2025-04-01 00:00:00')
      AND pay_time <  toDateTime('2026-05-01 00:00:00')
    GROUP BY pay_month_start
), refund_monthly AS (
    SELECT
        toStartOfMonth(pay_time) AS pay_month_start,
        count() AS same_month_refund_rows,
        uniqExact(flow_no) AS same_month_refund_flow_cnt,
        sum(toFloat64(refund_amount)) AS same_month_refund_gmv
    FROM tock_dwd_order_refund_df
    WHERE pay_status_name = '支付成功'
      AND pay_time >= toDateTime('2025-04-01 00:00:00')
      AND pay_time <  toDateTime('2026-05-01 00:00:00')
      AND refund_time >= toStartOfMonth(pay_time)
      AND refund_time <  addMonths(toStartOfMonth(pay_time), 1)
    GROUP BY pay_month_start
)
SELECT
    formatDateTime(p.pay_month_start, '%Y-%m') AS pay_month,
    p.pay_order_rows AS pay_order_rows,
    p.pay_flow_cnt AS pay_flow_cnt,
    round(p.pay_gmv, 2) AS pay_gmv,
    ifNull(r.same_month_refund_rows, 0) AS same_month_refund_rows,
    ifNull(r.same_month_refund_flow_cnt, 0) AS same_month_refund_flow_cnt,
    round(ifNull(r.same_month_refund_gmv, 0), 2) AS same_month_refund_gmv,
    round(ifNull(r.same_month_refund_gmv, 0) / nullIf(p.pay_gmv, 0), 6) AS same_month_refund_rate
FROM pay_monthly p
LEFT JOIN refund_monthly r
    ON p.pay_month_start = r.pay_month_start
ORDER BY p.pay_month_start
