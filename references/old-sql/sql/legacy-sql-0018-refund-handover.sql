WITH
drh_valid AS (
    SELECT
        order_no,
        anyIf(union_id, union_id != '') AS union_id,
        max(stop_study_status) AS stop_study_status,
        anyIf(stop_hand_emp, stop_hand_emp != '') AS stop_hand_emp,
        anyIf(class_camp_name, class_camp_name != '') AS class_camp_name
    FROM (
        SELECT *
        FROM drh_handover_plus FINAL
        WHERE _sign > 0
    )
    WHERE order_no != ''
    GROUP BY order_no
),
hp AS (
    SELECT
        t.order_no AS flow_no,
        anyIf(d.union_id, d.union_id != '') AS union_id_hp,
        max(if(
            d.stop_study_status = 1
            OR t.service_camp_name LIKE '%休学%'
            OR t.service_camp_name LIKE '%冻课%'
            OR t.service_camp_name LIKE '%延期%',
            1,
            0
        )) AS stop_freeze_flag_hp,
        minIf(t.stop_study_time, d.stop_study_status = 1 AND t.stop_study_time > toDateTime('1970-01-02 00:00:00')) AS first_rest_time,
        maxIf(t.stop_study_time, d.stop_study_status = 1 AND t.stop_study_time > toDateTime('1970-01-02 00:00:00')) AS latest_rest_time,
        anyIf(d.stop_hand_emp, d.stop_study_status = 1 AND d.stop_hand_emp != '') AS rest_operator,
        anyIf(coalesce(nullIf(t.service_camp_name, ''), d.class_camp_name), coalesce(nullIf(t.service_camp_name, ''), d.class_camp_name) != '') AS hp_class_camp_name,
        anyIf(t.service_camp_name, t.service_camp_name LIKE '%休学%' OR t.service_camp_name LIKE '%冻课%' OR t.service_camp_name LIKE '%延期%') AS keyword_class_camp_name
    FROM tock_handover_plus t
    LEFT JOIN drh_valid d ON t.order_no = d.order_no
    WHERE t.order_no != ''
      AND (
          d.stop_study_status = 1
          OR t.service_camp_name LIKE '%休学%'
          OR t.service_camp_name LIKE '%冻课%'
          OR t.service_camp_name LIKE '%延期%'
      )
    GROUP BY t.order_no
),
sr AS (
    SELECT
        order_no AS flow_no,
        anyIf(union_id, union_id != '') AS union_id_sr,
        max(if(stop_flag = 1, 1, 0)) AS stop_freeze_flag_sr,
        min(stop_time) AS first_freeze_time,
        max(stop_time) AS latest_freeze_time,
        count() AS freeze_record_cnt,
        anyIf(type, type != '') AS freeze_source,
        anyIf(nick_name, nick_name != '') AS nick_name,
        anyIf(camp_name, camp_name != '') AS freeze_camp_name,
        anyIf(sku, sku != '') AS freeze_sku
    FROM dev_stop_stu_record
    WHERE stop_flag = 1
      AND order_no != ''
      AND stop_time >= toDateTime('1970-01-01 00:00:00')
      AND stop_time < toDateTime('2026-05-09 00:00:00')
    GROUP BY order_no
),
flags AS (
    SELECT
        hp.flow_no AS flow_no,
        hp.union_id_hp AS union_id_flag,
        hp.stop_freeze_flag_hp AS stop_freeze_flag,
        hp.first_rest_time AS first_rest_time,
        hp.latest_rest_time AS latest_rest_time,
        hp.rest_operator AS rest_operator,
        toDateTime('1970-01-01 00:00:00') AS first_freeze_time,
        toDateTime('1970-01-01 00:00:00') AS latest_freeze_time,
        0 AS freeze_record_cnt,
        '' AS freeze_source,
        '' AS nick_name,
        '' AS freeze_camp_name,
        '' AS freeze_sku,
        hp.hp_class_camp_name AS hp_class_camp_name,
        hp.keyword_class_camp_name AS keyword_class_camp_name,
        if(hp.keyword_class_camp_name != '', 1, 0) AS keyword_hit_flag
    FROM hp
),
flow AS (
    SELECT
        flow_no,
        any(union_id) AS union_id2,
        any(pay_time) AS pay_time2,
        any(toYear(pay_time)) AS pay_year2,
        sum(pay_amount) AS pay_amount2,
        sum(refund_amount) AS refund_amount2,
        max(refund_time) AS refund_time2,
        any(camp_sku) AS sku2,
        any(main_goods_sku) AS main_goods_sku2,
        any(new_front_end_name) AS frontend_backend2,
        any(camp_name) AS camp_name2,
        any(main_first_level) AS main_first_level2,
        any(pay_status_name) AS pay_status_name2
    FROM dwd_order_flow_df
    WHERE pay_time >= toDateTime('1970-01-01 00:00:00')
      AND pay_time < toDateTime('2026-05-09 00:00:00')
      AND main_first_level = '课程'
      AND pay_status_name = '支付成功'
    GROUP BY flow_no
),
handover_track AS (
    SELECT
        flow_no,
        anyIf(camp_group_name, camp_group_name != '') AS class_camp_group_name
    FROM dwd_order_handover_df
    WHERE flow_no != ''
    GROUP BY flow_no
)
SELECT
    flags.flow_no AS flow_no,
    coalesce(flow.union_id2, flags.union_id_flag) AS union_id,
    flow.pay_time2 AS pay_time,
    flow.pay_year2 AS pay_year,
    flow.pay_amount2 AS pay_amount,
    flow.refund_amount2 AS refund_amount,
    flow.refund_time2 AS refund_time,
    flow.sku2 AS sku,
    flow.main_goods_sku2 AS main_goods_sku,
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
    flags.nick_name AS nick_name,
    flags.freeze_camp_name AS freeze_camp_name,
    flags.freeze_sku AS freeze_sku,
    flags.hp_class_camp_name AS hp_class_camp_name,
    handover_track.class_camp_group_name AS class_camp_group_name,
    flags.keyword_class_camp_name AS keyword_class_camp_name,
    if(flow.flow_no != '', 1, 0) AS matched_paid_course_order
FROM flags
LEFT JOIN flow ON flags.flow_no = flow.flow_no
LEFT JOIN handover_track ON flags.flow_no = handover_track.flow_no
WHERE flags.stop_freeze_flag = 1
