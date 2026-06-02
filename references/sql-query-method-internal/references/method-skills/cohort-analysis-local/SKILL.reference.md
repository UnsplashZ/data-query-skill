---
name: cohort-analysis-local
description: Run the user's migrated local cohort refund analysis workflow from Hermes without depending on OpenClaw. Use when the user wants cohort退费矩阵 or下月退费预测 from exported CSV data.
---

# Local cohort analysis

Use this for the user's migrated cohort refund analysis workflow.

Files:
- Script: `~/.hermes/python/projects/cohort-analysis/run_cohort.py`
- Project README: `~/.hermes/python/projects/cohort-analysis/README.md`

## Environment
Run in conda env `hermes-sql`.

## Command
```bash
eval "$(conda shell.bash hook)"
conda activate hermes-sql
python ~/.hermes/python/projects/cohort-analysis/run_cohort.py \
  --data-dir /path/to/data_dir \
  --skus 声乐,钢琴 \
  --predict-month 2026-04
```

## Notes
- `data_dir` must contain `订单明细.csv` and `退款明细.csv`.
- The script outputs an Excel workbook with prediction summary and cohort matrices.
- Optional GMV override is supported via `--march-gmv 大前端:7000000,大后端:12000000`.

## 5月 / future-month forecast workflow used in 2026-04

For requests asking for a future month with these three metrics:
- 当月产生的退费金额
- 当月订单在当月退费率
- 当月订单预计最终退费率（6个月）

Use the dedicated Hermes scripts:

```bash
/opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python \
  ~/.hermes/python/projects/cohort-analysis/fetch_cashflow_orders_refunds.py \
  --start-date 2024-01-01 \
  --end-date YYYY-MM-DD \
  --suffix YYYYMMDD_from2024

/opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python \
  ~/.hermes/python/projects/cohort-analysis/may_refund_forecast.py
```

Current implementation details:
- source: ODPS cashflow `订单明细.sql` + `退款明细.sql`
- default scope for the May forecast script after 2026-04-24 update: `sku in ('声乐','钢琴','朗诵','书画','口琴','声乐IP季课')` and `前后端 in ('大前端','大后端')`; user corrected the intended category from `书法` to `书画`
- training lag-rate window: complete refund months `2025-04` through `2026-03`, weighted by cohort GMV
- future-month generated refund = existing historical cohorts expected to refund in that month + new-month cohort lag0 refund
- same-month refund rate = lag0 rate
- 6-month final refund rate = cumulative lag0 through lag5
- Current `预测汇总` sheet is formula-driven: users can edit `4月最终GMV(人工填)` and `5月预算GMV(人工填)`; `5月产生退费金额预测` uses the Excel formula `历史至3月cohort预计5月退款 + 4月最终GMV×lag1退费率 + 5月预算GMV×lag0退费率`.
- Default editable values in the current script: `4月最终GMV(人工填)=4月MTD GMV/23×30`; `5月预算GMV(人工填)=4月MTD GMV/23×31`.
- Export path pattern: `~/.hermes/output/query_results/cohort_may_forecast/2026年5月cohort退费预测_多SKU.xlsx`

### April 2026 cutoff backtest

For the user's request “用截止3月31日的数据做一份4月预测，看和实际差异”, use:

```bash
/opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python \
  ~/.hermes/python/projects/cohort-analysis/april_refund_backtest.py
```

Current backtest script:
- source data dir: `~/.hermes/output/projects/cashflow-core/data_sources/odps/cohort_may_forecast-20260424_from2024-2024-01-01-2026-04-23`
- prediction month: `2026-04`
- forecast cutoff: `2026-03-31`
- actual observation end: `2026-04-23`
- training lag-rate window: complete refund months `2025-04` through `2026-03`, weighted by cohort GMV
- formula in `预测汇总`: `历史至2月cohort预计4月退款 + 3月最终GMV×lag1退费率 + 4月预算GMV×lag0退费率`
- editable yellow inputs: `3月最终GMV(人工填)` and `4月预算GMV(人工填)`
- default `4月预算GMV(人工填)` is actual April MTD GMV through 2026-04-23 for backtest comparison, and the note in the workbook calls out that this is a rate/lag-assumption backtest holding actual MTD GMV.
- output path: `~/.hermes/output/query_results/cohort_april_backtest/2026年4月cohort退费预测_截至3月31日_多SKU.xlsx`

### Product-type-aware May forecast

After the April backtest showed overprediction, the user asked to apply the product-type-aware logic to May. Use:

```bash
/opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python \
  ~/.hermes/python/projects/cohort-analysis/may_refund_forecast_by_product_type.py
```

Current script details:
- output path: `~/.hermes/output/query_results/cohort_may_forecast/2026年5月cohort退费预测_按商品类型_多SKU.xlsx`
- lag-rate grain: `SKU × 前后端 × 商品类型(订单明细.一级分类) × lag`; after 2026-04-24 update, SKUs `口琴` and `声乐IP季课` are combined across front/back into `前后端='合计'` before all grouping/rate/prediction calculations, while other SKUs remain split into 大前端/大后端
- training refund months: `2025-04` through `2026-03`, weighted by cohort GMV with overall-lag fallback
- detail formula: `历史至3月cohort预计5月退款 + 4月最终GMV×lag1 + 5月预算GMV×lag0`
- default editable values: `4月最终GMV=4月MTD GMV(截至4/23)/23×30`; `5月预算GMV=4月MTD GMV(截至4/23)/23×31`
- sheets include `预测汇总` aggregated from `商品类型明细`, plus formula-driven `商品类型明细`, `5月预测构成`, `lag退费率假设`, `历史月度GMV`, `训练样本`.
