# Query Brief

- Request: 统计示例商品近 7 天支付订单数。
- Owner / audience: demo analyst
- Result use: offline fixture
- Output path: evals/output/demo-orders.csv

## Business Question

- 近 7 天每日支付订单数是否稳定。

## Metric / Entity

- Metric: paid_order_count

## Scope

- Time range: 2026-05-01 to 2026-05-07
- Time field: paid_at
- Grain: day
- Filters: status = 'paid'
- Dimensions: dt

## Candidate Sources

| source | status | why considered | risk |
| --- | --- | --- | --- |
| demo.orders | observed | contains order payment status | fixture only |

## Assumptions

- paid_order_count counts distinct order_id after status = paid.

## SQL

```sql
select date(paid_at) as dt, count(distinct order_id) as paid_order_count
from demo.orders
where paid_at >= '2026-05-01' and paid_at < '2026-05-08'
  and status = 'paid'
group by 1
```
