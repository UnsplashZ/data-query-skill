---
name: refund-report-method
description: Understand and reuse the user's refund diagnosis method from the retired analysis project. Focus on front/back-end segmentation, lifecycle/process timing, reason taxonomy, text-theme extraction, payment-background comparison, and report-style business diagnosis.
---

# Refund diagnosis report method

Use this when the goal is to explain why refunds are happening and what operational action to prioritize, not just compute a refund rate.

## Problem this method solves
Turn refund details into an operating diagnosis that distinguishes:
- front-end vs back-end refund patterns
- payment-mechanism problems vs delivery/fit problems
- structural signals vs text evidence
- historical backlog vs current-month noise

## Source material
- `~/.hermes/docs/projects/analysis-methods/refund-report-method.md`
- Original source (may be deleted later): `/Users/zheng/dev/analysis/scripts/refund_report.py`

## Core business rules
1. Normalize segment labels:
   - `大前端`, `大前端-华彩乐园` -> front-end
   - `大后端`, `大后端-华彩乐园` -> back-end
2. Analyze three structural layers:
   - refund count / amount / avg refund
   - lifecycle: `支付到退费天数`
   - process timing: `提交到退费天数`
3. Use a reason taxonomy, not just raw reasons:
   - `学员客观约束`
   - `支付/价格机制`
   - `产品与服务匹配`
   - `其他长尾`
4. Extract text themes from refund/retention text:
   - health shock
   - time conflict
   - family resistance
   - economic pressure
   - trust/process issue
   - product promise mismatch
   - retention action and outcome themes
5. Payment background is reference-only:
   - compare payment structure vs refund structure
   - do not treat it as a complete refund-rate denominator by default
6. Voice-course front-end refund curves:
   - use `cci3_name = '声乐'`
   - use natural days `1..31`
   - GMV is anchored by `pay_time`
   - same-month refunds are anchored by refund table `refund_time`
   - avoid `dwd_order_flow_df.refund_amount` for this curve unless the method is explicitly changed
7. Final output should be business diagnosis:
   - explain mechanism, risk, and priority action
   - avoid writing only chart descriptions
   - when publishing to Feishu Sheets, create a visible `总结分析报告` / `报告正文` tab, not only raw data tabs; the first rows should say the result in business language
   - use Chinese field names on user-facing tabs
   - keep blank sheet cells truly blank; do not fill unused cells with empty strings because it blocks long-text overflow
   - for Feishu Docx business reports, use professional diagnostic language rather than conversational wording. Prefer titles such as `核心判断`, `问题定位`, `原因判断`, `解释边界`, and `处理建议`. Avoid colloquial or over-assertive phrases such as `猫腻`, `确实异常`, `仍不低`, `不能只追`, `只盯`, `一起看`, `看是否有`, `造成`, `单一渠道事故`, `全局风险抬升`, `系统性风险`. Replace them with cautious causal-boundary wording: `现有数据不支持将其主要归因于...`, `不宜归因为单一渠道`, `提示阶段性共性风险`, `显著高于历史区间，属于需要重点复盘的渠道`, `口径上不应并入...`.
   - when editing an existing Feishu report for style, first read back current `raw_content`, then patch the report-generation script or block source, publish, and read back again. Verify both required headings and forbidden wording; do not report completion from local script changes alone.
8. LLM narrative is optional enhancement; rule-based fallback is acceptable.

## Why this matters
A refund report built only on structured reason fields misses the real operational mechanism. Text signals and payment-background comparison are necessary to separate avoidable front-end refunds from high-ticket back-end delivery failures.

