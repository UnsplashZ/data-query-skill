
SELECT
  toStartOfMonth(toDate(o.camp_end_time)) AS camp_month,
  
CASE
  WHEN cb.market_belong LIKE '%BD2%' AND cb.teach_help = '图书' THEN 'BD2-图书'
  WHEN cb.market_belong LIKE '%BD2%' AND ce.is_pay = 0 AND cb.teach_help = '非图书' THEN 'BD2-0元'
  WHEN cb.market_belong LIKE '%BD1%' THEN 'BD1'
  WHEN cb.market_belong = '' OR cb.market_belong IS NULL THEN '未归类'
  ELSE cb.market_belong
END
 AS channel,
  sum(o.price) / 100 AS gmv,
  uniqExact(if(o.price >= 188000 AND o.pay_type IN (2, 3), o.user_id, NULL)) AS formal_student_cnt,
  sum(if(o.in_class = 0, o.price, 0)) / 100 AS in_class_gmv,
  sum(if(day_no = 1, o.price, 0)) / 100 AS d1_gmv,
  sum(if(day_no = 2, o.price, 0)) / 100 AS d2_gmv,
  sum(if(day_no = 3, o.price, 0)) / 100 AS d3_gmv,
  sum(if(day_no = 4, o.price, 0)) / 100 AS d4_gmv,
  sum(if(day_no = 5, o.price, 0)) / 100 AS d5_gmv,
  sum(if(day_no = 6, o.price, 0)) / 100 AS d6_gmv,
  sum(if(day_no = 7, o.price, 0)) / 100 AS d7_gmv,
  sum(if(day_no = 8, o.price, 0)) / 100 AS d8_gmv,
  sum(if(day_no = 9, o.price, 0)) / 100 AS d9_gmv,
  sum(if(day_no = 1 AND o.in_class = 0, o.price, 0)) / 100 AS d1_in_class_gmv,
  sum(if(day_no = 2 AND o.in_class = 0, o.price, 0)) / 100 AS d2_in_class_gmv,
  sum(if(day_no = 3 AND o.in_class = 0, o.price, 0)) / 100 AS d3_in_class_gmv,
  sum(if(day_no = 4 AND o.in_class = 0, o.price, 0)) / 100 AS d4_in_class_gmv,
  sum(if(day_no = 5 AND o.in_class = 0, o.price, 0)) / 100 AS d5_in_class_gmv,
  sum(if(day_no = 6 AND o.in_class = 0, o.price, 0)) / 100 AS d6_in_class_gmv,
  sum(if(day_no = 7 AND o.in_class = 0, o.price, 0)) / 100 AS d7_in_class_gmv,
  sum(if(day_no = 8 AND o.in_class = 0, o.price, 0)) / 100 AS d8_in_class_gmv,
  sum(if(day_no = 9 AND o.in_class = 0, o.price, 0)) / 100 AS d9_in_class_gmv
FROM
(
  SELECT
    order_id,
    user_id,
    price,
    pay_time,
    pay_type,
    in_class,
    channel_id,
    camp_end_time,
    class_time,
    dateDiff('day', toDate(class_time), toDate(pay_time)) + 1 AS day_no
  FROM
  (
    SELECT
      o.id AS order_id,
      o.user_id AS user_id,
      o.price AS price,
      o.pay_time AS pay_time,
      o.pay_type AS pay_type,
      o.in_class AS in_class,
      o.channel_id AS channel_id,
      cd.end_time AS camp_end_time,
      cd.class_time AS class_time
    FROM (SELECT id, user_id, price, pay_time, pay_type, in_class, channel_id, camp_id, front_end, pay_status FROM drh_order FINAL WHERE _sign > 0) AS o
    INNER JOIN (SELECT id, camp_id, end_time, class_time, category FROM drh_live_camp_date FINAL WHERE _sign > 0) AS cd ON o.camp_id = cd.camp_id
    INNER JOIN (SELECT category, name FROM drh_business_line FINAL WHERE _sign > 0) AS bl ON cd.category = bl.category
    WHERE o.price > 0
      AND o.front_end = 1
      AND o.pay_status = 2
      AND bl.name = '声乐'
      AND cd.end_time >= toDateTime('2025-11-01 00:00:00')
      AND cd.end_time < toDateTime('2026-06-01 00:00:00')
  ) AS base_orders
) AS o
INNER JOIN (SELECT channel_id, id, is_pay FROM drh_channel_emp FINAL WHERE _sign > 0) AS ce ON o.channel_id = ce.channel_id
INNER JOIN tock_channel_id_belong AS cb ON o.channel_id = cb.channel_id
GROUP BY camp_month, channel
ORDER BY camp_month, channel
