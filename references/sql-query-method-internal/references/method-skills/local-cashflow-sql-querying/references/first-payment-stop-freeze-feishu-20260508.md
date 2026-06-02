# 2026-05-08 历史首款/休学冻课 Feishu 表写入细节

## Target

User-facing Feishu Wiki Sheet:

- URL: `<REDACTED_FEISHU_URL>`
- Resolved spreadsheet token: `<REDACTED_FEISHU_SPREADSHEET_TOKEN>`

Final script:

- `/Users/zheng/.hermes/python/projects/first-payment-only/refresh_feishu_with_class_attendance.py`

Final local backup:

- `/Users/zheng/.hermes/output/query_results/20260508_历史首款_冻课学员_补上课情况.xlsx`

Run with:

```bash
/opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python \
  /Users/zheng/.hermes/python/projects/first-payment-only/refresh_feishu_with_class_attendance.py
```

## Final four tabs

The Feishu workbook should contain exactly the task-facing tabs:

1. `首款订单汇总`
2. `首款订单明细`
3. `冻课汇总`
4. `冻课明细`

The user manually adjusted the summary-sheet layout; future updates should preserve the current block-style format and write values into that shape rather than reverting to a long concatenated raw table.

## User-facing summary layout preferences learned

- Summary pages should be readable by sections/blocks, not a single complex long table.
- Keep the current block format/metric display unless the user explicitly asks to redesign it.
- Numeric KPIs must be numeric cells/values. Do **not** write text like `xxx 万` or `7.30%` into metric cells.
  - Amounts stay in yuan as numeric values.
  - Rates stay as numeric decimals such as `0.073`, letting the sheet formatting display them if desired.
- `支付金额分桶` blocks sort by bucket amount ascending:
  1. `1-99`
  2. `100-199`
  3. `200-500`
  4. `501-999`
  5. `1000-1880`
  6. `1881-2980`
  7. `2981-5000`
  8. `5001+`
  9. `其他`

## Final 首款订单口径

Source: `dwd_order_flow_df`.

- `pay_status_name = '支付成功'`
- `pay_type_code = 1`
- `pay_type_name = '首款'`
- `main_first_level = '课程'`
- anti-join: first-payment `flow_no` must not appear as a successful tail-payment `relate_flow_no`
- historical window currently uses `< toDateTime('2026-05-09 00:00:00')`

Latest observed after switching stop/freeze logic:

- `首款订单明细`: `137,041` rows
- `首款订单汇总`: `69` rows / `11` cols

## Final 首款订单上课情况 logic

Source table:

- `tock_ast_process_data`

Verified useful fields:

- `union_id`
- `camp_id` — 上课营期 ID
- `class_time`
- `study_time`
- `zb_study_time`
- `submit_cnt`
- `e_time_cnt`
- `message_cnt`

Join logic:

```sql
LEFT JOIN tock_ast_process_data a
  ON b.union_id = a.union_id
 AND b.camp_id = a.camp_id
```

Class record condition:

```sql
a.class_time > toDateTime('1970-01-02 00:00:00')
AND a.class_time >= b.pay_time
AND a.class_time < toDateTime('<end>')
```

Derived first-payment fields:

- `class_record_cnt`
- `first_class_time`
- `latest_class_time`
- `total_study_time`
- `total_zb_study_time`
- `active_class_record_cnt`
- `是否有上课记录`
- `是否有学习行为`

`active_class_record_cnt` uses records with attendance/interaction evidence:

```sql
study_time > 0 OR zb_study_time > 0 OR submit_cnt > 0 OR e_time_cnt > 0 OR message_cnt > 0
```

User later removed the standalone `按上课情况` summary block, but kept the class-attendance totals in `首款订单汇总` core KPIs and the class fields in `首款订单明细`.

Latest observed after rerun:

- `first_has_class_orders`: `26,899`
- `first_has_class_rate`: `0.19628432366955875`
- `first_active_orders`: `26,340`
- `first_active_rate`: `0.19220525244269962`

## Final 休学冻课 reporting rules

- Treat `休学冻课` as one combined concept.
- Do not split by:
  - `休学` vs `冻课`
  - keyword hit vs other rule hit
  - status-field hit vs class-name hit
- User-facing `冻课汇总` should only show total-level metrics and normal business breakdowns.
- Remove from summary output:
  - `匹配课程支付订单数`
  - `课程支付订单匹配率`
- The detail sheet may still carry audit fields if useful, but summary should not emphasize matching/source breakdowns.

## Latest 休学冻课 source logic correction

User corrected the source logic after comparing against:

