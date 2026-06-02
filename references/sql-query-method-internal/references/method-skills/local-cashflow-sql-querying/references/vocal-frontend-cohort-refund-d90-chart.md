# 声乐前端 cohort 退费率 D0-D90 曲线图

Session-derived reusable pattern for requests like:
- “声乐-前端-订单 cohort 退费率，最近半年，每个月一条线”
- “声乐-前端-课程-1880+-全款/尾款订单 cohort 退费率，逐日/90天对比”

## User-facing chart preferences learned

When producing this class of cohort refund-rate chart for Zheng:

- Prefer **smooth curves** for visual comparison.
- Use **one shared legend** for all subplots, not one legend per subplot.
- If there are many days on the x-axis, **do not draw per-day point markers**; they add visual noise.
- For D0-D90 views, label the x-axis as payment-age days, e.g. `支付后第 N 天（D0-D90）`.
- Keep the exact predicates in the chart footer / workbook SQL sheet for auditability.

## Two related but different cohort chart definitions

### 1. 月内逐日累计 view

Earlier short-window version used `dwd_order_flow_df` only:

- x-axis: `toDayOfMonth(pay_time)`
- numerator: cumulative `refund_amount` on orders paid from month start through that day
- denominator: cumulative `pay_amount` on orders paid from month start through that day
- useful for comparing same calendar-day monthly progression

### 2. D0-D90 payment-age cohort view

For “时间拉长一点，展示至多90天”, use refund detail so the x-axis is days since payment, not day-of-month.

- denominator: total cohort GMV for the payment month
- numerator at day N: refunds whose `dateDiff('day', toDate(pay_time), toDate(refund_time)) <= N`
- metric:
  - `cohort退费率 = D0-DN累计退款GMV / 该支付月cohort GMV`
- source:
  - denominator from `dwd_order_flow_df`
  - refunds from `tock_dwd_order_refund_df`

Important distinction:
- `dwd_order_flow_df.refund_amount` is convenient for month-end/order-level summaries.
- For D0-D90 curves, use `tock_dwd_order_refund_df.refund_time` to place refunds onto the payment-age axis.

## Verified predicates used in the session

Shared filters:

```sql
pay_status_name = '支付成功'
pay_time >= toDateTime('<start_month> 00:00:00')
pay_time <  toDateTime('<end_month> 00:00:00')
main_goods_sku = '声乐'
new_front_end_name LIKE '%前端%'
```

Second scope adds:

```sql
main_first_level = '课程'
total_original_price >= 1880
pay_type_name IN ('全款', '尾款')
```

Refund side adds:

```sql
refund_time >= pay_time
refund_time < now()
dateDiff('day', toDate(pay_time), toDate(refund_time)) BETWEEN 0 AND 90
```

## Reusable Python plotting pattern

- Generate a full D0-D90 grid for each `scope_id × pay_month`.
- Left join daily refund sums; fill missing days with zero.
- Compute cumulative refund by day and divide by fixed cohort GMV.
- Use `scipy.interpolate.PchipInterpolator` when available for smooth curves.
- Do not scatter actual daily points unless the user asks for them.
- Use PingFang/STHeiti font candidates on macOS.
- Export both PNG and XLSX; workbook should include:
  - `D90汇总`
  - `D0-D90明细`
  - `SQL`

## Example output script location from the session

The generated script was stored at:

```text
/Users/zheng/.hermes/scripts/cohort-refund-rate/vocal_frontend_recent_6m_charts_d90.py
```

This is a useful reference implementation, but future work should regenerate/adapt it under the relevant Hermes project folder rather than depending on this exact timestamped output.
