# 钢琴月×营期阶段×来源/购买课包价格人头数

Session: 2026-05-09

## User request

Run data from `2025-01-01` to now with columns:

- 月
- 营期阶段
- 来源课包价格
- 购买课包价格
- 人头数

User later clarified the scope:

- `cci3_name = '钢琴'`
- 商品也是钢琴 → `main_goods_sku = '钢琴'`

## Verified source mapping

Use ClickHouse.

Primary order pool:

- `dwd_order_flow_df`
- filters:
  - `pay_status_name = '支付成功'`
  - `main_first_level = '课程'`
  - `cci3_name = '钢琴'`
  - `main_goods_sku = '钢琴'`
  - `pay_time >= toDateTime('2025-01-01 00:00:00')`
  - `< next-day upper bound for current run`
  - `union_id != ''`

Fields:

- 月: `formatDateTime(toStartOfMonth(f.pay_time), '%Y-%m')`
- 购买课包价格: `dwd_order_flow_df.total_original_price`
- 营期阶段: prefer `dwd_order_handover_df.class_stage_name`, fallback `tock_order.class_stage`, fallback `dim_camp_df.class_stage_name`, else `未识别`
- 来源课包价格: `tock_order.goods_price`
- 人头数: `uniqExact(union_id)` within each group

Important discovery:

- `dwd_order_handover_df` does **not** have `package_price`; do not try to use it for 来源课包价格.
- In this run, `dwd_order_flow_df.flow_no` was unique in the filtered scope (`rows = uniqExact(flow_no)`), but still verify for future reruns.
- Sum of grouped 人头数 can exceed global users because users may appear across different month/stage/price groups. Treat each row as in-group distinct users, not a mutually-exclusive population.

## SQL shape

```sql
WITH
base AS (
    SELECT
        f.union_id AS union_id,
        f.flow_no AS flow_no,
        formatDateTime(toStartOfMonth(f.pay_time), '%Y-%m') AS pay_month,
        f.pay_time AS pay_time,
        f.camp_id AS camp_id,
        f.total_original_price AS purchase_package_price
    FROM dwd_order_flow_df f
    WHERE f.pay_status_name = '支付成功'
      AND f.main_first_level = '课程'
      AND f.cci3_name = '钢琴'
      AND f.main_goods_sku = '钢琴'
      AND f.pay_time >= toDateTime('{START}')
      AND f.pay_time < toDateTime('{END}')
      AND f.union_id != ''
),
handover AS (
    SELECT
        flow_no,
        anyIf(class_stage_name, class_stage_name != '') AS class_stage_name
    FROM dwd_order_handover_df
    WHERE flow_no != ''
    GROUP BY flow_no
),
order_detail AS (
    SELECT
        order_no,
        anyIf(class_stage, class_stage != '') AS class_stage,
        max(goods_price) AS goods_price
    FROM tock_order
    WHERE order_no != ''
    GROUP BY order_no
),
camp AS (
    SELECT
        camp_id,
        anyIf(class_stage_name, class_stage_name != '') AS camp_stage_name
    FROM dim_camp_df
    GROUP BY camp_id
),
base_enriched AS (
    SELECT
        b.pay_month AS pay_month,
        coalesce(nullIf(h.class_stage_name, ''), nullIf(o.class_stage, ''), nullIf(c.camp_stage_name, ''), '未识别') AS stage_name,
        o.goods_price AS source_package_price_raw,
        b.purchase_package_price AS purchase_package_price_raw,
        b.union_id AS union_id
    FROM base b
    LEFT JOIN handover h ON b.flow_no = h.flow_no
    LEFT JOIN order_detail o ON b.flow_no = o.order_no
    LEFT JOIN camp c ON b.camp_id = c.camp_id
)
SELECT
    pay_month,
    stage_name,
    if(source_package_price_raw > 0, toString(toInt64(round(source_package_price_raw))), '未识别') AS source_package_price,
    if(purchase_package_price_raw > 0, toString(toInt64(round(purchase_package_price_raw))), '未识别') AS purchase_package_price,
    uniqExact(union_id) AS people_cnt
FROM base_enriched
GROUP BY pay_month, stage_name, source_package_price, purchase_package_price
ORDER BY pay_month, stage_name, toFloat64OrZero(source_package_price), toFloat64OrZero(purchase_package_price)
```

## Export checks

For user-facing delivery:

1. Write `.xlsx` with Chinese headers exactly:
   - `月`
   - `营期阶段`
   - `来源课包价格`
   - `购买课包价格`
   - `人头数`
2. Include SQL and validation sheets when useful.
3. Reopen workbook with `openpyxl` and verify:
   - header order
   - row count
   - `人头数` cells are numeric integers.
4. Report the output file plus compact validation counts only.
