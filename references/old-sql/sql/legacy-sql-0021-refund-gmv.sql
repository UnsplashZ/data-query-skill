
/*
口径：
- 时间：2025-04-01 <= pay_time < 2026-05-01，即 2025-04 到 2026-04
- 声乐：cci3_name = '声乐'
- 前端：new_front_end_name LIKE '%前端%'
- 支付：pay_status_name = '支付成功'
- 支付GMV：当月支付订单 pay_amount 汇总
- 当月退费GMV：这些当月支付订单，在同一自然月内实际发生退款的 refund_amount 汇总
- 退款发生日：tock_dwd_order_refund_df.refund_time
*/
WITH pay_base AS (
    SELECT
        1 AS scope_id,
        '声乐-前端-全部订单' AS scope_name,
        toStartOfMonth(pay_time) AS pay_month_start,
        flow_no,
        toFloat64(pay_amount) AS pay_amount
    FROM dwd_order_flow_df
    WHERE pay_status_name = '支付成功'
      AND pay_time >= toDateTime('2025-04-01 00:00:00')
      AND pay_time <  toDateTime('2026-05-01 00:00:00')
      AND cci3_name = '声乐'
      AND new_front_end_name LIKE '%前端%'

    UNION ALL

    SELECT
        2 AS scope_id,
        '声乐-前端-课程-1880+-全款/尾款订单' AS scope_name,
        toStartOfMonth(pay_time) AS pay_month_start,
        flow_no,
        toFloat64(pay_amount) AS pay_amount
    FROM dwd_order_flow_df
    WHERE pay_status_name = '支付成功'
      AND pay_time >= toDateTime('2025-04-01 00:00:00')
      AND pay_time <  toDateTime('2026-05-01 00:00:00')
      AND cci3_name = '声乐'
      AND new_front_end_name LIKE '%前端%'
      AND main_first_level = '课程'
      AND total_original_price >= 1880
      AND pay_type_name IN ('全款', '尾款')
), pay_monthly AS (
    SELECT
        scope_id,
        scope_name,
        pay_month_start,
        count() AS pay_order_rows,
        uniqExact(flow_no) AS pay_flow_cnt,
        sum(pay_amount) AS pay_gmv
    FROM pay_base
    GROUP BY scope_id, scope_name, pay_month_start
), refund_base AS (
    SELECT
        1 AS scope_id,
        '声乐-前端-全部订单' AS scope_name,
        toStartOfMonth(pay_time) AS pay_month_start,
        flow_no,
        toFloat64(refund_amount) AS refund_amount
    FROM tock_dwd_order_refund_df
    WHERE pay_status_name = '支付成功'
      AND pay_time >= toDateTime('2025-04-01 00:00:00')
      AND pay_time <  toDateTime('2026-05-01 00:00:00')
      AND cci3_name = '声乐'
      AND new_front_end_name LIKE '%前端%'
      AND refund_time >= toStartOfMonth(pay_time)
      AND refund_time <  addMonths(toStartOfMonth(pay_time), 1)

    UNION ALL

    SELECT
        2 AS scope_id,
        '声乐-前端-课程-1880+-全款/尾款订单' AS scope_name,
        toStartOfMonth(pay_time) AS pay_month_start,
        flow_no,
        toFloat64(refund_amount) AS refund_amount
    FROM tock_dwd_order_refund_df
    WHERE pay_status_name = '支付成功'
      AND pay_time >= toDateTime('2025-04-01 00:00:00')
      AND pay_time <  toDateTime('2026-05-01 00:00:00')
      AND cci3_name = '声乐'
      AND new_front_end_name LIKE '%前端%'
      AND main_first_level = '课程'
      AND total_original_price >= 1880
      AND pay_type_name IN ('全款', '尾款')
      AND refund_time >= toStartOfMonth(pay_time)
      AND refund_time <  addMonths(toStartOfMonth(pay_time), 1)
), refund_monthly AS (
    SELECT
        scope_id,
        pay_month_start,
        count() AS same_month_refund_rows,
        uniqExact(flow_no) AS same_month_refund_flow_cnt,
        sum(refund_amount) AS same_month_refund_gmv
    FROM refund_base
    GROUP BY scope_id, pay_month_start
)
SELECT
    p.scope_id AS scope_id,
    p.scope_name AS scope_name,
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
    ON p.scope_id = r.scope_id
   AND p.pay_month_start = r.pay_month_start
ORDER BY p.scope_id, p.pay_month_start
