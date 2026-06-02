# Vocal frontend same-day cohort refund chart

Session reference for rebuilding the user's 声乐前端 cohort 退费率 chart when comparing handover optimization results.

## Correct business question

The user wanted two monthly-cohort line charts from 2025-01 to current month:

1. 声乐-前端-全部订单
2. 声乐-前端-课程-1880+-全款/尾款订单

Use:
- `cci3_name = '声乐'`
- `new_front_end_name LIKE '%前端%'`
- x-axis: 月内自然日 1-31
- one shared legend
- smoothed lines, no per-day markers
- exact predicate captions in title/footnote and workbook

## Critical correction

Do **not** compute the natural-day chart by grouping `dwd_order_flow_df.refund_amount` by `pay_time` day. That field represents the order's current accumulated refund amount. It pulls later refunds back to the original payment day, causing day 1 to look abnormally high.

Example debug finding:
- 2026-03-01 声乐前端全部订单 in `dwd_order_flow_df`:
  - GMV: `642,774`
  - current accumulated refund: `43,137.3`
  - apparent day-1 refund rate: `6.71%`
- Several high refunds for 2026-03-01 pay orders actually occurred later, such as 2026-03-24, 2026-03-28, 2026-04-08, 2026-04-09, or 2026-05-06.

## Correct same-day observation metric

For each payment month and day-of-month `d`:

```text
同日观察累计cohort退费率
= 同一支付月内截至第 d 天实际发生的退款GMV
  / 截至第 d 天该支付月累计支付GMV
```

Source split:
- denominator: `dwd_order_flow_df.pay_amount`, grouped by `pay_time` day
- numerator: `tock_dwd_order_refund_df.refund_amount`, grouped by `refund_time` day
- same payment-month refund filter:
  - `refund_time >= toStartOfMonth(pay_time)`
  - `refund_time < addMonths(toStartOfMonth(pay_time), 1)`

## SQL shape

Denominator daily GMV:

```sql
SELECT
    scope_id,
    scope_name,
    pay_month,
    day_of_month,
    count() AS order_rows,
    uniqExact(flow_no) AS flow_cnt,
    round(sum(pay_amount), 2) AS day_gmv
FROM (
    SELECT
        1 AS scope_id,
        '声乐-前端-全部订单' AS scope_name,
        formatDateTime(toStartOfMonth(pay_time), '%Y-%m') AS pay_month,
        toDayOfMonth(pay_time) AS day_of_month,
        flow_no,
        pay_amount
    FROM dwd_order_flow_df
    WHERE pay_status_name = '支付成功'
      AND pay_time >= toDateTime('2025-01-01 00:00:00')
      AND pay_time <  toDateTime('2026-06-01 00:00:00')
      AND cci3_name = '声乐'
      AND new_front_end_name LIKE '%前端%'

    UNION ALL

    SELECT
        2 AS scope_id,
        '声乐-前端-课程-1880+-全款/尾款订单' AS scope_name,
        formatDateTime(toStartOfMonth(pay_time), '%Y-%m') AS pay_month,
        toDayOfMonth(pay_time) AS day_of_month,
        flow_no,
        pay_amount
    FROM dwd_order_flow_df
    WHERE pay_status_name = '支付成功'
      AND pay_time >= toDateTime('2025-01-01 00:00:00')
      AND pay_time <  toDateTime('2026-06-01 00:00:00')
      AND cci3_name = '声乐'
      AND new_front_end_name LIKE '%前端%'
      AND main_first_level = '课程'
      AND total_original_price >= 1880
      AND pay_type_name IN ('全款', '尾款')
) base
GROUP BY scope_id, scope_name, pay_month, day_of_month
ORDER BY scope_id, pay_month, day_of_month
```

Refund daily numerator:

```sql
SELECT
    scope_id,
    scope_name,
    pay_month,
    refund_day_of_month AS day_of_month,
    count() AS refund_rows,
    uniqExact(flow_no) AS refund_flow_cnt,
    round(sum(refund_amount), 2) AS day_refund
FROM (
    SELECT
        1 AS scope_id,
        '声乐-前端-全部订单' AS scope_name,
        formatDateTime(toStartOfMonth(pay_time), '%Y-%m') AS pay_month,
        toDayOfMonth(refund_time) AS refund_day_of_month,
        flow_no,
        toFloat64(refund_amount) AS refund_amount
    FROM tock_dwd_order_refund_df
    WHERE pay_status_name = '支付成功'
      AND pay_time >= toDateTime('2025-01-01 00:00:00')
      AND pay_time <  toDateTime('2026-06-01 00:00:00')
      AND cci3_name = '声乐'
      AND new_front_end_name LIKE '%前端%'
      AND refund_time >= toStartOfMonth(pay_time)
      AND refund_time < addMonths(toStartOfMonth(pay_time), 1)

    UNION ALL

    SELECT
        2 AS scope_id,
        '声乐-前端-课程-1880+-全款/尾款订单' AS scope_name,
        formatDateTime(toStartOfMonth(pay_time), '%Y-%m') AS pay_month,
        toDayOfMonth(refund_time) AS refund_day_of_month,
        flow_no,
        toFloat64(refund_amount) AS refund_amount
    FROM tock_dwd_order_refund_df
    WHERE pay_status_name = '支付成功'
      AND pay_time >= toDateTime('2025-01-01 00:00:00')
      AND pay_time <  toDateTime('2026-06-01 00:00:00')
      AND cci3_name = '声乐'
      AND new_front_end_name LIKE '%前端%'
      AND main_first_level = '课程'
      AND total_original_price >= 1880
      AND pay_type_name IN ('全款', '尾款')
      AND refund_time >= toStartOfMonth(pay_time)
      AND refund_time < addMonths(toStartOfMonth(pay_time), 1)
) base
GROUP BY scope_id, scope_name, pay_month, day_of_month
ORDER BY scope_id, pay_month, day_of_month
```

Post-process by building a `1..31` day grid per `scope_id × pay_month`, merging denominator/refund daily rows, then computing cumulative sums in Python/pandas.

## Verified alignment values

For `cci3_name='声乐'` and `new_front_end_name LIKE '%前端%'`:

- 声乐前端全部订单:
  - 2026-03: `3.29%`
  - 2026-04: `2.90%`
- 声乐前端课程1880+全款/尾款:
  - 2026-03: `3.12%`
  - 2026-04: `2.44%`

The user interpreted the 2025-01-to-current chart as showing that April 2026 was still not low in absolute terms; it was lower than March, but high versus most 2025 months.

## Chart presentation preferences from the session

- Smooth curves are preferred for this comparison.
- Do not plot per-day dots/markers; they clutter the chart.
- Use one shared legend only.
- If extending to many months such as 2025-01 through current, widen the figure and use `tab20`; still expect some line overlap.
- Put exact filters and metric definition in the title/footnote and workbook SQL sheet.
