# 历史首款 / 冻课学员合并口径与飞书四表整理（2026-05-08）

## Trigger

Use this reference when the user asks to rebuild or explain the historical `仅首款订单 / 休学冻课` report, especially wording like:

- “历史全部数据”
- “休学冻课/冻课是一个概念，不用拆分”
- “class_camp_name 包含休学/冻课/延期也算”
- “整理成四个 sheet 写入飞书表格”

## Corrected business definition

The user corrected the earlier split view: **休学冻课 / 冻课 should be treated as one combined risk concept** for this report. Do not expose separate `休学订单数` / `冻课订单数` / `仅休学` / `仅冻课` breakdowns unless explicitly requested.

A record is included in the combined `休学冻课` pool when any one condition is true:

```sql
-- from drh_handover_plus FINAL WHERE _sign > 0
stop_study_status = 1
OR stop_flag = 1
OR class_camp_name LIKE '%休学%'
OR class_camp_name LIKE '%冻课%'
OR class_camp_name LIKE '%延期%'

-- from dev_stop_stu_record
stop_flag = 1
```

Join / grain rules:
- Grain: one row per `order_no` / `flow_no` after combining sources.
- Merge `drh_handover_plus` and `dev_stop_stu_record` by `order_no` with a full outer join.
- Then left join `dwd_order_flow_df` by `flow_no` only to enrich payment/SKU/frontend fields.
- The enrichment source should filter paid course orders:
  - `main_first_level = '课程'`
  - `pay_status_name = '支付成功'`
- Unmatched stop/freeze records should remain in the detail; mark match flag as 0 and leave SKU/frontend as `未识别` where needed.

Historical full-data window used in this session:

```text
START = '1970-01-01 00:00:00'
END   = '2026-05-09 00:00:00'  -- label as 历史全量至2026-05-08
```

## Corrected output shape

When the user asks to “整理一下结果，做成四个sheet”, use exactly these four sheet titles:

1. `首款订单汇总`
2. `首款订单明细`
3. `冻课汇总`
4. `冻课明细`

Despite the tab label `冻课`, the data should follow the combined `休学冻课` definition above unless the user explicitly narrows the definition.

Recommended source workbook from this session:

```text
~/.hermes/output/query_results/仅首款订单与休学冻课_独立口径_领导版_历史全量_补关键词_合并口径_20260508.xlsx
```

Four-sheet fallback workbook generated locally:

```text
~/.hermes/output/query_results/20260508_历史首款_冻课学员_四Sheet整理版.xlsx
```

Script locations:

```text
~/.hermes/python/projects/first-payment-only/make_independent_leader_report_history_keyword_combined.py
~/.hermes/python/projects/first-payment-only/write_history_keyword_combined_to_feishu.py
```

## Verified metrics from corrected run

First-payment-only pool:
- rows / distinct flows: `137,023`
- students: `98,926`
- pay amount: `71,404,981.66`
- refund amount: `5,212,771.75`
- refund rate: `7.30%`

Combined `休学冻课` pool:
- rows / distinct flows: `13,623`
- students: `12,752`
- matched paid course orders: `13,288`
- pay amount: `33,460,645.48`
- refund amount: `2,577,336.79`
- refund rate: `7.70%`
- keyword-hit orders from `class_camp_name`: `5,444`

Earlier split-only run had `8,681` stop/freeze records, so the keyword + combined correction added `4,942` records.

Four-sheet row counts:
- `首款订单汇总`: `85`
- `首款订单明细`: `137,023`
- `冻课汇总`: `54`
- `冻课明细`: `13,623`

## Feishu write attempt and permission pitfall

Target user-facing Wiki link:

```text
<REDACTED_FEISHU_URL>
```

Resolved underlying sheet token:

```text
JsJssm2cNhbXWWtmXracroh8neg
```

The app could resolve the Wiki node but failed when trying to create/rename tabs:

```text
sheets_batch_update HTTP 403
Feishu code=91403
msg=Forbidden
```

Interpretation:
- Wiki/node read or resolution permission is not enough.
- The Open Platform app needs edit permission on the underlying Sheet to create/rename tabs and write values.

Required response pattern when this happens:
1. State the exact Feishu API failure and token resolved.
2. Do not claim write success.
3. Save the intended four-sheet workbook locally and attach/send it if useful.
4. Tell the user to grant edit permission to the Hermes Feishu app, then rerun `write_history_keyword_combined_to_feishu.py`.

## Implementation notes

Feishu Sheets write API has a per-write limit around 5000 rows. Chunk detail writes (e.g. 4500 rows per `PUT /values`). Before writing:
- resolve Wiki token via `wiki/v2/spaces/get_node`;
- query tabs with `sheets/v3/spreadsheets/{token}/sheets/query`;
- create/rename tabs with `sheets_batch_update`;
- expand dimensions with `dimension_range`;
- clear stale values in chunks;
- write headers + rows in chunks;
- read back `A1` headers to verify.

If write permission fails at any step, stop and report the exact API error rather than falling back to browser assumptions.
