# 声乐 GMV 和退费日报：声乐-月课独立阶段

Session date: 2026-05-11

## Context

Target Feishu workbook:
- `<REDACTED_FEISHU_URL>`
- underlying spreadsheet token used by script: `<REDACTED_FEISHU_SPREADSHEET_TOKEN>`
- sheet id: `a5qFM6`
- visible tab: `GMV和退费`

Cron/report script:
- `/Users/zheng/.hermes/python/projects/gmv-daily/vocal_gmv_refund_daily/run_job.py`
- cron name: `声乐GMV和退费日报`

## Correct business handling

The report has two different concepts that must not be mixed:

1. `后端整体`
   - all `cci3_name = '声乐'` rows in the report date window
   - **no `class_stage_name IN (...)` restriction** after the 2026-05-11 correction
   - includes rows whose `dim_camp_view.class_stage_name` is outside the visible 二/三/四/五 columns

2. visible stage columns
   - fixed display order only:

```python
STAGE_ORDER = ['二阶营期', '三阶营期', '四阶营期', '五阶营期', '张大伟月课']
```

The `声乐-月课` rows are a separate attribution bucket and should be displayed as their own stage/column, not folded into `五阶营期`.

Correct ordinary 声乐 order SQL shape:

```sql
SELECT a.flow_no
,a.pay_amount_uhc
,c.class_stage_name
FROM dwd_order_flow_df a
LEFT JOIN dim_camp_view c
ON a.camp_id = c.camp_id
WHERE a.cci3_name = '声乐'
AND a.dt >= '{start_date}'
AND a.dt <= '{end_date}'
```

Correct ordinary 声乐 refund SQL shape:

```sql
SELECT a.flow_no
,a.refund_amount_uhc
,c.class_stage_name
FROM dwd_order_refund_df a
LEFT JOIN dim_camp_view c
ON a.camp_id = c.camp_id
WHERE a.cci3_name = '声乐'
AND a.dt >= '{start_date}'
AND a.dt <= '{end_date}'
```

Correct month-course SQL branch for orders:
```sql
SELECT a.flow_no
,a.pay_amount_uhc
,'张大伟月课' AS class_stage_name
FROM dwd_order_flow_df a
WHERE a.cci3_name = '声乐-月课'
AND a.dt >= '{start_date}'
AND a.dt <= '{end_date}'
```

Correct month-course SQL branch for refunds:
```sql
SELECT a.flow_no
,a.refund_amount_uhc
,'张大伟月课' AS class_stage_name
FROM dwd_order_refund_df a
WHERE a.cci3_name = '声乐-月课'
AND a.dt >= '{start_date}'
AND a.dt <= '{end_date}'
AND to_date(a.pay_time) >= '{start_date}'
```

Preserve the existing refund `pay_time` guard unless the user explicitly changes the口径.

## Aggregation rule after removing stage filter

After removing the ordinary 声乐 `class_stage_name IN (...)` filters, do **not** compute `后端整体` from the reindexed visible stage DataFrame. That would drop non-visible stages from the overall total.

Correct pattern:

1. aggregate all returned rows by `营期阶段`
2. merge order/refund summary
3. compute `后端整体` totals from this full `summary`
4. only then reindex `summary` to the visible `STAGE_ORDER` for stage columns

Observed fixed script lines on 2026-05-11:
- totals are computed before `.reindex(STAGE_ORDER, fill_value=0)`
- `cols[0]` is the full overall total
- subsequent `cols` are the visible stage values only

## Feishu write ranges

After adding `张大伟月课`, the sheet write range must expand from `B:F` to `B:G`:

```python
value_ranges = [
    {'range': f'{SHEET_GMV}!B1:B1', 'values': [[excel_date]]},
    {'range': f'{SHEET_GMV}!B2:G2', 'values': [['后端整体', '二阶', '三阶', '四阶', '五阶', '张大伟月课']]},
    {'range': f'{SHEET_GMV}!B3:G7', 'values': gmv_rows},
]
```

## Verification pattern

Preferred live run:

```bash
eval "$(conda shell.bash hook)" && conda activate hermes-sql && \
  python /Users/zheng/.hermes/python/projects/gmv-daily/vocal_gmv_refund_daily/run_job.py
```

