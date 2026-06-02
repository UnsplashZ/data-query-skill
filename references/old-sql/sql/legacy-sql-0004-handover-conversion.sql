-- handover base

SELECT
    h.class_camp_id AS target_camp_id,
    any(h.class_camp_name) AS target_camp_name,
    any(h.camp_group_name) AS target_track_name,
    any(h.class_stage_name) AS target_stage_name,
    any(d.class_stage) AS target_stage_code,
    any(d.start_class_time) AS target_start_time,
    any(d.end_class_time_bi) AS target_end_time,
    h.union_id AS union_id,
    argMin(h.flow_no, h.pay_time) AS source_flow_no,
    min(h.pay_time) AS source_pay_time
FROM dwd_order_handover_df h
LEFT JOIN dim_camp_df d ON h.class_camp_id = d.camp_id
WHERE h.sku = '钢琴'
  AND h.class_stage_name IN ('二阶营期','三阶营期','四阶营期')
  AND d.start_class_time >= toDateTime('2024-01-01 00:00:00')
  AND d.start_class_time <= today()
  AND d.start_class_time > toDateTime('2000-01-01 00:00:00')
  AND h.union_id != ''
GROUP BY target_camp_id, h.union_id


-- target order pool

SELECT
    f.flow_no AS flow_no,
    f.union_id AS union_id,
    f.pay_time AS pay_time,
    f.total_original_price AS package_price,
    f.pay_amount AS pay_amount,
    f.camp_id AS order_camp_id,
    d.class_stage AS order_stage_code,
    d.class_stage_name AS order_stage_name,
    d.camp_name AS order_camp_name,
    d.camp_sku AS order_camp_sku
FROM dwd_order_flow_df f
LEFT JOIN dim_camp_df d ON f.camp_id = d.camp_id
WHERE f.pay_status_name = '支付成功'
  AND f.main_first_level = '课程'
  AND f.main_goods_sku = '钢琴'
  AND f.pay_type_name IN ('全款','尾款')
  AND f.union_id != ''
  AND f.pay_time >= toDateTime('2023-01-01 00:00:00')


-- source flow price

SELECT
    flow_no,
    union_id,
    pay_time,
    total_original_price AS source_package_price,
    pay_amount AS source_pay_amount,
    camp_id AS source_order_camp_id,
    camp_sku AS source_order_camp_sku,
    main_goods_sku AS source_main_goods_sku
FROM dwd_order_flow_df
WHERE pay_status_name = '支付成功'
  AND main_first_level = '课程'
  AND flow_no != ''
