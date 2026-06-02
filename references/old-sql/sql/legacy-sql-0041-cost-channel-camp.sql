
SELECT
  toStartOfMonth(toDate(cd.end_time)) AS camp_month,
  
CASE
  WHEN market_belong LIKE '%BD2%' AND teach_help = '图书' THEN 'BD2-图书'
  WHEN market_belong LIKE '%BD2%' AND is_callback = '0元' AND teach_help = '非图书' THEN 'BD2-0元'
  WHEN market_belong LIKE '%BD1%' THEN 'BD1'
  WHEN market_belong = '' OR market_belong IS NULL THEN '未归类'
  ELSE market_belong
END
 AS channel_group,
  count() AS leads_cnt,
  sum(ifNull(tau.is_friend, 0)) AS friend_cnt,
  sum(if(tau.is_callback = '0元', 1, 0)) AS zero_leads_cnt,
  sum(if(tau.is_callback = '1元', 1, 0)) AS one_leads_cnt,
  sum(ifNull(tau.leads_cost, 0)) AS leads_cost,
  sum(ifNull(tau.d1_arrive, 0)) AS d1_arrive,
  sum(ifNull(tau.d2_arrive, 0)) AS d2_arrive,
  sum(ifNull(tau.d3_arrive, 0)) AS d3_arrive,
  sum(ifNull(tau.d4_arrive, 0)) AS d4_arrive,
  sum(ifNull(tau.d5_arrive, 0)) AS d5_arrive,
  sum(ifNull(tau.d6_arrive, 0)) AS d6_arrive
FROM tock_applet_user AS tau
INNER JOIN (SELECT * FROM drh_live_camp_date FINAL WHERE _sign > 0) AS cd ON tau.camp_date_id = cd.id
WHERE tau.is_repeat_leads = 0
  AND tau.is_callback != ''
  AND cd.end_time >= toDateTime('2025-11-01 00:00:00')
  AND cd.end_time < toDateTime('2026-06-01 00:00:00')
GROUP BY camp_month, channel_group
ORDER BY camp_month, channel_group
