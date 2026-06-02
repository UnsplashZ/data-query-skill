# 仅首款未付尾款订单与休学冻课分析

## Session context

The user has repeatedly asked for leadership-facing Excel workbooks around two related datasets:

1. `仅首款未付尾款订单`
   - source: `dwd_order_flow_df`
   - order-flow grain
   - first-payment rows that have not been related by a later tail-payment row
2. `休学冻课学员订单`
   - **independent dataset**, not a subset of the first-payment-only pool unless explicitly requested
   - should be treated as one combined business concept: `休学冻课`

Earlier workbook path:

`~/.hermes/output/query_results/仅首款未付尾款_课程前端_领导版数据简报_含休学冻课_20260429.xlsx`

Historical all-data corrected workbook path from 2026-05-08:

`~/.hermes/output/query_results/仅首款订单与休学冻课_独立口径_领导版_历史全量_补关键词_合并口径_20260508.xlsx`

Script retained under:

`~/.hermes/python/projects/first-payment-only/make_independent_leader_report_history_keyword_combined.py`

## First-payment-only order pool

Source:

- `dwd_order_flow_df`

Recommended anti-join:

- base rows:
  - `pay_status_name='支付成功'`
  - `pay_type_code=1`
  - `pay_type_name='首款'`
  - `main_first_level='课程'`
- tail-payment exclusion:
  - tail rows where `pay_type_code=2`, `pay_type_name='尾款'`, `pay_status_name='支付成功'`, `relate_flow_no != ''`
  - `LEFT JOIN tail_pay t ON f.flow_no = t.relate_flow_no`
  - keep `t.relate_flow_no = ''`

This is order-flow grain. Always verify:

```text
len(df) == df['flow_no'].nunique()
```

## Corrected 休学冻课口径

The user corrected the report on 2026-05-08:

> 休学冻课还要补充一种类型，handover_plus表中，class_camp_name如果包含休学/冻课/延期等关键词，也算做休学冻课；休学冻课是一个概念，不用拆分成两个值去看，直接汇总起来

Use this as the default for this report class.

### Sources

Source A: `drh_handover_plus FINAL WHERE _sign > 0`

Source B: `dev_stop_stu_record`

Join key / grain:

- use `order_no` from the source tables as `flow_no`
- aggregate by `order_no`
- do **not** expand by `union_id` unless the user explicitly asks for student-level broad matching

### Combined hit logic

A row counts as `休学冻课` if any of these are true:

```sql
drh_handover_plus.stop_study_status = 1
OR drh_handover_plus.stop_flag = 1
OR drh_handover_plus.class_camp_name LIKE '%休学%'
OR drh_handover_plus.class_camp_name LIKE '%冻课%'
OR drh_handover_plus.class_camp_name LIKE '%延期%'
OR dev_stop_stu_record.stop_flag = 1
```

Practical SQL shape:

```sql
hp AS (
    SELECT
        order_no AS flow_no,
        anyIf(union_id, union_id != '') AS union_id_hp,
        max(if(
            stop_study_status = 1
            OR stop_flag = 1
            OR class_camp_name LIKE '%休学%'
            OR class_camp_name LIKE '%冻课%'
            OR class_camp_name LIKE '%延期%',
            1,
            0
        )) AS stop_freeze_flag_hp,
        anyIf(
            class_camp_name,
            class_camp_name LIKE '%休学%'
            OR class_camp_name LIKE '%冻课%'
            OR class_camp_name LIKE '%延期%'
        ) AS keyword_class_camp_name
    FROM (
        SELECT *
        FROM drh_handover_plus FINAL
        WHERE _sign > 0
    )
    WHERE order_no != ''
      AND (
          stop_study_status = 1
          OR stop_flag = 1
          OR class_camp_name LIKE '%休学%'
          OR class_camp_name LIKE '%冻课%'
          OR class_camp_name LIKE '%延期%'
      )
    GROUP BY order_no
),
sr AS (
    SELECT
        order_no AS flow_no,
        anyIf(union_id, union_id != '') AS union_id_sr,
        max(if(stop_flag = 1, 1, 0)) AS stop_freeze_flag_sr,
        min(stop_time) AS first_freeze_time,
        max(stop_time) AS latest_freeze_time,
        count() AS freeze_record_cnt,
        anyIf(type, type != '') AS freeze_source,
        anyIf(nick_name, nick_name != '') AS nick_name,
        anyIf(camp_name, camp_name != '') AS freeze_camp_name,
        anyIf(sku, sku != '') AS freeze_sku
    FROM dev_stop_stu_record
    WHERE stop_flag = 1
      AND order_no != ''
    GROUP BY order_no
),
flags AS (
    SELECT
        coalesce(hp.flow_no, sr.flow_no) AS flow_no,
        coalesce(hp.union_id_hp, sr.union_id_sr) AS union_id_flag,
        if(ifNull(hp.stop_freeze_flag_hp, 0) = 1 OR ifNull(sr.stop_freeze_flag_sr, 0) = 1, 1, 0) AS stop_freeze_flag,
        hp.keyword_class_camp_name AS keyword_class_camp_name,
        if(hp.keyword_class_camp_name != '', 1, 0) AS keyword_hit_flag
    FROM hp
    FULL OUTER JOIN sr ON hp.flow_no = sr.flow_no
)
```

