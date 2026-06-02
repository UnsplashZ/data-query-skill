# User relationship exports: split-query + user-level summary

Use this pattern for ClickHouse exports that combine payment cohorts, enterprise WeChat friends, recent interaction, learning, complaint keywords, and service flags, but where the raw friend relation table would explode into hundreds of thousands of rows.

## When to use
- The user wants a deliverable for multiple user cohorts, but does **not** want one row per friend relation.
- The friend relation table is large enough that direct detail export becomes slow or error-prone.
- The report should be one row per `union_id`, with compact friend/interaction summaries.

## Recommended architecture
1. Query the base user cohort first.
2. Query user-level aggregates separately:
   - payment / refund / first-payment / high-value flags
   - learning summary
   - complaint keyword summary
   - service summary
   - live-user nickname/phone
3. Query friend relations as **user-level summaries**, not raw relation rows:
   - `friend_relation_cnt`
   - `current_friend_cnt`
   - `deleted_friend_cnt`
   - `qw_companies` sample list
   - `qw_belong_names` sample list
   - `qw_emp_names_sample` sample list
   - first/latest add time and first delete time
4. Query recent current-friend interaction as **user-level summary**:
   - `recent_qw_msg_cnt`
   - `recent_interaction_emp_cnt`
   - `latest_qw_msg_time`
   - sample companies / employees
5. Merge all aggregates in pandas by `union_id`.
6. Export one user-level row per `union_id` for each cohort sheet.

## Output design
Preferred workbook shape:
- `00_口径说明`
- `01_汇总`
- `02_退费用户_用户级`
- `03_首款小于1000_用户级`
- `04_付款大于880_用户级`

The user-facing sheets should keep:
- numeric counts
- boolean flags as 是/否
- compact friend samples
- no friend-relation row explosion

## Friend summary rules
- Use `uniqExact(emp_id)` for friend counts.
- Use `uniqExactIf(emp_id, del_time IS NULL OR del_time <= toDateTime('1971-01-01 00:00:00'))` for current friends.
- Use `uniqExactIf(emp_id, del_time > toDateTime('1971-01-01 00:00:00'))` for deleted friends.
- For sample strings, use `groupUniqArray(...)` then `arraySlice(..., 1, N)` and `arrayStringConcat(..., '、')`.

## Why this pattern is preferred
- It avoids huge friend-detail exports.
- It reduces Excel write failures caused by inconsistent DataFrame columns.
- It makes the workbook easier to review: one line per user, with compact indicators instead of relation-level noise.

## Verification
Before reporting success:
- verify the xlsx file opens
- verify the sheet names and row counts
- verify summary numbers match the intended cohorts
- verify the output is user-level, not raw friend-detail level
