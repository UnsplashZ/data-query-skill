# Vocal handover refund-effect analysis pattern

Use this when analyzing whether a handover/process intervention lowered refund rates, especially when the intervention landed first in 声乐.

## Source and default scope

Verified source in ClickHouse:
- `dwd_order_flow_df` for paid orders and same-month `refund_amount`
- `dwd_order_handover_df` for handover / join-group / add-WeChat states
- `tock_dwd_order_refund_df` for refund reason detail

Default filter used for this analysis:
```sql
pay_time >= toDateTime('2025-11-01 00:00:00')
AND pay_time < toDateTime('2026-05-01 00:00:00')
AND pay_amount > 0
AND pay_status_name = '支付成功'
AND new_front_end_name LIKE '%前端%'
```

For the 声乐-only section, add exactly:
```sql
AND cci3_name = '声乐'
```
Keep all other filters fixed so the vocal section is comparable to the big-market section. Do not silently switch to `main_goods_sku='声乐'` unless the user asks for that predicate.

Core scope for handover-effect validation:
```sql
main_first_level = '课程'
AND pay_type_name IN ('全款','尾款')
```
Optional high-ticket reference:
```sql
AND total_original_price >= 1880
```

Metric:
```text
same-month cohort refund rate = refund_amount occurring within the order's pay month / pay_amount
```

## Report logic requested by the user

The report should be ordered as:
1. big-market/mixed-SKU large-number view;
2. vocal (`cci3_name='声乐'`) view, because the handover project landed in vocal first;
3. inside each section, compare against prior months / recent-half-year, not only March vs April;
4. then validate whether the vocal decline plausibly relates to handover by checking coverage, same-status refund rates, structure, and refund reasons.

A better one-line conclusion for this pattern is:
```text
混合SKU大盘未下降，但声乐作为交接先落地SKU已经下降；声乐核心口径3月 3.16% → 4月 2.60%，且已入群/入班人群下降更明显，下一步重点验证未入群/有交接未入群与渠道结构。
```

## Validation dimensions beyond the headline rate

To avoid overstating causality, validate four areas:

1. **交接覆盖是否提升**
   - `has_handover = h.flow_no != ''`
   - `joined = join_group_time > '1970-01-02'`
   - `added_wechat = ast_friend_time > '1970-01-02'`
   - Compare coverage month by month.

2. **同一交接状态内退费率是否下降**
   Bucket orders after a de-duplicated handover join:
   - `已入群/入班`: `join_group_time` valid
   - `有交接未入群`: has handover row but no valid `join_group_time`
   - `无交接记录`: no handover row

   Important real finding from the 2026-03 vs 2026-04 vocal run:
   - 声乐核心大数: `3.16% -> 2.60%` (`-0.56pp`)
   - 有交接记录覆盖率: `68.60% -> 76.00%` (`+7.40pp`)
   - 入群/入班覆盖率: `59.39% -> 50.14%` (`-9.25pp`)
   - 已入群/入班退费率: `3.14% -> 1.47%` (`-1.66pp`)
   - 无交接记录退费率: `3.76% -> 2.43%` (`-1.33pp`)
   - 有交接未入群 was the risk bucket in April: `9.22%`

   Interpretation: not "any handover is enough"; the useful signal is completed承接/入群, while `有交接未入群` needs separate risk handling.

3. **渠道 / 价格 / 班型结构是否 changed**
   At minimum compare March vs April by:
   - `f_market_belong` (渠道归属)
   - `channel_emp_name` (投手)
   - price bucket from `total_original_price` (`>=2381` as 2980档, `>=1880` as 1880档, else 1880以下)
   - `camp_sku` / class-type proxy

   Report both share/GMV movement and within-group refund-rate movement; otherwise structural change can be mistaken for process effect.

4. **退款原因是否 supports process improvement**
   Join `tock_dwd_order_refund_df` by `flow_no` and filter refund rows to same-month refund windows. Use `refund_reason` and `refund_reason_detail` to distinguish objective reasons from flow-service reasons.

   In the vocal validation run, top same-month refund reasons still included objective reasons like 家人原因/身体原因/时间原因 plus payment errors; this means the result supports a positive signal but is still observational.

## Feishu report style lessons from the session

For this user's Feishu Docx report, avoid a raw table-dump style. Use:
- formal title hierarchy (`heading1/2/3` when API allows it)
- a one-line business conclusion at the top
- KPI-style overview image/cards before detail
- short bullets rather than dense paragraphs
- section order: big market first, then vocal first-landed-SKU analysis
- explicit predicate captions such as `cci3_name='声乐'`
- a chart for monthly trend and a chart for validation dimensions

Full Excel should remain an appendix/reference, not the primary reading surface.