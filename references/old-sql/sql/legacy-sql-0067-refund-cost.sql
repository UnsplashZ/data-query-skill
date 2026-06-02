
WITH
    tail_pay AS
    (
        SELECT relate_flow_no
        FROM dwd_order_flow_df
        WHERE pay_status_name = '支付成功'
          AND pay_type_code = 2
          AND relate_flow_no != ''
        GROUP BY relate_flow_no
    ),
    live_user AS
    (
        SELECT
            union_id,
            anyLast(nick_name) AS nick_name,
            anyLast(phone) AS phone
        FROM drh_live_user FINAL
        WHERE _sign > 0
          AND union_id != ''
        GROUP BY union_id
    ),
    order_user AS
    (
        SELECT
            union_id,
            count() AS paid_order_cnt,
            sum(pay_amount) AS paid_amount,
            sum(refund_amount) AS refund_amount,
            max(refund_time) AS latest_refund_time,
            max(pay_time) AS latest_pay_time,
            groupUniqArray(camp_sku) AS paid_skus,
            groupUniqArray(main_goods_sku) AS paid_main_skus,
            max(is_official) AS has_official_order,
            sumIf(pay_amount, is_official = 1) AS official_paid_amount,
            argMax(camp_name, pay_time) AS latest_order_camp_name,
            argMax(main_goods_name, pay_time) AS latest_goods_name
        FROM dwd_order_flow_df
        WHERE pay_status_name = '支付成功'
          AND main_first_level = '课程'
          AND union_id != ''
          AND pay_time >= toDateTime('2026-01-01 00:00:00')
        GROUP BY union_id
    ),
    refund_user AS
    (
        SELECT DISTINCT union_id
        FROM dwd_order_flow_df
        WHERE pay_status_name = '支付成功'
          AND main_first_level = '课程'
          AND union_id != ''
          AND pay_time >= toDateTime('2026-01-01 00:00:00')
          AND refund_amount > 0
    ),
    first_lt1000_user AS
    (
        SELECT DISTINCT f.union_id
        FROM dwd_order_flow_df f
        LEFT JOIN tail_pay t ON f.flow_no = t.relate_flow_no
        WHERE f.pay_status_name = '支付成功'
          AND f.main_first_level = '课程'
          AND f.union_id != ''
          AND f.pay_time >= toDateTime('2026-01-01 00:00:00')
          AND f.pay_type_code = 1
          AND f.pay_amount < 1000
          AND f.refund_amount <= 0
          AND t.relate_flow_no = ''
    ),
    gt880_user AS
    (
        SELECT DISTINCT union_id
        FROM dwd_order_flow_df
        WHERE pay_status_name = '支付成功'
          AND main_first_level = '课程'
          AND union_id != ''
          AND pay_time >= toDateTime('2026-01-01 00:00:00')
          AND pay_amount > 880
          AND refund_amount <= 0
    ),
    study_30 AS
    (
        SELECT
            union_id,
            countIf(class_time >= toDateTime('2026-05-19 00:00:00') - INTERVAL 30 DAY
                    AND (study_time > 0 OR zb_study_time > 0 OR submit_cnt > 0 OR e_time_cnt > 0 OR message_cnt > 0)) AS recent_study_record_cnt,
            maxIf(class_time, class_time >= toDateTime('2026-05-19 00:00:00') - INTERVAL 30 DAY
                         AND (study_time > 0 OR zb_study_time > 0 OR submit_cnt > 0 OR e_time_cnt > 0 OR message_cnt > 0)) AS latest_study_time,
            sumIf(study_time + zb_study_time, class_time >= toDateTime('2026-05-19 00:00:00') - INTERVAL 30 DAY
                         AND (study_time > 0 OR zb_study_time > 0 OR submit_cnt > 0 OR e_time_cnt > 0 OR message_cnt > 0)) AS recent_study_minutes,
            countIf(class_time > toDateTime('1971-01-01 00:00:00') AND study_time > 0) AS all_started_class_cnt,
            minIf(class_time, class_time > toDateTime('1971-01-01 00:00:00') AND study_time > 0) AS first_started_class_time
        FROM tock_ast_process_data
        WHERE union_id != ''
        GROUP BY union_id
    ),
    complaint_user AS
    (
        SELECT
            union_id,
            max(msgtime) AS latest_complaint_time,
            count() AS complaint_msg_cnt
        FROM tock_qw_message_res
        WHERE union_id != ''
          AND match(content, '投诉|客诉|举报|315|消协|黑猫|律师|法院|起诉|报警')
        GROUP BY union_id
    ),
    service_info AS
    (
        SELECT
            union_id,
            max(service_camp_name != '') AS is_served,
            argMax(service_camp_stage, pay_time) AS latest_service_stage,
            argMax(service_camp_name, pay_time) AS latest_service_camp_name,
            argMax(service_emp_name, pay_time) AS latest_service_emp_name,
            argMax(service_emp_group_name, pay_time) AS latest_service_group_name,
            argMax(service_start_class_time, pay_time) AS latest_service_start_time,
            argMax(service_add_time, pay_time) AS latest_service_add_time,
            argMax(service_is_friend, pay_time) AS latest_service_is_friend
        FROM tock_handover_plus
        WHERE union_id != ''
          AND pay_time >= toDateTime('2026-01-01 00:00:00')
        GROUP BY union_id
    ),
    current_friend AS
    (
        SELECT
            union_id,
            emp_id,
            anyLast(emp_name) AS emp_name,
            anyLast(company) AS company,
            anyLast(belong_name) AS belong_name,
            anyLast(external_user_id) AS external_user_id,
            min(add_time) AS first_add_time,
            max(add_time) AS latest_add_time,
            max(qw_tag_name) AS qw_tag_name,
            max(emp_remark) AS emp_remark,
            max(del_time) AS latest_del_time,
            minIf(del_time, del_time > toDateTime('1971-01-01 00:00:00')) AS first_del_time,
            count() AS friend_relation_rows
        FROM tock_emp_external_user
        WHERE union_id != ''
          AND emp_id != 0
          AND (del_time IS NULL OR del_time <= toDateTime('1971-01-01 00:00:00'))
        GROUP BY union_id, emp_id
    ),
    all_friend AS
    (
        SELECT
            union_id,
            emp_id,
            anyLast(emp_name) AS emp_name,
            anyLast(company) AS company,
            anyLast(belong_name) AS belong_name,
            anyLast(external_user_id) AS external_user_id,
            min(add_time) AS first_add_time,
            max(add_time) AS latest_add_time,
            max(qw_tag_name) AS qw_tag_name,
            max(emp_remark) AS emp_remark,
            max(del_time) AS latest_del_time,
            minIf(del_time, del_time > toDateTime('1971-01-01 00:00:00')) AS first_del_time,
            count() AS friend_relation_rows,
            max(del_time IS NULL OR del_time <= toDateTime('1971-01-01 00:00:00')) AS is_current_friend
        FROM tock_emp_external_user
        WHERE union_id != ''
          AND emp_id != 0
        GROUP BY union_id, emp_id
    ),
    msg_30 AS
    (
        SELECT
            union_id,
            emp_id,
            count() AS recent_qw_msg_cnt,
            max(msgtime) AS latest_qw_msg_time,
            countIf(send_role = '员工') AS recent_emp_msg_cnt,
            countIf(send_role != '员工') AS recent_user_msg_cnt
        FROM tock_qw_message_res
        WHERE union_id != ''
          AND emp_id != 0
          AND msgtime >= toDateTime('2026-05-19 00:00:00') - INTERVAL 30 DAY
        GROUP BY union_id, emp_id
    ),
    friend_summary AS
    (
        SELECT
            union_id,
            count() AS current_friend_cnt,
            groupUniqArray(concat(company, '/', belong_name, '/', emp_name)) AS current_friend_locations
        FROM current_friend
        GROUP BY union_id
    )