## Reporting rule: do not split 休学 / 冻课

For user-facing workbook sheets and summaries:

- Use `休学冻课订单数`, not separate `休学订单数` and `冻课订单数`.
- Do not output status buckets like `仅休学`, `仅冻课`, `休学+冻课` unless explicitly requested.
- A helper field like `关键词命中标记` / `关键词命中班级名称` is acceptable for auditability.
- Sheet names should prefer:
  - `休学冻课_KPI`
  - `休学冻课_SKU前后端`
  - `休学冻课_SKU汇总`
  - `休学冻课_前后端汇总`
  - `休学冻课_命中来源`
  - `休学冻课_金额分桶`
  - `休学冻课_订单明细`
- Avoid user-facing `休学冻课_状态拆分` unless the user asks to see source breakdown.

## Matching course order attributes

After building `休学冻课` flags, left join to `dwd_order_flow_df` to enrich:

- payment time
- pay/refund amount
- SKU
- frontend/backend
- camp name

Course paid-order enrichment filter:

```sql
main_first_level = '课程'
pay_status_name = '支付成功'
```

Keep unmatched `休学冻课` records. They should show as `未识别` for SKU/front-end fields and carry an explicit `是否匹配课程支付订单 = 0` / `matched_paid_course_order = 0`.

## Historical all-data convention

When the user says “时间范围调整一下，放宽到历史全部数据”, use an explicit broad bound for auditability, e.g.:

```python
START = '1970-01-01 00:00:00'
END = '<tomorrow 00:00:00>'
PERIOD_LABEL = '历史全量至<today>'
```

Include exact SQL in the workbook sheet `SQL与口径`.

## Verified result from 2026-05-08 corrected run

Workbook:

`~/.hermes/output/query_results/仅首款订单与休学冻课_独立口径_领导版_历史全量_补关键词_合并口径_20260508.xlsx`

Historical all-data through `2026-05-08`:

First-payment-only:

- rows / distinct flows: `137,023`
- students: `98,926`
- pay amount: `71,404,981.66`
- refund amount: `5,212,771.75`
- refund rate: `7.30%`

休学冻课 combined:

- rows / distinct flows: `13,623`
- students: `12,752`
- matched course paid orders: `13,288`
- pay amount: `33,460,645.48`
- refund amount: `2,577,336.79`
- refund rate: `7.70%`
- keyword-hit orders: `5,444`

Previous historical run before adding `class_camp_name` keywords had:

- `8,681` 休学冻课 orders

Corrected口径 added:

- `4,942` orders net

## Implementation pitfalls

### ClickHouse driver may prefix selected aliases

For complex CTE queries, `clickhouse_driver.Client.query_dataframe()` can return aliases like:

- `b_flow_no`
- `flow_pay_amount2`
- `hp_keyword_class_camp_name`

Normalize by stripping known table prefixes / suffix forms before downstream pandas logic.

### Convert default epoch timestamps before Excel export

If `DateTime('1970-01-01/1970-01-02')`-style defaults are exported directly, Excel/openpyxl may show confusing serial numbers. Convert date columns via pandas and blank default timestamps:

```python
for c in ['pay_time', 'refund_time', 'first_rest_time', 'latest_rest_time', 'first_freeze_time', 'latest_freeze_time']:
    if c in df.columns:
        df[c] = pd.to_datetime(df[c], errors='coerce')
        df.loc[df[c] <= pd.Timestamp('1970-01-02 00:00:00'), c] = pd.NaT
```

## Verification checklist

- `len(first) == first['flow_no'].nunique()`
- `len(rest) == rest['flow_no'].nunique()`
- KPI numeric cells are actual numeric types after reopening with `openpyxl`
- Rest-facing sheets do not contain old split headers:
  - `休学订单数`
  - `冻课订单数`
  - `休学标记`
  - `冻课标记`
  - `休学/冻课状态`
  - `休学或冻课订单数`
- Sheet names and headers reflect the combined concept `休学冻课`
