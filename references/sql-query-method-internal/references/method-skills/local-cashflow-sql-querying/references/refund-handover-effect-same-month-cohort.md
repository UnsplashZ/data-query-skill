# Same-month cohort refund-rate analysis for handover efficiency

Session pattern for user question: “盯交接流程效率之后，退费率是否有下降？”

## Source and default filters

Use ClickHouse `dwd_order_flow_df` for the main cohort denominator/numerator.

Default front-end scope used in the successful run:

```sql
pay_time >= toDateTime('<start_month> 00:00:00')
AND pay_time < toDateTime('<end_month_excl> 00:00:00')
AND pay_amount > 0
AND pay_status_name = '支付成功'
AND new_front_end_name LIKE '%前端%'
```

Main metric:

```text
同月 cohort 金额退费率 = 支付当月内发生的 refund_amount / 支付 GMV
```

For “4月订单在4月退费率、3月订单在3月退费率”, apply:

```sql
refund_amount > 0
AND refund_time >= toStartOfMonth(pay_time)
AND refund_time < addMonths(toStartOfMonth(pay_time), 1)
```

## Required board splits

When the user says “看前端订单分几个板块：总订单，课程+全款/尾款的订单”, provide at least:

1. `总订单`: all rows matching the front-end base filter.
2. `课程_全款尾款`: `main_first_level = '课程' AND pay_type_name IN ('全款','尾款')`.
3. Optional handover/high-ticket reference: add `total_original_price >= 1880` for high-order-price handover-sensitive scope.

For each board, export recent six full payment months and compare current month vs prior month / trailing averages.

## Handover dimension linkage

For process-efficiency judgment, left join handover data by `flow_no`, but dedupe handover rows first:

```sql
WITH handover AS (
  SELECT
    flow_no,
    minIf(handover_time, handover_time > toDateTime('1970-01-02 00:00:00')) AS handover_time,
    minIf(join_group_time, join_group_time > toDateTime('1970-01-02 00:00:00')) AS join_group_time,
    minIf(ast_friend_time, ast_friend_time > toDateTime('1970-01-02 00:00:00')) AS ast_friend_time,
    any(class_stage_name) AS class_stage_name,
    any(camp_group_name) AS camp_group_name
  FROM dwd_order_handover_df
  WHERE flow_no != ''
  GROUP BY flow_no
)
```

Then classify dimensions such as:

- `交接状态`: no handover / handed over but not joined / joined group or class
- `交接时效`: D0, D1, D2-D3, D4-D7, D8+, 未交接
- `入群时效`: D0, D1, D2-D3, D4-D7, D8+, 未入群
- `加微时效`: D0, D1, D2-D3, D4-D7, D8+, 未加微
- SKU as a confounder/control dimension

Use these dimensions to judge whether the observed refund-rate movement is concentrated in covered vs uncovered handover populations.

## Output structure

Prefer an Excel workbook under:

`~/.hermes/output/query_results/refund-handover-effect/`

Sheets used successfully:

- `口径说明`
- `核心结论_月度对比`
- `最近半年月度大数`
- `逐日累计退费率`
- `交接维度明细`
- `交接维度摘要`

Verify by reopening with `openpyxl` and checking sheet names, row counts, and numeric cell types for rates/GMV.

## Interpretation rule

Do not claim causality from this observational cut.

A stable conclusion shape:

- If total/front-end refund rate rises but “已入群/入班” falls, say: **交接承接到位的人群退费率有下降信号；整体大盘未下降，可能被无交接/未入群人群拉高。**
- If both overall and covered handover groups fall, say the pattern is **consistent with** handover efficiency helping, but still not proof of sole causality.
- Always separate amount refund-rate from order refund-rate if both are shown.