```sql
SELECT count(*)
FROM tock_handover_plus
WHERE toDate(stop_study_time) > '2020-01-01'
   OR multiMatchAny(service_camp_name, ['休学|延期|冻课'])
```

Important reconciliation findings:

- The user's query returns `14,691` raw rows / `14,690` distinct non-empty `order_no`.
- Earlier report logic using `drh_handover_plus FINAL WHERE _sign > 0` plus `dev_stop_stu_record` produced a different order set.
- `tock_handover_plus` has only `order_no`, `service_camp_name`, `stop_study_time` for this purpose; it does **not** have `_sign`, `stop_study_status`, or `stop_flag`.

Current source logic:

1. Main handover source is `tock_handover_plus t`.
2. Join current effective `drh_handover_plus` by `order_no` only to get `stop_study_status` and auxiliary fields:

```sql
LEFT JOIN (
  SELECT
      order_no,
      anyIf(union_id, union_id != '') AS union_id,
      max(stop_study_status) AS stop_study_status,
      anyIf(stop_hand_emp, stop_hand_emp != '') AS stop_hand_emp,
      anyIf(class_camp_name, class_camp_name != '') AS class_camp_name
  FROM (
      SELECT *
      FROM drh_handover_plus FINAL
      WHERE _sign > 0
  )
  WHERE order_no != ''
  GROUP BY order_no
) d ON t.order_no = d.order_no
```

3. Include a `tock_handover_plus` order when:

```sql
t.order_no != ''
AND (
    d.stop_study_status = 1
    OR t.service_camp_name LIKE '%休学%'
    OR t.service_camp_name LIKE '%冻课%'
    OR t.service_camp_name LIKE '%延期%'
)
```

4. Still union with supplemental `dev_stop_stu_record.stop_flag = 1` rows:

```sql
SELECT order_no AS flow_no
FROM dev_stop_stu_record
WHERE stop_flag = 1
  AND order_no != ''
  AND stop_time >= toDateTime('1970-01-01 00:00:00')
  AND stop_time < toDateTime('2026-05-09 00:00:00')
GROUP BY order_no
```

5. After FULL OUTER JOIN of the two sources, use `coalesce(nullIf(hp.flow_no, ''), sr.flow_no)`. ClickHouse FULL OUTER JOIN can leave the missing side as an empty-string default; plain `coalesce(hp.flow_no, sr.flow_no)` caused many unmatched `sr` rows to collapse to `''` and duplicate. The `nullIf` fix preserves `sr.flow_no`.

Latest observed after this correction:

- `hp` from `tock_handover_plus + drh.stop_study_status`: `11,929` distinct orders
- `dev_stop_stu_record` supplement: `7,381` distinct orders
- combined distinct freeze/rest orders: `13,367`
- `冻课明细`: `13,367` rows / `28` cols
- `冻课汇总`: `46` rows / `6` cols

## 交接轨次字段

User requested `冻课明细` include the track field for the handover class.

Source:

- `dwd_order_handover_df.camp_group_name`

Join:

```sql
LEFT JOIN (
  SELECT
      flow_no,
      anyIf(camp_group_name, camp_group_name != '') AS class_camp_group_name
  FROM dwd_order_handover_df
  WHERE flow_no != ''
  GROUP BY flow_no
) handover_track ON flags.flow_no = handover_track.flow_no
```

User-facing field:

- `交接班级轨次`

Place it after `交接班级名称` in `冻课明细`.

## Feishu write pitfalls found

1. Wiki resolution worked before sheet write permission did:
   - `wiki/v2/spaces/get_node` succeeded
   - `sheets_batch_update` initially failed with `403`, Feishu `code=91403`, `msg=Forbidden`
   - Resolution: user granted edit permission to the app/workbook.

2. Large row expansion failed in one call:
   - error: `code=90204`, `invalid parameter: Dimension.Length`
   - Fix: append rows in chunks, e.g. max `5000` rows per `dimension_range` call.

3. Clearing huge ranges caused transient SSL EOF / oversized calls.
   - Fix: for large detail tabs, overwrite target area directly and only clear a small stale tail if needed.
   - For summary tabs, clear a bounded area such as first `220` rows × `30` columns to remove stale blocks while preserving sheet-level formatting.

4. Detail write uses value API chunks of around `4500` rows per write.

5. Feishu values read may transiently return `90235 data not ready,retry later` immediately after large writes. Retry after a few seconds before treating verification as failed.

## Verification

After write, read samples from all four tabs via Sheets API and verify non-empty headers/samples. Do not claim completion based only on write API success.
