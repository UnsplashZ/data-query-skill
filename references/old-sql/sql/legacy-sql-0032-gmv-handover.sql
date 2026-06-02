
WITH
input_tracks AS (
    SELECT *
    FROM values('input_order UInt8, track_name String',
        (1, '声乐三阶-20260106-进阶班'),
        (2, '声乐二阶-20260106-院长班'),
        (3, '声乐四阶-20260310-师承班'),
        (4, '声乐二阶-20260127-院长特惠班'),
        (5, '声乐二阶-20260203-院长班'),
        (6, '声乐三阶-20260310-进阶班'),
        (7, '声乐二阶-20260210-院长特惠班'),
        (8, '声乐二阶-20260317-院长班'),
        (9, '声乐二阶-20260310-BLT院长特惠班'),
        (10, '声乐二阶-20260310-BLT院长班')
    )
),
raw_input AS (
    SELECT *
    FROM values('raw_track_name String',
        ('声乐三阶-20260106-进阶班'),
        ('声乐二阶-20260106-院长班'),
        ('声乐二阶-20260106-院长班（二）'),
        ('声乐四阶-20260310-师承班'),
        ('声乐二阶-20260127-院长特惠班'),
        ('声乐二阶-20260203-院长班'),
        ('声乐二阶-20260203-院长班(二)'),
        ('声乐三阶-20260310-进阶班'),
        ('声乐二阶-20260210-院长特惠班'),
        ('声乐二阶-20260317-院长班'),
        ('声乐二阶-20260310-BLT院长特惠班'),
        ('声乐二阶-20260310-BLT院长班')
    )
),
target_tracks AS (
    SELECT
        min(i.input_order) AS input_order,
        c.class_stage_name AS stage_name,
        replaceRegexpAll(c.camp_group_name, '[(（]二[)）]$', '') AS track_name,
        groupUniqArray(c.camp_group_name) AS included_raw_tracks,
        max(c.end_class_time_bi) AS end_class_time_bi
    FROM dim_camp_df c
    INNER JOIN input_tracks i
      ON replaceRegexpAll(c.camp_group_name, '[(（]二[)）]$', '') = i.track_name
    WHERE c.camp_group_name != ''
    GROUP BY c.class_stage_name, track_name
),
missing_input AS (
    SELECT
        i.input_order AS input_order,
        '' AS stage_name,
        i.track_name AS track_name,
        [] AS included_raw_tracks,
        toDateTime('1970-01-01 00:00:00') AS end_class_time_bi
    FROM input_tracks i
    LEFT JOIN target_tracks t ON i.track_name = t.track_name
    WHERE t.track_name = ''
),
target_all AS (
    SELECT * FROM target_tracks
    UNION ALL
    SELECT * FROM missing_input
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
    t.input_order,
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
FROM target_all t
LEFT JOIN track_agg a
  ON t.stage_name = a.stage_name
 AND t.track_name = a.track_name
ORDER BY t.input_order, t.stage_name;
