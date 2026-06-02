SELECT
    c.order_no,
    c.union_id,
    c.goods_id,
    c.price / 100.0 AS amount_yuan,
    c.pay_time,
    c.pay_status,
    c.pay_origin,
    c.pay_no,
    c.mch_id,
    c.app_id,
    p.name AS app_name,
    p.app_type,
    c.camp_id,
    d.camp_name,
    c.category,
    c.is_class,
    c.buy_count
FROM (
    SELECT *
    FROM drh_common_order FINAL
    WHERE _sign > 0
) c
LEFT JOIN (
    SELECT mch_id, app_id, any(name) AS name, any(app_type) AS app_type
    FROM drh_wx_pay_base FINAL
    WHERE _sign > 0
    GROUP BY mch_id, app_id
) p ON c.mch_id = p.mch_id AND c.app_id = p.app_id
LEFT JOIN dim_camp_df d ON c.camp_id = d.camp_id
WHERE c.mch_id = '1616437306'
  AND c.app_id = 'wx874eac9ca7c7e9b2'
  AND c.pay_status = 2
ORDER BY c.pay_time DESC;
