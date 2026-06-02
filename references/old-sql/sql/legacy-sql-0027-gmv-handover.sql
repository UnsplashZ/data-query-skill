-- 指定声乐轨次 最新 GMV / 课程类GMV / 平均续费间隔
-- 数据源：ClickHouse dwd_order_flow_df + dim_camp_df + dwd_order_handover_df
-- 轨次匹配：multiMatchAny；末尾 (二)/（二） 合并到无后缀轨次
-- GMV：订单所属营期口径，支付成功订单 pay_amount
-- 课程类GMV：订单所属营期口径，支付成功且 main_first_level='课程' 的 pay_amount
-- 平均续费间隔：严格 handover 锚点口径，按用户取 handover 的最早 pay_time，再取同轨次同阶段首笔课程订单 pay_time >= track_pay_time，计算天数均值

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
),
handover_base AS (
    SELECT
        h.class_stage_name AS stage_name,
        replaceRegexpAll(h.camp_group_name, '[(（]二[)）]$', '') AS track_name,
        h.union_id AS union_id,
        min(h.pay_time) AS track_pay_time
    FROM dwd_order_handover_df h
    INNER JOIN target_tracks t
      ON h.class_stage_name = t.stage_name
     AND replaceRegexpAll(h.camp_group_name, '[(（]二[)）]$', '') = t.track_name
    WHERE h.union_id != ''
      AND multiMatchAny(h.camp_group_name, [
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
    GROUP BY h.class_stage_name, track_name, h.union_id
),
renewal_by_user AS (
    SELECT
        hb.stage_name AS stage_name,
        hb.track_name AS track_name,
        hb.union_id AS union_id,
        hb.track_pay_time AS track_pay_time,
        sumIf(f.pay_amount, f.renewal_pay_time >= hb.track_pay_time) AS strict_course_gmv,
        minIf(f.renewal_pay_time, f.renewal_pay_time >= hb.track_pay_time) AS first_course_renewal_pay_time
    FROM handover_base hb
    LEFT JOIN (
        SELECT
            f2.union_id AS union_id,
            f2.pay_time AS renewal_pay_time,
            f2.pay_amount AS pay_amount,
            c2.class_stage_name AS stage_name2,
            replaceRegexpAll(c2.camp_group_name, '[(（]二[)）]$', '') AS track_name2
        FROM dwd_order_flow_df f2
        INNER JOIN dim_camp_df c2 ON f2.camp_id = c2.camp_id
        INNER JOIN target_tracks t2
          ON c2.class_stage_name = t2.stage_name
         AND replaceRegexpAll(c2.camp_group_name, '[(（]二[)）]$', '') = t2.track_name
        WHERE f2.pay_status_name = '支付成功'
          AND f2.main_first_level = '课程'
          AND multiMatchAny(c2.camp_group_name, [
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
    ) AS f
      ON hb.union_id = f.union_id
     AND hb.stage_name = f.stage_name2
     AND hb.track_name = f.track_name2
    GROUP BY hb.stage_name, hb.track_name, hb.union_id, hb.track_pay_time
),
interval_scope AS (
    SELECT
        stage_name,
        track_name,
        uniqExact(union_id) AS handover_users,
        uniqExactIf(union_id, first_course_renewal_pay_time > toDateTime('1970-01-02 00:00:00')) AS interval_users,
        round(sumIf(strict_course_gmv, first_course_renewal_pay_time > toDateTime('1970-01-02 00:00:00')), 2) AS interval_course_gmv,
        round(avgIf(
            dateDiff('day', track_pay_time, first_course_renewal_pay_time),
            first_course_renewal_pay_time > toDateTime('1970-01-02 00:00:00')
        ), 4) AS avg_interval_days
    FROM renewal_by_user
    GROUP BY stage_name, track_name
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
    ifNull(o.course_gmv, 0) AS course_gmv,
    ifNull(i.handover_users, 0) AS handover_users,
    ifNull(i.interval_users, 0) AS interval_users,
    ifNull(i.interval_course_gmv, 0) AS interval_course_gmv,
    if(o.course_pay_users = 0, 0, round(i.interval_users / o.course_pay_users, 4)) AS interval_user_coverage_rate,
    if(o.course_gmv = 0, 0, round(i.interval_course_gmv / o.course_gmv, 4)) AS interval_gmv_coverage_rate,
    ifNull(i.avg_interval_days, 0) AS avg_interval_days
FROM target_tracks t
LEFT JOIN order_scope o
  ON t.stage_name = o.stage_name
 AND t.track_name = o.track_name
LEFT JOIN interval_scope i
  ON t.stage_name = i.stage_name
 AND t.track_name = i.track_name
ORDER BY t.stage_name, t.track_name;