SELECT
    '退费用户' AS group_name,
    ou.union_id AS union_id,
    lu.nick_name AS nick_name,
    lu.phone AS phone,
    ou.paid_order_cnt AS paid_order_cnt,
    round(ou.paid_amount, 2) AS paid_amount,
    round(ou.refund_amount, 2) AS refund_amount,
    ou.latest_refund_time AS latest_refund_time,
    arrayStringConcat(ou.paid_skus, ',') AS paid_skus,
    af.emp_id AS qw_emp_id,
    af.emp_name AS qw_emp_name,
    af.company AS qw_company,
    af.belong_name AS qw_belong_name,
    af.external_user_id AS external_user_id,
    af.first_add_time AS first_add_time,
    af.latest_add_time AS latest_add_time,
    if(af.is_current_friend = 1, '当前仍为好友', '历史好友/已删除') AS friend_status,
    af.first_del_time AS first_del_time,
    af.qw_tag_name AS qw_tag_name,
    af.emp_remark AS emp_remark
FROM refund_user ru
INNER JOIN order_user ou ON ru.union_id = ou.union_id
LEFT JOIN live_user lu ON ru.union_id = lu.union_id
LEFT JOIN all_friend af ON ru.union_id = af.union_id
ORDER BY ou.latest_refund_time DESC, ou.union_id, friend_status DESC, af.company, af.emp_name
