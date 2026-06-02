# 声乐前端 cohort 退费率图与3-4月异常归因（2026-05）

Use this reference when rebuilding or explaining the user's 声乐前端 cohort refund-rate charts / boss-facing analysis around 2026-03 and 2026-04.

## Correct chart口径 after user correction

For the chart that should match the user's handover-optimization report, use **same-month natural-day observation**, not D0-D90 elapsed days and not current cumulative refund on pay-day rows.

Filters:
- `pay_status_name = '支付成功'`
- `cci3_name = '声乐'`
- `new_front_end_name LIKE '%前端%'`
- scope 1: all orders
- scope 2/core: additionally:
  - `main_first_level = '课程'`
  - `total_original_price >= 1880`
  - `pay_type_name IN ('全款','尾款')`

Axis:
- `月内自然日 1-31`

Metric:
- denominator: cumulative paid GMV in the payment month up to natural day N, from `dwd_order_flow_df.pay_time/pay_amount`
- numerator: refund GMV for orders in the same payment month whose `refund_time` is also within that same payment month and on/before natural day N, from `tock_dwd_order_refund_df.refund_time/refund_amount`
- rate: `同一支付月内截至当日发生的退款GMV / 截至当日该支付月累计GMV`

Critical pitfall:
- Do **not** use `dwd_order_flow_df.refund_amount` alone for a natural-day observed trend. That field reflects the order's current accumulated refund and will allocate later refunds back to the original pay day. This made 2026-03 day 1 look abnormally high because 3/1 paid orders later refunded on 3/24, 3/28, 4/8, 4/9, etc. were counted on day 1.
- Use `tock_dwd_order_refund_df.refund_time` whenever the question is “as of the same natural day in month”.
- D0-D90 elapsed-day cohort charts are a different metric and must be labeled as such; do not compare their values directly with monthly handover reports.

## Verified headline values for same-month natural-day口径

Historical baseline used in the boss report: 2025-01 through 2026-02 weighted by GMV.

All 声乐前端 orders:
- historical baseline: `1.21%`
- 2026-03: `3.29%` (`+2.08pp`, excess refund about `16.65万`)
- 2026-04: `2.90%` (`+1.69pp`, excess refund about `6.57万`)

Core `课程 + 1880+ + 全款/尾款`:
- historical baseline: `0.91%`
- 2026-03: `3.12%` (`+2.20pp`, excess refund about `13.74万`)
- 2026-04: `2.44%` (`+1.53pp`, excess refund about `4.48万`)

Business wording:
- Say: `3月开始进入显著高退费区间；4月较3月回落，但仍处于历史高位。`
- Do **not** say: `4月退费低`.

## 3-4月异常归因 summary

2026-03 main pattern:
- mostly front-end transaction / expectation quality rather than pure handover absence
- concentrated in:
  - `BD1-KOL`
  - `李聿为` / `汪国炳`
  - `声乐院长特别班` / `开开华彩·声乐系统·1880`
  - `2980档` / `1880档`
  - `全款`
  - specific camps such as `声乐443.5.ZM.0223`, `声乐444.4.ZM.0226`, `声乐446.5.ZM.0305`, `声乐449.6.ZM.0316`

Examples from the deep dive:
- `BD1-KOL × 李聿为 × 声乐院长特别班 × 声乐449.6.ZM.0316 × 2980档 × 全款`: 16 orders / GMV 47,680 / refund 8,840 / rate 18.54%
- `BD1-KOL × 汪国炳 × 声乐院长特别班 × 声乐444.4.ZM.0226 × 2980档 × 全款`: 15 orders / GMV 44,700 / refund 7,941 / rate 17.77%

2026-04 main pattern:
- not broad front-end explosion; risk shifted to handover completion
- `已入群/入班` improved materially
- `有交接未入群` became the high-risk bucket

Verified handover-status rates:
- all orders, 2026-04:
  - `已入群/入班`: 1.46%
  - `无交接记录`: 4.73%
  - `有交接未入群`: 9.70%
- core orders, 2026-04:
  - `已入群/入班`: 1.43%
  - `有交接未入群`: 29.94%

Interpretation:
- 3月：优先复盘 `BD1-KOL × 李聿为/汪国炳 × 院长班/1880系统课 × 高价全款 × 特定营期` 的成交质量、承诺边界、家庭/时间确认。
- 4月：重点治理交接后未入群/未入班，不要只看“是否有交接记录”。

## Local outputs generated in the session

- Chart/workbook, 2025-to-current same-day natural-day口径:
  - `/Users/zheng/.hermes/output/query_results/cohort_refund_rate/声乐前端cohort退费率_cci3_月内自然日_同日观察口径_2025年至今_20260507_142808.png`
  - `/Users/zheng/.hermes/output/query_results/cohort_refund_rate/声乐前端cohort退费率_cci3_月内自然日_同日观察口径_2025年至今_20260507_142808.xlsx`
- Attribution workbook:
  - `/Users/zheng/.hermes/output/query_results/cohort_refund_rate/声乐前端退费率_20260304异常归因分析.xlsx`
- Deep-dive workbook:
  - `/Users/zheng/.hermes/output/query_results/cohort_refund_rate/声乐前端退费率_20260304下钻分析.xlsx`
- Boss-facing Feishu report assets:
  - `/Users/zheng/.hermes/output/query_results/cohort_refund_rate/report_assets/`

## Boss-facing report structure learned from user's reference folder

The user's old专项分析 PPTs generally follow:
1. title + context / purpose / data口径;
2. conclusion-first headline;
3. trend or large-number evidence;
4. stepwise attribution by dimensions;
5. statistical or controlled comparison only when needed;
6. appendix/details.

For a Feishu Docx boss report, use:
- KPI summary image first;
- short口径 paragraph;
- concise bullets with exact percentages/pp/excess refund amounts;
- 2-4 charts, not raw table dumps;
- recommended actions separated by 3月 front-end成交质量 vs 4月交接未入群治理.

Feishu doc written in this session:
- `<REDACTED_FEISHU_URL>`
- underlying docx id observed: `HY1wdsAK0ocf9jxhRCocgawvnbb`
- permission update calls may fail even when document content/image writes succeed; verify by raw content and image block counts rather than assuming permission-call failure means write failure.