If proxy contamination or shell wrapper issues appear, use the absolute interpreter and unset proxies:

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy \
  /opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python \
  /Users/zheng/.hermes/python/projects/gmv-daily/vocal_gmv_refund_daily/run_job.py
```

Then read back `a5qFM6!B1:G7` via Feishu Sheets API to verify the date/header/values were written.

Observed verification before removing the ordinary stage filter on 2026-05-11 for window `2026-05-01 ~ 2026-05-10`:
- order rows: `404`
- refund rows: `115`
- `张大伟月课` was present as a column but all five metric values were `0` for that period.

Observed verification after removing the ordinary stage filter on 2026-05-11 for the same window:
- order rows: `1005`
- refund rows: `191`
- Feishu readback `a5qFM6!B1:G7`:

| 指标 | 后端整体 | 二阶 | 三阶 | 四阶 | 五阶 | 张大伟月课 |
|---|---:|---:|---:|---:|---:|---:|
| GMV订单数 | 1005 | 110 | 265 | 27 | 2 | 0 |
| GMV_归属 | 1893742.6 | 206739 | 790538 | 168083 | 12579 | 0 |
| 退款订单数 | 191 | 77 | 24 | 13 | 1 | 0 |
| 退款_归属 | 325337 | 155454 | 54746 | 32939.2 | 1680 | 0 |
| 净GMV | 1568405.6 | 51285 | 735792 | 135143.8 | 10899 | 0 |

Interpretation: `后端整体` now intentionally exceeds the visible 二/三/四/五/张大伟月课 columns because non-visible `声乐` stages are included in the overall total.

## Current restored behavior verified on 2026-05-18

A later check of the live script found the 2026-05-11 “remove ordinary stage filter” behavior was not the final state. The current script at:

`/Users/zheng/.hermes/python/projects/gmv-daily/vocal_gmv_refund_daily/run_job.py`

has restored ordinary 声乐 stage filters and computes `后端整体` from the visible `STAGE_ORDER` buckets after reindexing.

Current cron and target mapping:
- cron job name: `声乐GMV和退费日报`
- job id: `28862874b814`
- schedule: `5 10 * * *`
- child command: `/opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python /Users/zheng/.hermes/python/projects/gmv-daily/vocal_gmv_refund_daily/run_job.py`
- target sheet id: `a5qFM6`
- user-facing wiki URL observed: `<REDACTED_FEISHU_URL>`
- script spreadsheet token observed: `<REDACTED_FEISHU_SPREADSHEET_TOKEN>`

Current ordinary 声乐 order SQL shape:

```sql
SELECT a.flow_no
,a.pay_amount_uhc
,c.class_stage_name
FROM dwd_order_flow_df a
LEFT JOIN dim_camp_view c
ON a.camp_id = c.camp_id
WHERE a.cci3_name = '声乐'
AND c.class_stage_name IN ('二阶营期','三阶营期','四阶营期','五阶营期')
AND a.new_front_end_name LIKE '%后端%'
AND a.dt >= '{start_date}'
AND a.dt <= '{end_date}'
```

Current ordinary 声乐 refund SQL shape:

```sql
SELECT a.flow_no
,a.refund_amount_uhc
,c.class_stage_name
FROM dwd_order_refund_df a
LEFT JOIN dim_camp_view c
ON a.camp_id = c.camp_id
WHERE a.cci3_name = '声乐'
AND c.class_stage_name IN ('二阶营期','三阶营期','四阶营期','五阶营期')
AND a.new_front_end_name LIKE '%后端%'
AND a.dt >= '{start_date}'
AND a.dt <= '{end_date}'
```

Current month-course branch is still separate:

```sql
-- orders
SELECT a.flow_no
,a.pay_amount_uhc
,'张大伟月课' AS class_stage_name
FROM dwd_order_flow_df a
WHERE a.cci3_name = '声乐-月课'
AND a.dt >= '{start_date}'
AND a.dt <= '{end_date}'