## Outputs to preserve
- core summary tables
- charts for segment split, timing, reasons, text themes, payment background, team/stage breakdowns
- formula-driven Excel templates for future-month refund amount forecasts by SKU × front/back-end; include user-fillable GMV inputs, editable forecast refund rate, formula columns, exact SQL, field validation, and口径说明. For a verified pattern and ClickHouse 21.8 pitfalls, see `references/sku-front-back-monthly-refund-forecast-excel-20260527.md`.
- refund-month × pay-month tracing when the user asks where a refund wave came from; see `references/vocal-backend-refund-detail-pay-month-trace-20260511.md` for a verified 声乐后端 example
- front-end handover/refund impact reports where current-month refunds may be affected by delayed historical cohorts; see `references/vocal-frontend-handover-refund-analysis-20260513.md` for the verified 声乐前端 4月 pattern
- focused M0/M1 cohort diagnosis when a month is high in the payment month itself: split current-month immediate refund (M0) from next-month release (M1), then diagnose reason/source/timing and write a problem-cause-solution section; see `references/vocal-frontend-march-april-m0-m1-diagnosis-20260513.md`. When multiple channels' refund rates rise together, avoid single-channel attribution: compare channels by refund rate with GMV denominators, then check historical reason deltas, raw refund text, and D4-D15 timing; see `references/vocal-frontend-march-systemic-refund-diagnosis-20260514.md`.
- channel-level attribution must compare refund rates, not only absolute refund amount: for each pay_month × channel × lag, compute `refund_amount / channel_pay_month_gmv`; then interpret together with GMV scale and refund amount contribution. This prevents over-weighting large channels or over-reading tiny high-rate channels. In narrative and charts, source/channel structure should show at least `GMV`, `退费额`, and `分组退费率`; avoid writing source sections that only rank by refund amount or share. For a verified 声乐前端 example where 3月 BD1-KOL M0 was abnormal by rate and scale, see `references/vocal-frontend-channel-rate-comparison-20260514.md`
- for SKU/category GMV and cohort work where the user asks for a category total plus a stricter product-order subset, keep the denominator broad and the numerator narrow. Example from 钢琴/声乐: total GMV uses `cci3_name = '钢琴'/'声乐'`; the 880+ course subset uses `main_goods_sku = '钢琴'/'声乐' AND main_first_level='课程' AND total_original_price >= 880`. Do not use `main_goods_sku` as the total GMV denominator unless the user explicitly asks for product-SKU total only; see `references/piano-cohort-refund-reason-20260520.md`.
- whenever a report compares 3月/4月, M0/M1, or any cohort refund rate, show the actual GMV denominator next to refund amount and refund rate (e.g. `支付月GMV(退费率分母)`, `退费额`, `退费率`). Do not make the user infer whether the rate denominator is correct. For historical baselines, exclude a known abnormal month from the baseline unless explicitly comparing against an “含异常月” benchmark; label the included months clearly (e.g. `2025-10至2026-02加权 M0退费率`).
- when a table-style report is unreadable or the user asks for 图文并茂, rebuild as a Feishu Docx business brief with KPI cards, large charts, short bullets, and explicit causal limits; see `references/vocal-frontend-april-docx-visual-report-20260513.md`
- when a Feishu Docx refund report section has too much narrative text, especially part2/part3/part4 cohort diagnostics, reduce each section to 3-4 bullets (problem定位、关键读数、来源/原因判断、处理建议) and move enumerations into section-local charts. Place each chart immediately after its section, update image block paths/count validation, publish, then verify raw_content keywords plus image token count.
- when a Feishu Docx refund report already has correct data and section-local charts but still reads like a diagnostic note rather than an executive-ready analysis, upgrade it to a business review structure: 3 concise core judgments, problem/improvement/risk sections, a `处理优先级与观察指标` section, split dense 3-panel charts into clearer section-level charts, and ensure source/channel sections show GMV + refund amount + source refund rate; see `references/vocal-frontend-refund-report-executive-upgrade-20260514.md`
- when a Feishu Docx refund report already has correct data but the user says the language is too colloquial or not professional enough, do a read-only style audit first, then rewrite only titles/expression/causal boundaries while preserving numbers and conclusions; see `references/feishu-docx-refund-report-style-audit-20260514.md`
- when the user says a refund report's structure is still too flat or asks to remove standalone `渠道维度` / `交接状态解释边界` / final `问题-原因-建议` sections, restructure it so each cohort section contains its own problem定位、原因结构、时效结构、来源结构、处理建议. Put channel/投手 as source-priority evidence inside cohort sections, put handover causal limits in `数据与限制`, and add a verifiable M1 refund-interval sheet when discussing cross-month release; see `references/vocal-frontend-docx-report-structure-iteration-20260514.md`.
- when investigating whether 4月 D4-D14 refund risk is tied to handover/selection requirements, split `已选期` vs `未选期` using valid `class_camp_id > 0 AND class_camp_name != ''`, show GMV/refund amount/refund rate for both M0 and D4-D14, and state correlation rather than causality unless refund initiator/failure-reason fields are available; see `references/vocal-frontend-selected-period-refund-risk-20260514.md`.
- in handover/refund impact reports, include a dedicated cohort-lag section when interpreting a current month. For example, after explaining 4月 cohort, add a separate 3月 cohort section if 3月 M1/M2 materially changes the read: show 3月 GMV, M0退费率, M0_M2累计退费率, M1+M2退费额, and the implication that 4月 M2 is not mature yet.
- when the user asks for a short Feishu message/leader summary of a refund report they have modified, read the current Feishu doc content first and base the summary on that version, not on prior session memory or earlier report drafts. If the direct Feishu doc tool is unavailable outside comment context, use authenticated local Chrome/headless DOM or another readback path, then extract the actual report body before writing the summary. The message should be concise, business-facing, and include GMV denominators next to refund amounts/rates when 3月/4月 or M0/M1 rates are mentioned; see `references/refund-doc-leader-summary-after-user-edits-20260514.md`.
- for SKU × 前后端 refund forecast workbooks where the user wants a simple input sheet for 6月累计退费金额, use `dwd_order_flow_df.cci3_name` as SKU (unless explicitly overridden), define each column as `X月GMV在6月预计退费率` rather than a generic monthly refund rate, include 5月 M1 and 6月 M0 predicted rates, and calculate `6月累计退费GMV` as the sum of 1-6月 GMV × corresponding maturity-adjusted rates; see `references/sku-front-back-june-refund-forecast-workbook-20260527.md`.
- when the forecast column means “任意支付月 GMV 在目标自然月当月产生的退费率” (for example `X月GMV在6月当月退费率`), use the single target-month lag component only: `refund_amount_at_lag / pay_month_gmv`. Do not use cumulative-to-target-month rates (`cum_refund_rate`, `cumN_rate`) or final predicted rates (`predicted_final_refund_rate`) for this column. Keep separate fields such as `predicted_current_month_refund_rate` and `predicted_final_refund_rate`; see `references/current-month-vs-cumulative-refund-rate-forecast-20260528.md`.
- Feishu Sheet automation pitfalls for 声乐前端 refund reports, including pandas Chinese-column consistency and API readback checks; see `references/vocal-frontend-refund-sheet-automation-pitfalls-20260513.md`
- 声乐后端退费明细更新到“截止昨天”时，右开区间应固定到今天 00:00:00，并校验 `退费明细` 最大退费时间；see `references/vocal-backend-refund-detail-pay-month-trace-20260511.md`
- 休学冻课/首款订单 diagnostic reports when the user asks about 冻课、休学冻课、仅首款数据; see `references/first-payment-freeze-analysis-method.md`
- markdown / docx report
- optional Feishu publication

## Common mistakes
- treating payment background as a true full refund-rate denominator
- relying only on structured reason fields
- merging front-end and back-end into one conclusion
- reporting percentages without explaining mechanism and action
- when a month has high M0 refunds, over-attributing the issue to historical lag or handover delay; M0 is an immediate same-month problem and needs its own reason/source/timing diagnosis before discussing M1/M2 lag
- using absolute refund amount alone to label a channel as problematic; channel comparison must show GMV, refund amount, refund rate, and small-sample caveats. If several channels' refund rates rise together, frame it as possible systemic risk first, then use absolute amount only for prioritization.
- using absolute refund amount alone to compare channels; channel quality must be compared by refund rate with the same pay-month GMV denominator, while absolute refund amount only indicates business impact/priority. Always show GMV, refund amount, refund rate, and a scale threshold or sample-size note for small channels.
- in analysis scripts, renaming SQL aliases to Chinese in a shared `qdf()` helper but later referencing the old English alias after pandas `groupby(...).agg(...)`; keep named aggregation outputs user-facing/Chinese or centralize a column-normalization helper before downstream calculations
- writing a Feishu report before independently reading back key tabs; after write, verify at least `报告正文`, `核心指标`, cohort tabs, and detail tab headers/first rows through the API
