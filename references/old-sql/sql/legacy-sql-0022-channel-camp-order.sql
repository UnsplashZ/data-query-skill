SELECT
    flow_no,
    collect_order_no,
    union_id,
    camp_id,
    camp_name,
    main_goods_sku,
    camp_sku,
    pay_amount,
    pay_amount_hc,
    pay_amount_uhc,
    pay_time,
    pay_status_code,
    pay_status_name,
    order_source_code,
    order_source_name,
    pay_source,
    pay_no,
    mch_id
FROM dwd_order_flow_df
WHERE mch_id = '1616437306'
  AND pay_status_name = '支付成功'
ORDER BY pay_time DESC;
