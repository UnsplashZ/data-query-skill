
WITH
orders AS (
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
    WHERE a1.dt >= '2025-01-01'
      AND a1.dt < '2026-05-10'
      AND a1.pay_status_name = '支付成功'
      AND a1.cci3_name = '钢琴'
      AND a1.main_goods_sku = '钢琴'
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
            argMaxIf(src.purchase_price, src.pay_time, src.class_stage = o.class_stage - 2 AND src.pay_time < o.pay_time)
        ) AS source_price,
        o.purchase_price AS purchase_price,
        o.union_id AS union_id
    FROM orders o
    LEFT JOIN orders src ON o.union_id = src.union_id
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
