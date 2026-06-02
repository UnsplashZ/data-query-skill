
WITH
base AS (
    SELECT
        f.union_id AS union_id,
        f.flow_no AS flow_no,
        formatDateTime(toStartOfMonth(f.pay_time), '%Y-%m') AS pay_month,
        f.pay_time AS pay_time,
        f.camp_id AS camp_id,
        f.total_original_price AS purchase_package_price,
        f.pay_amount AS pay_amount
    FROM dwd_order_flow_df f
    WHERE f.pay_status_name = '支付成功'
      AND f.main_first_level = '课程'
      AND f.cci3_name = '钢琴'
      AND f.main_goods_sku = '钢琴'
      AND f.pay_time >= toDateTime('2025-01-01 00:00:00')
      AND f.pay_time < toDateTime('2026-05-10 00:00:00')
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
GROUP BY
    pay_month,
    stage_name,
    source_package_price,
    purchase_package_price
ORDER BY
    pay_month,
    stage_name,
    toFloat64OrZero(source_package_price),
    toFloat64OrZero(purchase_package_price)
