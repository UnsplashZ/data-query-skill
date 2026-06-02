
SELECT
    formatDateTime(toStartOfMonth(f.pay_time), '%Y-%m') AS pay_month,
    f.pay_time AS pay_time,
    f.flow_no AS flow_no,
    f.collect_order_no AS collect_order_no,
    f.union_id AS union_id,
    f.pay_type_name AS pay_type_name,
    f.cci3_name AS cci3_name,
    f.new_front_end_name AS new_front_end_name,
    ifNull(nullIf(d.class_stage_name, ''), '未匹配营期阶段') AS class_stage_name,
    ifNull(nullIf(d.camp_group_name, ''), '') AS camp_group_name,
    f.camp_id AS camp_id,
    f.camp_name AS camp_name,
    f.camp_sku AS camp_sku,
    f.main_goods_sku AS main_goods_sku,
    f.main_first_level AS main_first_level,
    f.main_second_level AS main_second_level,
    multiIf(
        f.main_first_level = '课程', '课程续费',
        f.main_first_level = '电商', '电商',
        f.main_first_level = '权益' AND (
            f.main_second_level IN ('文旅长线', '合作团', '自营团', '同城聚', '同城社团')
            OR f.main_goods_name LIKE '%游%'
            OR f.main_goods_name LIKE '%旅%'
            OR f.main_goods_name LIKE '%音乐节%'
            OR f.main_goods_name LIKE '%金色大厅%'
            OR f.main_goods_name LIKE '%南极%'
            OR f.main_goods_name LIKE '%俄罗斯%'
            OR f.main_goods_name LIKE '%春晚%'
        ), '文旅/活动权益',
        f.main_first_level = '权益', '权益其他',
        concat(ifNull(nullIf(f.main_first_level, ''), '未分类'), '-', ifNull(nullIf(f.main_second_level, ''), '未分类'))
    ) AS business_type,
    f.main_goods_id AS main_goods_id,
    f.main_goods_name AS main_goods_name,
    f.total_original_price AS total_original_price,
    f.pay_amount AS pay_amount,
    f.refund_amount AS refund_amount,
    f.net_received_amount AS net_received_amount,
    f.pay_status_name AS pay_status_name,
    f.refund_time AS refund_time,
    f.order_emp_id AS order_emp_id,
    f.order_emp_name AS order_emp_name,
    f.channel_emp_id AS channel_emp_id,
    f.channel_emp_name AS channel_emp_name,
    f.emp_group_name AS emp_group_name,
    f.emp_team_name AS emp_team_name,
    f.in_class_name AS in_class_name,
    f.order_source_name AS order_source_name,
    f.pay_source AS pay_source,
    f.rev_type_name AS rev_type_name
FROM dwd_order_flow_df f
LEFT JOIN dim_camp_df d ON f.camp_id = d.camp_id
WHERE f.pay_time >= toDateTime('2026-01-01 00:00:00')
  AND f.pay_time < today() + 1
  AND f.cci3_name = '声乐'
  AND f.new_front_end_name LIKE '%后端%'
  AND f.pay_status_name = '支付成功'
ORDER BY f.pay_time DESC, f.flow_no
