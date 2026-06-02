
    WITH
      front_orders AS (
        SELECT
          flow_no, relate_flow_no, union_id, pay_time, pay_type_code, pay_type_name,
          camp_id, camp_name, camp_sku, main_goods_id, main_goods_name, main_goods_sku,
          main_first_level, main_second_level, total_original_price, pay_amount, refund_amount,
          refund_time, is_official, order_source_name, front_end_name, new_front_end_name
        FROM dwd_order_flow_df
        WHERE pay_status_name = '支付成功'
          AND new_front_end_name = '大前端'
          AND main_first_level = '课程'
          AND union_id != ''
          AND pay_time >= toDateTime('2026-01-01 00:00:00')
      ),
      tail_pay AS (
        SELECT relate_flow_no
        FROM dwd_order_flow_df
        WHERE pay_status_name = '支付成功'
          AND pay_type_code = 2
          AND relate_flow_no != ''
        GROUP BY relate_flow_no
      )
    SELECT
      o.flow_no AS flow_no,
      o.relate_flow_no AS relate_flow_no,
      o.union_id AS union_id,
      o.pay_time AS pay_time,
      o.pay_type_code AS pay_type_code,
      o.pay_type_name AS pay_type_name,
      o.camp_id AS camp_id,
      o.camp_name AS camp_name,
      o.camp_sku AS camp_sku,
      o.main_goods_id AS main_goods_id,
      o.main_goods_name AS main_goods_name,
      o.main_goods_sku AS main_goods_sku,
      o.main_second_level AS main_second_level,
      round(o.total_original_price, 2) AS total_original_price,
      round(o.pay_amount, 2) AS pay_amount,
      round(o.refund_amount, 2) AS refund_amount,
      o.refund_time AS refund_time,
      o.is_official AS order_is_official,
      o.order_source_name AS order_source_name,
      o.front_end_name AS front_end_name,
      o.new_front_end_name AS new_front_end_name,
      if(o.refund_amount > 0, 1, 0) AS is_refund_order,
      if(o.pay_type_code = 1 AND o.pay_amount < 1000 AND o.refund_amount <= 0 AND ifNull(t.relate_flow_no, '') = '', 1, 0) AS is_first_lt1000_no_tail_order,
      if(o.pay_amount > 880 AND o.refund_amount <= 0, 1, 0) AS is_gt880_noref_order
    FROM front_orders o
    LEFT JOIN tail_pay t ON o.flow_no = t.relate_flow_no
    WHERE o.refund_amount > 0
       OR (o.pay_type_code = 1 AND o.pay_amount < 1000 AND o.refund_amount <= 0 AND ifNull(t.relate_flow_no, '') = '')
       OR (o.pay_amount > 880 AND o.refund_amount <= 0)
    