-- 多轨次续费双口径汇总
-- 轨次筛选：按用户提供的 rlike 语义，用 multiMatchAny 匹配
-- 合并规则：轨次名末尾的 (二) / （二） 合并到无后缀轨次
-- 口径：
-- 1) 宽口径：dwd_order_flow_df + dim_camp_df，订单所属营期在目标轨次下，支付成功，main_first_level='课程'
-- 2) 严口径：dwd_order_handover_df 作为轨次用户与 track_pay_time 锚点，再在同轨次同阶段课程订单中找 pay_time >= track_pay_time 的首笔续费订单

WITH target_tracks AS (
    SELECT
        class_stage_name AS stage_name,
        replaceRegexpAll(camp_group_name, '[(（]二[)）]$', '') AS track_name,
        any(camp_sku) AS camp_sku,
        max(end_class_time_bi) AS end_class_time_bi,
        groupUniqArray(camp_group_name) AS raw_track_names
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

total_scope AS (
    SELECT
        c.class_stage_name AS stage_name,
        replaceRegexpAll(c.camp_group_name, '[(（]二[)）]$', '') AS track_name,
        uniqExact(f.union_id) AS all_order_users,
        count() AS all_order_rows,
        sum(f.pay_amount) AS total_gmv
    FROM dwd_order_flow_df f
    INNER JOIN dim_camp_df c ON f.camp_id = c.camp_id
    INNER JOIN target_tracks t
      ON c.class_stage_name = t.stage_name
     AND replaceRegexpAll(c.camp_group_name, '[(（]二[)）]$', '') = t.track_name
    WHERE f.pay_status_name = '支付成功'
      AND f.main_first_level = '课程'
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
        sumIf(f.pay_amount, f.renewal_pay_time >= hb.track_pay_time) AS strict_gmv,
        minIf(f.renewal_pay_time, f.renewal_pay_time >= hb.track_pay_time) AS first_renewal_pay_time
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
        uniqExactIf(union_id, first_renewal_pay_time > toDateTime('1970-01-02 00:00:00')) AS interval_users,
        sumIf(strict_gmv, first_renewal_pay_time > toDateTime('1970-01-02 00:00:00')) AS interval_covered_gmv,
        avgIf(
            dateDiff('day', track_pay_time, first_renewal_pay_time),
            first_renewal_pay_time > toDateTime('1970-01-02 00:00:00')
        ) AS avg_interval_days
    FROM renewal_by_user
    GROUP BY stage_name, track_name
)

SELECT
    t.stage_name AS stage_name,
    t.track_name AS track_name,
    arrayStringConcat(t.raw_track_names, ',') AS included_raw_tracks,
    t.camp_sku AS camp_sku,
    t.end_class_time_bi AS end_class_time_bi,
    ifNull(ts.all_order_users, 0) AS all_order_users,
    ifNull(ts.all_order_rows, 0) AS all_order_rows,
    ifNull(ts.total_gmv, 0) AS total_gmv,
    ifNull(i.handover_users, 0) AS handover_users,
    ifNull(i.interval_users, 0) AS interval_users,
    ifNull(i.interval_covered_gmv, 0) AS interval_covered_gmv,
    if(ts.all_order_users = 0, 0, round(i.interval_users / ts.all_order_users, 4)) AS interval_user_coverage_rate,
    if(ts.total_gmv = 0, 0, round(i.interval_covered_gmv / ts.total_gmv, 4)) AS interval_gmv_coverage_rate,
    round(i.avg_interval_days, 4) AS avg_interval_days
FROM target_tracks t
LEFT JOIN total_scope ts
  ON t.stage_name = ts.stage_name
 AND t.track_name = ts.track_name
LEFT JOIN interval_scope i
  ON t.stage_name = i.stage_name
 AND t.track_name = i.track_name
ORDER BY t.stage_name, t.track_name;
