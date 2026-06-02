-- 指定声乐轨次 最新 GMV / 课程类GMV
-- 数据源：ClickHouse dwd_order_flow_df + dim_camp_df
-- 轨次匹配：multiMatchAny；末尾 (二)/（二） 合并到无后缀轨次
-- GMV：支付成功订单 pay_amount
-- 课程类GMV：支付成功且 main_first_level='课程' 的 pay_amount

WITH target_tracks AS (
    SELECT
        class_stage_name AS stage_name,
        replaceRegexpAll(camp_group_name, '[(（]二[)）]$', '') AS track_name,
        groupUniqArray(camp_group_name) AS included_raw_tracks,
        max(end_class_time_bi) AS end_class_time_bi
    FROM dim_camp_df
    WHERE multiMatchAny(camp_group_name, [
        '声乐二阶-20251209-院长班',
        '声乐二阶-20251223-院长特惠班',
        '声乐二阶-20251224-赵曼院长班-BLT',
        '声乐二阶-20260106-院长班',
        '声乐二阶-20260113-院长班BLT',
        '声乐二阶-20260127-院长特惠班',
        '声乐二阶-20260203-院长班',
        '声乐三阶-20251118-进阶班',
        '声乐三阶-20260106-进阶班',
        '声乐四阶-20251111-名师班'
    ])
      AND camp_group_name != ''
    GROUP BY class_stage_name, track_name
),
order_scope AS (
    SELECT
        c.class_stage_name AS stage_name,
        replaceRegexpAll(c.camp_group_name, '[(（]二[)）]$', '') AS track_name,
        uniqExact(f.union_id) AS pay_users,
        uniqExact(f.flow_no) AS pay_orders,
        round(sum(f.pay_amount), 2) AS gmv,
        uniqExactIf(f.union_id, f.main_first_level = '课程') AS course_pay_users,
        uniqExactIf(f.flow_no, f.main_first_level = '课程') AS course_pay_orders,
        round(sumIf(f.pay_amount, f.main_first_level = '课程'), 2) AS course_gmv
    FROM dwd_order_flow_df f
    INNER JOIN dim_camp_df c ON f.camp_id = c.camp_id
    INNER JOIN target_tracks t
      ON c.class_stage_name = t.stage_name
     AND replaceRegexpAll(c.camp_group_name, '[(（]二[)）]$', '') = t.track_name
    WHERE f.pay_status_name = '支付成功'
      AND multiMatchAny(c.camp_group_name, [
        '声乐二阶-20251209-院长班',
        '声乐二阶-20251223-院长特惠班',
        '声乐二阶-20251224-赵曼院长班-BLT',
        '声乐二阶-20260106-院长班',
        '声乐二阶-20260113-院长班BLT',
        '声乐二阶-20260127-院长特惠班',
        '声乐二阶-20260203-院长班',
        '声乐三阶-20251118-进阶班',
        '声乐三阶-20260106-进阶班',
        '声乐四阶-20251111-名师班'
      ])
    GROUP BY c.class_stage_name, track_name
)
SELECT
    t.stage_name,
    t.track_name,
    arrayStringConcat(t.included_raw_tracks, ',') AS included_raw_tracks,
    t.end_class_time_bi,
    ifNull(o.pay_users, 0) AS pay_users,
    ifNull(o.pay_orders, 0) AS pay_orders,
    ifNull(o.gmv, 0) AS gmv,
    ifNull(o.course_pay_users, 0) AS course_pay_users,
    ifNull(o.course_pay_orders, 0) AS course_pay_orders,
    ifNull(o.course_gmv, 0) AS course_gmv
FROM target_tracks t
LEFT JOIN order_scope o
  ON t.stage_name = o.stage_name
 AND t.track_name = o.track_name
ORDER BY t.stage_name, t.track_name;
