# 营期阶段 × 来源课包价格 × 购买课包价格人头数

Use this when the user asks for a report shaped like:

`月 / 营期阶段 / 来源课包价格 / 购买课包价格 / 人头数`

and clarifies that “来源课包价格” means the user's previous-stage order price, not a same-order field.

## Business definition

- Current order pool usually follows the user's base SQL:
  - `dwd_order_flow_df a1`
  - `LEFT JOIN dim_camp_df a2 ON a1.camp_id = a2.camp_id`
  - date filter on `a1.dt`
  - product filters such as `a1.cci3_name = '钢琴'` and `a1.main_goods_sku = '钢琴'`
  - `a1.pay_type_name IN ('全款','尾款')`
  - `a1.main_first_level = '课程'`
- `购买课包价格` = current order `a1.total_original_price`.
- `来源课包价格` = the previous-stage order's `total_original_price` for the same `union_id`.
- `销转营期` source price is blank.
- If the previous stage has multiple orders, use the last one before the current order time: `argMaxIf(src.purchase_price, src.pay_time, ...)`.

## Stage mapping verified locally

`dim_camp_df.class_stage / class_stage_name`:

- `0` = `销转营期`
- `2` = `二阶营期`
- `3` = `三阶营期`
- `4` = `四阶营期`
- `5` = `五阶营期`
- `6` / `9` = `特殊营期`

Previous-stage mapping:

```sql
src.class_stage = if(o.class_stage = 2, 0, o.class_stage - 1)
```

This fixes the common bug where `o.class_stage - 2` is only correct for `二阶营期 -> 销转营期`, but wrong for 三阶及以后.

## ClickHouse 21.8 implementation caveat

ClickHouse 21.8 does not allow inequality predicates in `JOIN ON`, so do not write:

```sql
LEFT JOIN source_orders src
  ON o.union_id = src.union_id
 AND src.pay_time < o.pay_time
```

Instead join only on `union_id` and put the time/stage condition inside `argMaxIf`:

```sql
argMaxIf(
    src.purchase_price,
    src.pay_time,
    src.class_stage = if(o.class_stage = 2, 0, o.class_stage - 1)
    AND src.pay_time < o.pay_time
) AS source_price
```

## Query template

```sql
WITH
current_orders AS (
    SELECT
        a1.flow_no AS flow_no,
        a1.union_id AS union_id,
        a1.camp_id AS camp_id,
        a1.pay_time AS pay_time,
        toString(toYYYYMM(toDate(a1.dt))) AS pay_month,
        a1.total_original_price AS purchase_price,
        a2.class_stage AS class_stage,
        a2.class_stage_name AS class_stage_name
    FROM dwd_order_flow_df a1
    LEFT JOIN dim_camp_df a2 ON a1.camp_id = a2.camp_id
    WHERE a1.dt >= '{start_date}'
      AND a1.dt < '{end_date_excl}'
      AND a1.pay_status_name = '支付成功'
      AND a1.cci3_name = '{cci3_name}'
      AND a1.main_goods_sku = '{main_goods_sku}'
      AND a1.pay_type_name IN ('全款','尾款')
      AND a1.main_first_level = '课程'
      AND a1.union_id != ''
),
source_orders AS (
    SELECT
        a1.flow_no AS flow_no,
        a1.union_id AS union_id,
        a1.pay_time AS pay_time,
        a1.total_original_price AS purchase_price,
        a2.class_stage AS class_stage,
        a2.class_stage_name AS class_stage_name
    FROM dwd_order_flow_df a1
    LEFT JOIN dim_camp_df a2 ON a1.camp_id = a2.camp_id
    WHERE a1.pay_status_name = '支付成功'
      AND a1.cci3_name = '{cci3_name}'
      AND a1.main_goods_sku = '{main_goods_sku}'
      AND a1.pay_type_name IN ('全款','尾款')
      AND a1.main_first_level = '课程'
      AND a1.union_id != ''
),
enriched AS (
    SELECT
        o.pay_month AS pay_month,
        o.class_stage_name AS class_stage_name,
        if(
            o.class_stage_name = '销转营期',
            NULL,
            argMaxIf(
                src.purchase_price,
                src.pay_time,
                src.class_stage = if(o.class_stage = 2, 0, o.class_stage - 1)
                AND src.pay_time < o.pay_time
            )
        ) AS source_price,
        o.purchase_price AS purchase_price,
        o.union_id AS union_id
    FROM current_orders o
    LEFT JOIN source_orders src ON o.union_id = src.union_id
    GROUP BY
        o.pay_month,
        o.class_stage_name,
        o.class_stage,
        o.pay_time,
        o.purchase_price,
        o.union_id
)
SELECT
    pay_month AS month,
    class_stage_name AS stage,
    if(isNull(source_price) OR source_price <= 0, '', toString(toInt64(round(source_price)))) AS source_package_price,
    toString(toInt64(round(purchase_price))) AS purchase_package_price,
    uniqExact(union_id) AS people_cnt
FROM enriched
GROUP BY
    month,
    stage,
    source_package_price,
    purchase_package_price
ORDER BY
    month,
    stage,
    toFloat64OrZero(source_package_price),
    toFloat64OrZero(purchase_package_price)
```

## Pitfalls from the session

- Do not treat `tock_order.goods_price` joined by current `flow_no = order_no` as 来源课包价格. That only supplements the current order and is not the user's intended previous-stage source order.
- Do not use a fixed `class_stage - 2` rule. It fails for 三阶及以后.
- The source-order CTE may need a broader date window than the current report window, because a previous-stage order may occur before the current report start date.
- Grouped `uniqExact(union_id)` can double-count the same user across month/stage/price groups by design; label the grain if reporting totals.