
SELECT
    formatDateTime(toStartOfMonth(r.refund_time), '%Y-%m') AS refund_month,
    formatDateTime(toStartOfMonth(r.pay_time), '%Y-%m') AS pay_month,
    r.refund_time AS refund_time,
    r.pay_time AS pay_time,
    r.flow_no AS flow_no,
    r.collect_order_no AS collect_order_no,
    r.union_id AS union_id,
    r.refund_student AS refund_student,
    r.user_phone AS user_phone,
    r.pay_type_name AS pay_type_name,
    r.cci3_name AS cci3_name,
    r.new_front_end_name AS new_front_end_name,
    ifNull(nullIf(d.class_stage_name, ''), '未匹配营期阶段') AS class_stage_name,
    ifNull(nullIf(d.camp_group_name, ''), '') AS camp_group_name,
    r.camp_id AS camp_id,
    r.camp_name AS camp_name,
    r.camp_sku AS camp_sku,
    r.main_goods_sku AS main_goods_sku,
    r.main_first_level AS main_first_level,
    r.main_second_level AS main_second_level,
    multiIf(
        r.main_first_level = '课程', '课程续费',
        r.main_first_level = '电商', '电商',
        r.main_first_level = '权益' AND (
            r.main_second_level IN ('文旅长线', '合作团', '自营团', '同城聚', '同城社团')
            OR r.main_goods_name LIKE '%游%'
            OR r.main_goods_name LIKE '%旅%'
            OR r.main_goods_name LIKE '%音乐节%'
            OR r.main_goods_name LIKE '%金色大厅%'
            OR r.main_goods_name LIKE '%南极%'
            OR r.main_goods_name LIKE '%俄罗斯%'
            OR r.main_goods_name LIKE '%春晚%'
        ), '文旅/活动权益',
        r.main_first_level = '权益', '权益其他',
        concat(ifNull(nullIf(r.main_first_level, ''), '未分类'), '-', ifNull(nullIf(r.main_second_level, ''), '未分类'))
    ) AS business_type,
    r.main_goods_id AS main_goods_id,
    r.main_goods_name AS main_goods_name,
    toFloat64(r.total_original_price) AS total_original_price,
    toFloat64(r.pay_amount) AS pay_amount,
    toFloat64(r.refund_amount) AS refund_amount,
    toFloat64(r.net_income) AS net_income,
    r.pay_status_name AS pay_status_name,
    dateDiff('day', toDate(r.pay_time), toDate(r.refund_time)) AS pay_to_refund_days,
    r.refund_reason AS refund_reason,
    r.refund_reason_detail AS refund_reason_detail,
    r.is_retention_attempted AS is_retention_attempted,
    r.retention_method AS retention_method,
    r.retention_info AS retention_info,
    r.order_emp_id AS order_emp_id,
    r.order_emp_name AS order_emp_name,
    r.channel_emp_id AS channel_emp_id,
    r.channel_emp_name AS channel_emp_name,
    r.emp_group_name AS emp_group_name,
    r.emp_team_name AS emp_team_name,
    r.in_class_name AS in_class_name,
    r.order_source_name AS order_source_name
FROM tock_dwd_order_refund_df r
LEFT JOIN dim_camp_df d ON r.camp_id = d.camp_id
WHERE r.refund_time >= toDateTime('2026-01-01 00:00:00')
  AND r.refund_time < today() + 1
  AND r.cci3_name = '声乐'
  AND r.new_front_end_name LIKE '%后端%'
  AND r.refund_amount > 0
ORDER BY r.refund_time DESC, r.flow_no
