-- 指定声乐轨次：承接学员数 / GMV(含电商) / GMV(仅课程) / 续费率(课程GMV) / 平均续费间隔
-- 数据源：ClickHouse dwd_order_handover_df + dwd_order_flow_df + dim_camp_df
-- 口径：
-- 1) 承接学员数来自 dwd_order_handover_df，按 class_stage_name + 轨次 + union_id 去重。
-- 2) GMV(含电商) / GMV(仅课程) 来自承接学员在同阶段同轨次订单池中的支付成功订单，且 pay_time >= 该学员最早承接 pay_time。
-- 3) 续费率(课程GMV) = GMV(仅课程) / 承接学员数。
-- 4) 平均续费间隔 = 每个承接学员首笔课程续费订单 pay_time - 最早承接 pay_time 的天数均值。

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
        sumIf(f.pay_amount, f.renewal_pay_time >= hb.track_pay_time) AS renewal_gmv_all,
        sumIf(f.pay_amount, f.renewal_pay_time >= hb.track_pay_time AND f.main_first_level = '课程') AS renewal_course_gmv,
        minIf(f.renewal_pay_time, f.renewal_pay_time >= hb.track_pay_time AND f.main_first_level = '课程') AS first_course_renewal_pay_time
    FROM handover_base hb
    LEFT JOIN (
        SELECT
            f2.union_id AS union_id,
            f2.pay_time AS renewal_pay_time,
            f2.pay_amount AS pay_amount,
            f2.main_first_level AS main_first_level,
            c2.class_stage_name AS stage_name2,
            replaceRegexpAll(c2.camp_group_name, '[(（]二[)）]$', '') AS track_name2
        FROM dwd_order_flow_df f2
        INNER JOIN dim_camp_df c2 ON f2.camp_id = c2.camp_id
        INNER JOIN target_tracks t2
          ON c2.class_stage_name = t2.stage_name
         AND replaceRegexpAll(c2.camp_group_name, '[(（]二[)）]$', '') = t2.track_name
        WHERE f2.pay_status_name = '支付成功'
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
track_agg AS (
    SELECT
        stage_name,
        track_name,
        uniqExact(union_id) AS handover_users,
        round(sum(renewal_gmv_all), 2) AS gmv_all,
        round(sum(renewal_course_gmv), 2) AS course_gmv,
        uniqExactIf(union_id, renewal_course_gmv > 0) AS course_renewal_users,
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
    ifNull(a.handover_users, 0) AS handover_users,
    ifNull(a.gmv_all, 0) AS gmv_all,
    ifNull(a.course_gmv, 0) AS course_gmv,
    if(a.handover_users = 0, 0, round(a.course_gmv / a.handover_users, 2)) AS course_gmv_per_handover_user,
    ifNull(a.course_renewal_users, 0) AS course_renewal_users,
    if(a.handover_users = 0, 0, round(a.course_renewal_users / a.handover_users, 4)) AS course_renewal_user_rate,
    ifNull(a.avg_interval_days, 0) AS avg_interval_days
FROM target_tracks t
LEFT JOIN track_agg a
  ON t.stage_name = a.stage_name
 AND t.track_name = a.track_name
ORDER BY t.stage_name, t.track_name;
