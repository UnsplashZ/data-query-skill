-- 轨次续费双口径汇总
-- 口径：
-- 1) 总GMV / 全部下单用户数 / 全部订单数：宽口径
--    - 订单所属营期在目标轨次下
--    - 来源 dwd_order_flow_df + dim_camp_df
--    - 条件：支付成功 + main_first_level='课程'
-- 2) 平均续费间隔 / 可计算续费间隔用户数 / 间隔覆盖GMV：严口径
--    - 必须在 dwd_order_handover_df 中能找到该轨次的 track_pay_time
--    - 续费间隔 = 首笔续费支付时间 - 轨次付费时间
--
-- 用法：把下面两个地方的轨次名替换为目标值：
--   声乐二阶-20251224-赵曼院长班-BLT

WITH total_scope AS (
    SELECT
        c.class_stage_name AS stage_name,
        c.camp_group_name AS track_name,
        uniqExact(f.union_id) AS all_order_users,
        count() AS all_order_rows,
        sum(f.pay_amount) AS total_gmv
    FROM dwd_order_flow_df f
    INNER JOIN dim_camp_df c ON f.camp_id = c.camp_id
    WHERE c.camp_group_name = '声乐二阶-20251224-赵曼院长班-BLT'
      AND f.pay_status_name = '支付成功'
      AND f.main_first_level = '课程'
    GROUP BY c.class_stage_name, c.camp_group_name
),

interval_scope AS (
    SELECT
        hb.stage_name,
        hb.track_name,
        uniqExactIf(hb.union_id, fs.first_renewal_pay_time > toDateTime('1970-01-02 00:00:00')) AS interval_users,
        sumIf(fs.strict_gmv, fs.first_renewal_pay_time > toDateTime('1970-01-02 00:00:00')) AS interval_covered_gmv,
        avgIf(
            dateDiff('day', hb.track_pay_time, fs.first_renewal_pay_time),
            fs.first_renewal_pay_time > toDateTime('1970-01-02 00:00:00')
        ) AS avg_interval_days
    FROM (
        SELECT
            h.class_stage_name AS stage_name,
            h.camp_group_name AS track_name,
            h.union_id AS union_id,
            min(h.pay_time) AS track_pay_time
        FROM dwd_order_handover_df h
        WHERE h.camp_group_name = '声乐二阶-20251224-赵曼院长班-BLT'
          AND h.union_id != ''
        GROUP BY h.class_stage_name, h.camp_group_name, h.union_id
    ) AS hb
    LEFT JOIN (
        SELECT
            h2.union_id AS union_id,
            minIf(f2.pay_time, f2.pay_time >= h2.track_pay_time) AS first_renewal_pay_time,
            sumIf(f2.pay_amount, f2.pay_time >= h2.track_pay_time) AS strict_gmv
        FROM (
            SELECT
                union_id,
                min(pay_time) AS track_pay_time
            FROM dwd_order_handover_df
            WHERE camp_group_name = '声乐二阶-20251224-赵曼院长班-BLT'
              AND union_id != ''
            GROUP BY union_id
        ) AS h2
        LEFT JOIN (
            SELECT
                f.union_id AS union_id,
                f.pay_time AS pay_time,
                f.pay_amount AS pay_amount
            FROM dwd_order_flow_df f
            INNER JOIN dim_camp_df c2 ON f.camp_id = c2.camp_id
            WHERE c2.camp_group_name = '声乐二阶-20251224-赵曼院长班-BLT'
              AND f.pay_status_name = '支付成功'
              AND f.main_first_level = '课程'
        ) AS f2
          ON h2.union_id = f2.union_id
        GROUP BY h2.union_id
    ) AS fs
      ON hb.union_id = fs.union_id
    GROUP BY hb.stage_name, hb.track_name
)

SELECT
    t.stage_name AS `营期阶段`,
    t.track_name AS `轨次`,
    t.all_order_users AS `全部下单用户数`,
    t.all_order_rows AS `全部订单数`,
    t.total_gmv AS `总GMV`,
    i.interval_users AS `可计算续费间隔用户数`,
    i.interval_covered_gmv AS `间隔覆盖GMV`,
    round(i.interval_users / t.all_order_users, 4) AS `间隔用户覆盖率`,
    round(i.interval_covered_gmv / t.total_gmv, 4) AS `间隔GMV覆盖率`,
    i.avg_interval_days AS `平均续费间隔(天)`
FROM total_scope t
LEFT JOIN interval_scope i
  ON t.stage_name = i.stage_name
 AND t.track_name = i.track_name;