-- refunds
SELECT a.flow_no
,a.refund_amount_uhc
,'张大伟月课' AS class_stage_name
FROM dwd_order_refund_df a
WHERE a.cci3_name = '声乐-月课'
AND a.dt >= '{start_date}'
AND a.dt <= '{end_date}'
AND to_date(a.pay_time) >= '{start_date}'
```

Current aggregation:
- `order_sum`: group by `营期阶段`, count `flow_no`, sum `pay_amount_uhc`
- `refund_sum`: group by `营期阶段`, count `flow_no`, sum `refund_amount_uhc`
- merge, compute `净GMV = GMV_归属 - 退款_归属`
- reindex to `['二阶营期', '三阶营期', '四阶营期', '五阶营期', '张大伟月课']`
- compute `后端整体` as the sum of the reindexed visible buckets

Important interpretation update:
- Do **not** state that `后端整体` intentionally includes non-visible stages unless the script is changed again.
- If the user asks why the reference conflicts with current code, treat this as a historical口径 change: 2026-05-11 broadened it, then a later restore brought the filter back.
- Always inspect the live script before explaining this task because the口径 has changed before.

Current verification performed on 2026-05-18:

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy \
  /opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python -m py_compile \
  /Users/zheng/.hermes/python/projects/gmv-daily/vocal_gmv_refund_daily/run_job.py
```

Result: syntax check passed. No live ODPS/Feishu write was run in that session.

## Current supplemental 罗一豪二阶 column added on 2026-05-18

The live script now includes an extra supplemental column after `张大伟月课` for the user's requested four 二阶 track groups:

```python
SUPPLEMENTAL_STAGE = '罗一豪二阶'
SUPPLEMENTAL_CAMP_GROUPS = [
    '声乐二阶-20260203-院长班',
    '声乐二阶-20260203-院长班(二)',
    '声乐二阶-20260127-院长特惠班',
    '声乐二阶-20260210-院长特惠班',
]
```

Important handling:
- This is an **extra supplemental column**, not a new member of `STAGE_ORDER`.
- `后端整体` must remain the sum of only the existing visible `STAGE_ORDER` buckets: 二阶/三阶/四阶/五阶/张大伟月课.
- Feishu write range is now `B:H`:

```python
{'range': f'{SHEET_GMV}!B2:H2', 'values': [['后端整体', '二阶', '三阶', '四阶', '五阶', '张大伟月课', SUPPLEMENTAL_STAGE]]}
{'range': f'{SHEET_GMV}!B3:H7', 'values': gmv_rows}
```

Supplemental order SQL shape:

```sql
SELECT a.flow_no
,a.pay_amount_uhc
,'罗一豪二阶' AS class_stage_name
FROM dwd_order_flow_df a
LEFT JOIN dim_camp_view c
ON a.camp_id = c.camp_id
WHERE c.camp_group_name IN (
  '声乐二阶-20260203-院长班',
  '声乐二阶-20260203-院长班(二)',
  '声乐二阶-20260127-院长特惠班',
  '声乐二阶-20260210-院长特惠班'
)
AND a.cci3_name = '声乐'
AND a.new_front_end_name LIKE '%后端%'
AND a.dt >= '{start_date}'
AND a.dt <= '{end_date}'
```

Supplemental refund SQL uses the same filters on `dwd_order_refund_df` and `dim_camp_view`; it intentionally has **no** `to_date(pay_time)` guard, matching ordinary 声乐后端 refund logic rather than the month-course branch.

Observed live run on 2026-05-18 for window `2026-05-01 ~ 2026-05-17`:
- existing order rows: `679`
- existing refund rows: `210`
- supplemental 罗一豪二阶 order rows: `74`
- supplemental 罗一豪二阶 refund rows: `7`
- supplemental values: `[GMV订单数=74, GMV_归属=120901.0, 退款订单数=7, 退款_归属=9471.0, 净GMV=111430.0]`
- script completed and wrote `a5qFM6` successfully.

Verification command used before live run:

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy \
  /opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python -m py_compile \
  /Users/zheng/.hermes/python/projects/gmv-daily/vocal_gmv_refund_daily/run_job.py
```

- Old script behavior mapped `cci3_name='声乐-月课'` to `'五阶营期' AS class_stage_name`, which made `五阶` include month-course attribution. Do not preserve that when the user asks for `声乐-月课` as an independent stage.
- After removing the ordinary `class_stage_name IN (...)` restrictions, non-visible stages will appear in the raw grouped summary. Reindexing for visible columns is still correct, but only **after** computing the overall totals.
- Do not present column sums as a reconciliation check for `后端整体` after this correction; the overall is deliberately broader than the visible stage columns.
- As of 2026-05-18, the live script has restored the ordinary stage filter, so column sums should reconcile to `后端整体` under the current script.
