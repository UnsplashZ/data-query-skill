
SELECT
  toStartOfMonth(toDate(cd.end_time)) AS camp_month,
  
CASE
  WHEN cb.market_belong LIKE '%BD2%' AND cb.teach_help = '图书' THEN 'BD2-图书'
  WHEN cb.market_belong LIKE '%BD2%' AND tau.is_callback = '0元' AND cb.teach_help = '非图书' THEN 'BD2-0元'
  WHEN cb.market_belong LIKE '%BD1%' THEN 'BD1'
  WHEN cb.market_belong = '' OR cb.market_belong IS NULL THEN '未归类'
  ELSE cb.market_belong
END
 AS channel,
  count() AS leads_cnt,
  sum(ifNull(tau.is_friend, 0)) AS friend_cnt,
  sum(ifNull(tau.leads_cost, 0)) AS leads_cost,
  sum(ifNull(tau.d1_arrive, 0)) AS d1_arrive,
  sum(ifNull(tau.d2_arrive, 0)) AS d2_arrive,
  sum(ifNull(tau.d3_arrive, 0)) AS d3_arrive,
  sum(ifNull(tau.d4_arrive, 0)) AS d4_arrive,
  sum(ifNull(tau.d5_arrive, 0)) AS d5_arrive,
  sum(ifNull(tau.d6_arrive, 0)) AS d6_arrive
FROM tock_applet_user AS tau
INNER JOIN (SELECT * FROM drh_live_camp_date FINAL WHERE _sign > 0) AS cd ON tau.camp_date_id = cd.id
INNER JOIN tock_channel_id_belong AS cb ON tau.channel_id = cb.channel_id
WHERE tau.is_repeat_leads = 0
  AND tau.is_callback != ''
  AND tau.sku = '声乐'
  AND cd.end_time >= toDateTime('2025-11-01 00:00:00')
  AND cd.end_time < toDateTime('2026-06-01 00:00:00')
GROUP BY camp_month, channel
ORDER BY camp_month, channel
