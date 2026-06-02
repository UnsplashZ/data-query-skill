WITH
drh_valid AS (
    SELECT
        order_no,
        anyIf(union_id, union_id != '') AS union_id,
        max(stop_study_status) AS stop_study_status,
        anyIf(stop_hand_emp, stop_hand_emp != '') AS stop_hand_emp,
        anyIf(class_camp_name, class_camp_name != '') AS drh_class_camp_name
    FROM (
        SELECT *
        FROM drh_handover_plus FINAL
        WHERE _sign > 0
    )
    WHERE order_no != ''
      AND ifNull(class_camp_name, '') != ''
    GROUP BY order_no
),
stop_study_user AS (
    SELECT
        t.order_no AS flow_no,
        coalesce(nullIf(anyIf(t.union_id, t.union_id != ''), ''), anyIf(d.union_id, d.union_id != '')) AS union_id,
        minIf(t.stop_study_time, t.stop_study_time > toDateTime('1970-01-02 00:00:00')) AS first_rest_time,
        maxIf(t.stop_study_time, t.stop_study_time > toDateTime('1970-01-02 00:00:00')) AS latest_rest_time,
        anyIf(d.stop_hand_emp, d.stop_hand_emp != '') AS rest_operator,
        anyIf(coalesce(nullIf(t.service_camp_name, ''), d.drh_class_camp_name), coalesce(nullIf(t.service_camp_name, ''), d.drh_class_camp_name) != '') AS hp_class_camp_name,
        anyIf(t.service_camp_name, multiMatchAny(t.service_camp_name, ['冻课', '休学', '延期'])) AS keyword_class_camp_name
    FROM tock_handover_plus t
    LEFT JOIN drh_valid d ON t.order_no = d.order_no
    WHERE t.order_no != ''
      AND (
          multiMatchAny(t.service_camp_name, ['冻课', '休学', '延期'])
          OR d.stop_study_status = 1
       )
    GROUP BY t.order_no
),
stop_study_flag AS (
    SELECT
        flow_no,
        union_id,
        '休学' AS flag,
        1 AS stop_freeze_flag,
        1 AS keyword_hit_flag,
        first_rest_time,
        latest_rest_time,
        rest_operator,
        toDateTime('1970-01-01 00:00:00') AS first_freeze_time,
        toDateTime('1970-01-01 00:00:00') AS latest_freeze_time,
        0 AS freeze_record_cnt,
        'tock_handover_plus/drh_handover_plus' AS freeze_source,
        hp_class_camp_name,
        keyword_class_camp_name
    FROM stop_study_user
),
handover_order AS (
    SELECT order_no
    FROM tock_handover_plus
    WHERE order_no != ''
    GROUP BY order_no
),
no_handover_user AS (
    SELECT
        order_no AS flow_no,
        anyIf(union_id, union_id != '') AS union_id,
        anyIf(service_camp_name, service_camp_name != '') AS hp_class_camp_name
    FROM tock_handover_plus
    WHERE order_no != ''
      AND service_camp_name = ''
      AND service_emp_name = ''
      AND order_no NOT IN (
          SELECT flow_no
          FROM stop_study_flag
      )
    GROUP BY order_no
),
no_handover_flag AS (
    SELECT
        flow_no,
        anyIf(union_id, union_id != '') AS union_id,
        '未分配' AS flag,
        0 AS stop_freeze_flag,
        0 AS keyword_hit_flag,
        toDateTime('1970-01-01 00:00:00') AS first_rest_time,
        toDateTime('1970-01-01 00:00:00') AS latest_rest_time,
        '' AS rest_operator,
        toDateTime('1970-01-01 00:00:00') AS first_freeze_time,
        toDateTime('1970-01-01 00:00:00') AS latest_freeze_time,
        0 AS freeze_record_cnt,
        'tock_handover_plus' AS freeze_source,
        anyIf(hp_class_camp_name, hp_class_camp_name != '') AS hp_class_camp_name,
        '' AS keyword_class_camp_name
    FROM no_handover_user
    GROUP BY flow_no
),
flags AS (
    SELECT * FROM stop_study_flag
    UNION ALL
    SELECT * FROM no_handover_flag
),
flow AS (
    SELECT
        flow_no,
        anyIf(union_id, union_id != '') AS union_id2,
        min(pay_time) AS pay_time2,
        toYear(min(pay_time)) AS pay_year2,
        sum(pay_amount) AS pay_amount2,
        sum(refund_amount) AS refund_amount2,
        max(refund_time) AS refund_time2,
        anyIf(camp_sku, camp_sku != '') AS sku2,
        anyIf(main_goods_sku, main_goods_sku != '') AS main_goods_sku2,
        anyIf(main_goods_name, main_goods_name != '') AS main_goods_name2,
        anyIf(new_front_end_name, new_front_end_name != '') AS frontend_backend2,
        anyIf(camp_name, camp_name != '') AS camp_name2,
        anyIf(order_emp_name, order_emp_name != '') AS order_emp_name2,
        max(total_original_price) AS total_original_price2
    FROM dwd_order_flow_df
    WHERE pay_time >= toDateTime('1970-01-01 00:00:00')
      AND pay_time < toDateTime('2026-05-09 00:00:00')
      AND main_first_level = '课程'
      AND pay_status_name = '支付成功'
    GROUP BY flow_no
),
handover_detail AS (
    SELECT
        flow_no,
        anyIf(camp_group_name, camp_group_name != '') AS class_camp_group_name,
        anyIf(ast_emp_name, ast_emp_name != '') AS ast_emp_name,
        anyIf(class_stage_name, class_stage_name != '') AS class_stage_name
    FROM dwd_order_handover_df
    WHERE flow_no != ''
    GROUP BY flow_no
),
order_detail AS (
    SELECT
        order_no,
        anyIf(union_id, union_id != '') AS union_id3,
        anyIf(emp_name, emp_name != '') AS emp_name,
        anyIf(goods_name, goods_name != '') AS goods_name,
        max(goods_price) AS goods_price,
        anyIf(class_stage, class_stage != '') AS class_stage
    FROM tock_order
    WHERE order_no != ''
    GROUP BY order_no
),
applet_user AS (
    SELECT
        union_id,
        argMax(nick_name, create_time) AS nick_name,
        argMaxIf(phone, create_time, phone != '') AS phone
    FROM tock_applet_user
    WHERE union_id != ''
    GROUP BY union_id
)
SELECT
    flags.flow_no AS flow_no,
    coalesce(nullIf(flow.union_id2, ''), nullIf(flags.union_id, ''), order_detail.union_id3) AS union_id,
    flow.pay_time2 AS pay_time,
    flow.pay_year2 AS pay_year,
    flow.pay_amount2 AS pay_amount,
    flow.refund_amount2 AS refund_amount,
    flow.refund_time2 AS refund_time,
    flow.sku2 AS sku,
    flow.main_goods_sku2 AS main_goods_sku,
    coalesce(nullIf(flow.main_goods_name2, ''), order_detail.goods_name) AS main_goods_name,
    flow.frontend_backend2 AS frontend_backend,
    flow.camp_name2 AS camp_name,
    flags.stop_freeze_flag AS stop_freeze_flag,
    flags.keyword_hit_flag AS keyword_hit_flag,
    flags.first_rest_time AS first_rest_time,
    flags.latest_rest_time AS latest_rest_time,
    flags.rest_operator AS rest_operator,
    flags.first_freeze_time AS first_freeze_time,
    flags.latest_freeze_time AS latest_freeze_time,
    flags.freeze_record_cnt AS freeze_record_cnt,
    flags.freeze_source AS freeze_source,
    applet_user.nick_name AS nick_name,
    applet_user.phone AS phone,
    flags.hp_class_camp_name AS freeze_camp_name,
    flow.sku2 AS freeze_sku,
    flags.hp_class_camp_name AS hp_class_camp_name,
    handover_detail.class_camp_group_name AS class_camp_group_name,
    flags.keyword_class_camp_name AS keyword_class_camp_name,
    if(flow.flow_no != '', 1, 0) AS matched_paid_course_order,
    flags.flag AS flag,
    coalesce(nullIf(flow.order_emp_name2, ''), order_detail.emp_name) AS deal_emp_name,
    handover_detail.ast_emp_name AS ast_emp_name,
    if(flow.total_original_price2 > 0, flow.total_original_price2, order_detail.goods_price) AS package_price,
    coalesce(nullIf(handover_detail.class_stage_name, ''), order_detail.class_stage) AS deal_camp_stage
FROM flags
LEFT JOIN flow ON flags.flow_no = flow.flow_no
LEFT JOIN handover_detail ON flags.flow_no = handover_detail.flow_no
LEFT JOIN order_detail ON flags.flow_no = order_detail.order_no
LEFT JOIN applet_user ON coalesce(nullIf(flow.union_id2, ''), nullIf(flags.union_id, ''), order_detail.union_id3) = applet_user.union_id
