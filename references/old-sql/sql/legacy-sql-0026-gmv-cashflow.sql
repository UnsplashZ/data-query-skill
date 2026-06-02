
WITH
    toDate('{{start_date}}') AS start_date,
    toDate('{{end_date}}') AS end_date,
    budget_daily AS (
        SELECT
            dt AS stat_date,
            sku,
            toString(front_end) AS front_back,
            sum(gmv) AS day_budget
        FROM daily_gmv_budget
        WHERE sku = '社团'
          AND toString(front_end) = '社团'
          AND dt >= start_date
          AND dt <= end_date
        GROUP BY stat_date, sku, front_back
    ),
    real_daily AS (
        SELECT
            toDate(p_date) AS stat_date,
            sku2 AS sku,
            replaceRegexpAll(org_name2, '大', '') AS front_back,
            sum(data_d) AS day_gmv
        FROM tock_dws_cash_account_indicators_md_pdf
        WHERE sku2 = '社团'
          AND replaceRegexpAll(org_name2, '大', '') = '社团'
          AND p_date >= toDateTime(start_date)
          AND p_date < addDays(toDateTime(end_date), 1)
          AND mn >= toString(toYYYYMM(start_date))
          AND mn <= toString(toYYYYMM(end_date))
          AND indicators_name IN ('GMV', '渠道收入', '打赏收入')
        GROUP BY stat_date, sku, front_back
    ),
    daily AS (
        SELECT
            b.stat_date AS stat_date,
            b.sku AS sku,
            b.front_back AS front_back,
            b.day_budget AS day_budget,
            ifNull(r.day_gmv, 0) AS day_gmv
        FROM budget_daily b
        LEFT JOIN real_daily r
            ON b.stat_date = r.stat_date
           AND b.sku = r.sku
           AND b.front_back = r.front_back
        UNION ALL
        SELECT
            r.stat_date AS stat_date,
            r.sku AS sku,
            r.front_back AS front_back,
            0 AS day_budget,
            r.day_gmv AS day_gmv
        FROM real_daily r
        LEFT JOIN budget_daily b
            ON b.stat_date = r.stat_date
           AND b.sku = r.sku
           AND b.front_back = r.front_back
        WHERE b.stat_date IS NULL
    ),
    monthly_budget AS (
        SELECT
            sku,
            toString(front_end) AS front_back,
            sum(gmv) AS month_budget
        FROM daily_gmv_budget
        WHERE sku = '社团'
          AND toString(front_end) = '社团'
          AND dt >= toStartOfMonth(start_date)
          AND dt < addMonths(toStartOfMonth(start_date), 1)
        GROUP BY sku, front_back
    ),
    calc AS (
        SELECT
            d.stat_date AS stat_date,
            d.sku AS sku,
            d.front_back AS front_back,
            ifNull(m.month_budget, 0) AS month_budget,
            sum(d.day_gmv) OVER (PARTITION BY d.sku, d.front_back, toYYYYMM(d.stat_date) ORDER BY d.stat_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS current_gmv,
            round((dateDiff('day', toStartOfMonth(d.stat_date), d.stat_date) + 1) * 1.0 /
                  (dateDiff('day', toStartOfMonth(d.stat_date), addDays(addMonths(toStartOfMonth(d.stat_date), 1), -1)) + 1), 4) AS month_progress,
            sum(d.day_budget) OVER (PARTITION BY d.sku, d.front_back, toYYYYMM(d.stat_date) ORDER BY d.stat_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS current_budget,
            d.day_budget AS day_budget,
            d.day_gmv AS day_gmv
        FROM daily d
        LEFT JOIN monthly_budget m
            ON d.sku = m.sku
           AND d.front_back = m.front_back
    )
SELECT
    stat_date AS `日期`,
    sku AS `SKU`,
    front_back AS `前后端`,
    month_budget AS `当月预算`,
    current_gmv AS `当前GMV`,
    if(month_budget = 0, NULL, current_gmv / month_budget) AS `当月达成`,
    month_progress AS `时间进度`,
    current_budget AS `当前预算`,
    if(current_budget = 0, NULL, current_gmv / current_budget) AS `当前达成`,
    day_budget AS `当日预算`,
    day_gmv AS `当日GMV`,
    if(day_budget = 0, NULL, day_gmv / day_budget) AS `当日达成`
FROM calc
ORDER BY stat_date;
