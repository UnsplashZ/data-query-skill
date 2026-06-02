WITH base AS (
    SELECT
        a.flow_no,
        a.union_id,
        a.main_goods_sku AS goods_sku,
        toStartOfMonth(a.pay_time) AS pay_month,
        a.pay_time,
        a.studio_lv2 AS channel_type,
        a.channel_emp_name AS channel_emp_name
    FROM dwd_order_flow_df a
    LEFT JOIN (select * from drh_live_camp final where _sign > 0) c ON a.camp_id = c.id
    WHERE a.pay_time >= toDateTime('2025-01-01 00:00:00')
      AND a.pay_amount > 0
      AND a.pay_type_name IN ('全款', '尾款')
      AND a.new_front_end_name LIKE '%前端%'
      AND c.is_class = 0
      AND a.main_goods_sku = '钢琴'
),
second_orders AS (
    SELECT
        a.flow_no AS second_flow_no,
        a.union_id,
        a.camp_sku AS camp_sku,
        a.pay_time AS second_pay_time,
        a.pay_amount AS second_pay_amount
    FROM dwd_order_flow_df a
    LEFT JOIN (select * from drh_live_camp final where _sign > 0) c ON a.camp_id = c.id
    WHERE a.pay_time >= toDateTime('2025-01-01 00:00:00')
      AND a.pay_amount > 0
      AND a.pay_type_name IN ('全款', '尾款')
      AND c.is_class = 1
      AND c.class_stage = 2
),
base_flag AS (
    SELECT
        b.flow_no,
        formatDateTime(b.pay_month, '%Y-%m') AS pay_month_str,
        ifNull(nullIf(b.channel_type, ''), '未分类') AS channel_type_norm,
        ifNull(nullIf(b.channel_emp_name, ''), '未分类') AS channel_emp_name_norm,
        max(
            if(
                s.second_pay_time > b.pay_time
                AND s.camp_sku = b.goods_sku,
                1,
                0
            )
        ) AS renewed_flag,
        sumIf(
            s.second_pay_amount,
            s.second_pay_time > b.pay_time
            AND s.camp_sku = b.goods_sku
        ) AS renewal_gmv
    FROM base b
    LEFT JOIN second_orders s
      ON b.union_id = s.union_id
    GROUP BY
        b.flow_no,
        pay_month_str,
        channel_type_norm,
        channel_emp_name_norm
)
SELECT
    pay_month_str AS `支付自然月`,
    channel_type_norm AS `渠道聚合类型`,
    channel_emp_name_norm AS `投手`,
    count() AS `销转订单数`,
    sum(renewed_flag) AS `续费订单数`,
    sum(renewal_gmv) AS `续费GMV`,
    round(sum(renewed_flag) / count(), 6) AS `续费率`
FROM base_flag
GROUP BY
    pay_month_str,
    channel_type_norm,
    channel_emp_name_norm
ORDER BY
    pay_month_str,
    channel_type_norm,
    channel_emp_name_norm;
