---
name: handover-stats-report-method
description: Understand and reuse the user's handover detail aggregation method from the retired analysis project. Focus on converting detail rows into funnel flags and team/camp/date Excel summaries with non-refund denominators.
---

# Handover stats report method

Use this when the task is to turn handover detail rows into a multi-view Excel funnel summary across date, camp, and sales-team dimensions.

## Problem this method solves
Summarize where handover flow is getting stuck: acceptance, camp selection, WeChat addition, and class start progression.

## Source material
- `~/.hermes/docs/projects/analysis-methods/handover-stats-report-method.md`
- Original source (may be deleted later): `/Users/zheng/dev/analysis/scripts/handover_stats_report.py`

## Core business rules
1. Standardize text and parse key timestamps:
   - payment time
   - refund time
   - WeChat add time
   - class start date
   - camp-entry date
2. Build funnel / operating-result flags:
   - 未承接
   - 未选期
   - 已选期
   - 当前加微 / 已加微
   - 选期加微
   - 已开课
   - 衔接课开课 / 衔接课开课率
   - 24H交接
   - 3天内交接
   - 7天内交接
   - 7天选期
   - 7天加微
3. Price bucket rule:
   - raw price >= 2381 -> `2980`
   - otherwise -> `1880`
4. Started-class rule:
   - class date exists
   - and current date has reached/passed class date
5. Handover timing is based on `加入营期日期 - 支付时间`.
6. Funnel-rate denominator is `非退费订单数`, not total orders.
7. Second-stage handover/WeChat summary only includes rows that are:
   - non-refund
   - accepted
   - have second-stage camp or manager information

## Outputs to preserve
Excel workbook with sheets such as:
- 按支付日期
- 按前端营期
- 按营期销售团队
- 营期团队转化率
- 营期团队转化率汇总
- 二阶承接加微汇总

## Why this matters
Using total orders as denominator distorts operational funnel rates. This method deliberately keeps process metrics anchored to non-refund orders so teams and camps are comparable.

## Extended business rules preserved from memory

### Cohort handover cutoff
- Cohort handover cutoff uses `pay_month_end + 7 days`.

### Historical first-payment / frozen-class reports
Use these when the user asks about 历史首款、休学冻课、未分配 or related handover-detail breakdowns:
- Preserve the existing summary layout unless the user asks to redesign it.
- Amount and percentage columns should remain numeric, not strings such as `xx万` or `12%`.
- Amount buckets should sort ascending.
- 休学/冻课 can include rows where `service_camp_name` is empty when `stop_study_status = 1`.
- 未分配 should use only `tock_handover_plus` rows with empty service camp / service person, and should exclude 休学/冻课 rows.
- Do not UNION `tock_order` for the 未分配 logic unless the user explicitly changes the method.
- Detail exports often need these supplemental columns: 成交人、交接学管、手机号、商品名称、课包价格、成交营期阶段.

##交接数据看板卡片口径

For the Feishu 5-SKU handover dashboard card, see `references/handover-daily-card-kpi-sources.md` before editing or regenerating the card. The card uses a narrower operational KPI set than the full report: 开课率 comes from 开课封板 (`开课节点 = 开课封板`, `已开课人数 / 订单数`), while 加微率 and 选期率 come from 加微封板 (`当前节点 = 加微封板`). `selected_wechat` is legacy compatibility only and should not reappear as a main displayed metric.

## 封板营期渠道月度漏斗报表

When the user asks for 封板营期按月/分渠道 metrics such as leads、加微率、转化率、ROI、D1-D6 到课、D1-D9 逐日转化率/课中转化率, use `references/channel-camp-monthly-funnel-report.md`. The reusable pattern is: ClickHouse, month by `drh_live_camp_date.end_time`, leads/attendance/cost from `tock_applet_user`, GMV/conversion from `drh_order FINAL`, and output two numeric Excel sheets. If the user says only 声乐 SKU 前端 or provides a desktop sample with `月汇总` / `月x渠道汇总`, keep that exact two-sheet shape and 25-column summary layout; do not default to all-SKU or 60-column debug output.

When reviewing a Feishu narrative/analysis document against this Excel output, also use `references/channel-camp-monthly-funnel-review-checks.md`. Key pitfalls: `转化率` may be `GMV / 2980 / leads` rather than pure buyer conversion; `课下转化率 = 总转化率 - 课中转化率` is an inferred GMV-standardized metric; separate channel-mix effects from within-channel efficiency; split total ROI from paid-channel ROI; and verify whether monthly GMV equals the sum of channel-level GMV before making precise channel ROI claims.

## 交接实时同步 SQL 口径维护

实时同步 SQL 路径：`/Users/zheng/.hermes/sql/projects/handover-realtime-sync/交接数据-实时.sql`，配置入口：`/Users/zheng/.hermes/python/projects/handover-realtime-sync/config.yaml`。

当前正价课基础筛选保留价格门槛和支付类型：`T1.pay_type IN (2, 3)` 与 `round(ifNull(T1.total_price, 0) / 100, 4) >= {{goods_price}}`；课程筛选保持 `T3.first_level_name = '课程'`。不要把“欢乐颂”加到这里的商品名称/课程判断里。

“正价课开课学员”判断在后面的 `tock_ast_process_data` 子查询（a3）里，通过 `course_name` 的 `multiMatchAny(...)` 判断首节正价课开课课程。这里已加入 `'.*欢乐颂.*'`、`'.*先导课.*'`，并保留 `study_time > 0`。后续同类开课关键词也应加在这个 a3 子查询的课程名列表里，不要放宽价格门槛、SKU/camp_sku 或日期条件。

验证时可运行：`/opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python /Users/zheng/.hermes/python/projects/handover-realtime-sync/test_run_sync_metrics.py`。该环境可能没有 pytest；直接运行 unittest 文件即可。不要用完整同步 SQL 做 `EXPLAIN SYNTAX` 当作常规验证，ClickHouse 21.8 可能因展开后 AST 过大报 `AST is too big`，即使生产查询此前可运行。

## Common mistakes
- using total orders as denominator for selection/WeChat/start rates
- mixing refunded rows into funnel conversion
- treating any non-empty class date as already started
- combining second-stage accepted users with the full detail population
- counting frozen-class rows as 未分配 just because service camp or service person is empty
- using textified amount/percentage cells in Excel outputs when numeric cells are required
- for the handover dashboard card, using 衔接课开课人数 or 加微封板 rows to calculate the displayed 开课率
- regenerating a Feishu interactive card without clicking SKU buttons and checking patch logs
