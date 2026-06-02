WITH
    tail_pay AS (
        SELECT relate_flow_no
        FROM dwd_order_flow_df
        WHERE pay_status_name = '支付成功'
          AND pay_type_code = 2
          AND pay_type_name = '尾款'
          AND relate_flow_no != ''
        GROUP BY relate_flow_no
    ),
    base AS (
        SELECT
            f.flow_no AS flow_no,
            f.union_id AS union_id,
            f.camp_id AS camp_id,
            f.pay_time AS pay_time,
            toYear(f.pay_time) AS pay_year,
            formatDateTime(toStartOfMonth(f.pay_time), '%Y-%m') AS pay_month,
            f.pay_amount AS pay_amount,
            f.refund_amount AS refund_amount,
            f.refund_time AS refund_time,
            f.camp_sku AS sku,
            f.main_goods_sku AS main_goods_sku,
            f.new_front_end_name AS frontend_backend,
            f.camp_name AS camp_name
        FROM dwd_order_flow_df f
        LEFT JOIN tail_pay t ON f.flow_no = t.relate_flow_no
        WHERE f.pay_status_name = '支付成功'
          AND f.pay_type_code = 1
          AND f.pay_type_name = '首款'
          AND f.main_first_level = '课程'
          AND f.pay_time >= toDateTime('1970-01-01 00:00:00')
          AND f.pay_time < toDateTime('2026-05-09 00:00:00')
          AND t.relate_flow_no = ''
    )
SELECT
    b.flow_no AS flow_no,
    b.union_id AS union_id,
    b.camp_id AS camp_id,
    b.pay_time AS pay_time,
    b.pay_year AS pay_year,
    b.pay_month AS pay_month,
    b.pay_amount AS pay_amount,
    b.refund_amount AS refund_amount,
    b.refund_time AS refund_time,
    b.sku AS sku,
    b.main_goods_sku AS main_goods_sku,
    b.frontend_backend AS frontend_backend,
    b.camp_name AS camp_name,
    countIf(a.class_time > toDateTime('1970-01-02 00:00:00')
            AND a.class_time >= b.pay_time
            AND a.class_time < toDateTime('2026-05-09 00:00:00')) AS class_record_cnt,
    minIf(a.class_time,
          a.class_time > toDateTime('1970-01-02 00:00:00')
          AND a.class_time >= b.pay_time
          AND a.class_time < toDateTime('2026-05-09 00:00:00')) AS first_class_time,
    maxIf(a.class_time,
          a.class_time > toDateTime('1970-01-02 00:00:00')
          AND a.class_time >= b.pay_time
          AND a.class_time < toDateTime('2026-05-09 00:00:00')) AS latest_class_time,
    sumIf(a.study_time,
          a.class_time > toDateTime('1970-01-02 00:00:00')
          AND a.class_time >= b.pay_time
          AND a.class_time < toDateTime('2026-05-09 00:00:00')) AS total_study_time,
    sumIf(a.zb_study_time,
          a.class_time > toDateTime('1970-01-02 00:00:00')
          AND a.class_time >= b.pay_time
          AND a.class_time < toDateTime('2026-05-09 00:00:00')) AS total_zb_study_time,
    countIf(a.class_time > toDateTime('1970-01-02 00:00:00')
            AND a.class_time >= b.pay_time
            AND a.class_time < toDateTime('2026-05-09 00:00:00')
            AND (a.study_time > 0 OR a.zb_study_time > 0 OR a.submit_cnt > 0 OR a.e_time_cnt > 0 OR a.message_cnt > 0)) AS active_class_record_cnt
FROM base b
LEFT JOIN tock_ast_process_data a
    ON b.union_id = a.union_id
   AND b.camp_id = a.camp_id
GROUP BY
    b.flow_no,
    b.union_id,
    b.camp_id,
    b.pay_time,
    b.pay_year,
    b.pay_month,
    b.pay_amount,
    b.refund_amount,
    b.refund_time,
    b.sku,
    b.main_goods_sku,
    b.frontend_backend,
    b.camp_name
