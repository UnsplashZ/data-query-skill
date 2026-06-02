-- 口径说明：
-- 1) 基于 cashflow-core 导出的 订单明细 / 退款明细 明细口径
-- 2) 前端定义：前后端 LIKE '%前端%'
-- 3) 声乐定义：sku = '声乐'
-- 4) 时间口径：支付自然月 = '2026-03'
-- 5) cohort退费 = 按订单号聚合后的累计退款金额
-- 6) 该 SQL 是对之前 pandas 汇总逻辑的等价表达

WITH orders_base AS (
    SELECT
        `订单号`,
        `sku`,
        `渠道聚合类型`,
        `前后端`,
        substr(CAST(`支付日期` AS STRING), 1, 7) AS `支付自然月`,
        CAST(`gmv` AS DOUBLE) AS `gmv_val`
    FROM orders_detail_source
    WHERE `前后端` LIKE '%前端%'
      AND `sku` = '声乐'
      AND substr(CAST(`支付日期` AS STRING), 1, 7) = '2026-03'
),
refunds_grouped AS (
    SELECT
        `订单号`,
        SUM(CAST(`退款gmv` AS DOUBLE)) AS `cohort退费`
    FROM refunds_detail_source
    GROUP BY `订单号`
)
SELECT
    o.`sku` AS `sku`,
    o.`渠道聚合类型` AS `渠道聚合类型`,
    o.`支付自然月` AS `支付自然月`,
    ROUND(SUM(o.`gmv_val`), 2) AS `gmv`,
    ROUND(SUM(COALESCE(r.`cohort退费`, 0)), 2) AS `退费`,
    COUNT(DISTINCT o.`订单号`) AS `订单数`,
    ROUND(
        CASE WHEN SUM(o.`gmv_val`) = 0 THEN 0
             ELSE SUM(COALESCE(r.`cohort退费`, 0)) / SUM(o.`gmv_val`)
        END,
        6
    ) AS `cohort退费率`
FROM orders_base o
LEFT JOIN refunds_grouped r
    ON o.`订单号` = r.`订单号`
GROUP BY
    o.`sku`,
    o.`渠道聚合类型`,
    o.`支付自然月`
ORDER BY `gmv` DESC;
