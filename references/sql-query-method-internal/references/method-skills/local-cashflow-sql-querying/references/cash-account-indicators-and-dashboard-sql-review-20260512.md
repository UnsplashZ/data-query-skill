# Cash-account indicators and dashboard SQL review notes — 2026-05-12

## When to use

Use these notes when the user asks for total income / total expense by SKU bundle, or asks to review a long ClickHouse dashboard SQL similar to `/Users/zheng/Desktop/2.sql`.

## Prefer cash-account indicators for 总收入 / 总支出

The user corrected the source choice: for `总收入` and `总支出`, use the cash-account indicator table directly instead of stitching income from `dws_netcashflow_gmv_df` and expense from `dwd_finance_cash_cost_md_pdf`.

Verified ClickHouse table:

```sql
tock_dws_cash_account_indicators_md_pdf
```

Relevant columns:

```text
p_date           日期
sku1             一级SKU
sku2             二级SKU
studio_lv1       一级流量工作室
studio_lv2       二级流量工作室
indicators_name  指标名
data_d           指标值
mn               月份
org_name2        二级部门
```

Current-month-to-date pattern:

```sql
SELECT
    multiIf(
        sku2 IN ('口琴','美妆'), '口琴(含美妆)',
        sku2 IN ('声乐IP季课','冥想瑜伽'), '声乐IP季课(含冥想瑜伽)',
        'other'
    ) AS grp,
    round(sumIf(data_d, indicators_name = '总支出'), 2) AS total_cost,
    round(sumIf(data_d, indicators_name = '总收入'), 2) AS total_income,
    minIf(p_date, indicators_name IN ('总支出','总收入')) AS min_date,
    maxIf(p_date, indicators_name IN ('总支出','总收入')) AS max_date
FROM tock_dws_cash_account_indicators_md_pdf
WHERE sku2 IN ('口琴','美妆','声乐IP季课','冥想瑜伽')
  AND indicators_name IN ('总支出','总收入')
  AND toDate(p_date) >= toStartOfMonth(today())
  AND toDate(p_date) <= today()
GROUP BY grp
ORDER BY grp
```

Verified 2026-05 MTD example at time of discovery:

```text
口琴(含美妆): 总支出 1,197,345.82; 总收入 740,432.05
声乐IP季课(含冥想瑜伽): 总支出 974,043.13; 总收入 318,211.90
```

Component check at time of discovery:

```text
口琴: 总支出 1,155,330.70; 总收入 709,577.05
美妆: 总支出 42,015.13; 总收入 30,855.00
声乐IP季课: 总支出 967,963.13; 总收入 318,211.90
冥想瑜伽: 总支出 6,080.00; 总收入 0.00
```

## Dashboard SQL review checklist from `/Users/zheng/Desktop/2.sql`

A rendered test with:

```text
sku = 声乐
start_time = 2026-05-12
end_time = 2026-05-12
```

ran successfully, so the file was not a pure syntax failure. The durable review points were logic and parameter safety.

### 1. Optional team filter can reference the wrong employee field

In `drh_applet_user` and `tock_applet_user` sections, the optional `team_name` block used:

```sql
a1.emp_num in (...)
```

Verified fields:

```text
drh_applet_user has emp_id, not emp_num
tock_applet_user has emp_id, not emp_num
dr h_order uses emp_num; that section is OK
```

Fix for those non-order sections:

```sql
[[and a1.emp_id in (
    select emp_id
    from drh_kk_group_team final
    where _sign > 0
      and {{team_name}}
)]]
```

### 2. BD1 categorization must be internally consistent

The SQL comments said BD1 should not be split by `teach_help`, but the CASE logic still produced `BD1-书课包` in several branches:

```sql
when market_belong like '%BD1%' and teach_help = '图书' then 'BD1-书课包'
when market_belong like '%BD1%' then 'BD1'
```

The later grouped label only included `BD1` and `BD1-0元`, so any `BD1-书课包` could fall to `其他`.

Preferred options:

- If BD1 should be unified, simplify all branches to `when market_belong like '%BD1%' then 'BD1'` and remove `BD1-书课包` / `BD1-0元` downstream logic.
- If `BD1-书课包` remains, include it in summary grouping:

```sql
when multiMatchAny(channel_emp_type, ['BD1','BD1-0元','BD1-书课包']) then 'BD1-汇总'
```

### 3. `drh_live_camp_date` join can amplify order facts

The reviewed SQL joined:

```sql
left join (
    select camp_id, class_time
    from drh_live_camp_date final
    where _sign > 0
) a10 on a1.camp_id = a10.camp_id
```

`drh_live_camp_date` may contain multiple rows per `camp_id`; joining it directly can duplicate order rows and inflate GMV/cost/D4-D9 metrics. Safer default:

```sql
left join (
    select
        camp_id,
        min(class_time) as class_time
    from drh_live_camp_date final
    where _sign > 0
      and camp_id is not null
      and camp_id > 0
    group by camp_id
) a10 on a1.camp_id = a10.camp_id
```

If business needs a different class-time definition, choose `min` / `max` / a date-type-specific row explicitly.

### 4. Guard `加微率` against zero leads

The SQL used:

```sql
sum(is_friend)/sum(leads_cnt) AS `加微率`
```

Use the same protection already used for D-rate metrics:

```sql
if(sum(leads_cnt)=0, 0, sum(is_friend)/sum(leads_cnt)) AS `加微率`
```

### 5. Sum of pre-aggregated distinct users is not global distinct users

The reviewed SQL computed `zj_cnt` as `count(distinct user_id)` at daily/channel/SKU/teach_help grain, then summed it in outer summary rows. This is valid only if the intended metric is additive across categories. If the user asks for true de-duplicated 正价课学员数 at the final summary grain, keep user-level detail through the aggregation or recompute distinct at the final grain.

### 6. Long dashboard SQL review workflow

For this class of SQL review:

1. Read the exact file first.
2. Render dashboard placeholders with a minimal safe test parameter set.
3. Strip optional `[[...]]` blocks for a base syntax run, then test selected optional blocks separately.
4. Use `LIMIT 1` for syntax/shape checks.
5. Verify physical fields in `system.columns` before calling a block valid.
6. Check join cardinality for potentially one-to-many dimension joins before concluding metric correctness.
7. Report separately:
   - runnable syntax status;
   - hard errors that only appear when optional filters are enabled;
   - metric-inflation risks;
   - business categorization inconsistencies.
