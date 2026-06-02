
SELECT
    '钢琴' AS sku,
    '合计' AS front_end_name,
    count() AS total_order_cnt,
    uniqExact(union_id) AS total_user_cnt,
    round(sum(pay_amount), 2) AS total_gmv,
    countIf(main_goods_sku = '钢琴' AND main_first_level = '课程' AND total_original_price >= 880) AS sku_880_course_order_cnt,
    uniqExactIf(union_id, main_goods_sku = '钢琴' AND main_first_level = '课程' AND total_original_price >= 880) AS sku_880_course_user_cnt,
    round(sumIf(pay_amount, main_goods_sku = '钢琴' AND main_first_level = '课程' AND total_original_price >= 880), 2) AS sku_880_course_gmv,
    round(sku_880_course_gmv / nullIf(total_gmv, 0), 6) AS sku_880_course_gmv_ratio
FROM dwd_order_flow_df
WHERE pay_status_name = '支付成功'
  AND pay_time >= toDateTime('2026-01-01 00:00:00')
  AND pay_time < toDateTime('2027-01-01 00:00:00')
  AND cci3_name = '钢琴'
