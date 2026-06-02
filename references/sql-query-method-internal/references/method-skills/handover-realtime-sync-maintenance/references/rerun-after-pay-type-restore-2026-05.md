# 2026-05 handover realtime pay_type restore and rerun comparison

Session-specific learning for `handover-realtime-sync-maintenance`.

## Situation

User noticed the cron task `交接实时数据同步到飞书` may have had logic changes. Inspection showed:

- SQL file: `~/.hermes/sql/projects/handover-realtime-sync/交接数据-实时.sql`
- Python script: `~/.hermes/python/projects/handover-realtime-sync/run_sync.py`
- Cron job id: `3449f705d7a3`

The SQL had temporarily lost:

```sql
AND T1.pay_type IN (2, 3)
```

Restoring that condition was requested explicitly. User also corrected workflow: do not lightly modify scheduled task business logic.

## Important operational pitfall

When user asks to rerun the scheduled task, prefer the actual cron wrapper first and verify the session output. Do not start a parallel direct business-script run while the cron-triggered run is still active.

A parallel direct run during this session hit Feishu API `too many request` while the cron wrapper was still running. The cron wrapper then completed successfully and wrote Feishu.

Good verification indicators from the cron session JSON:

```text
task='交接实时数据同步到飞书' exit_code=0 runtime=101.06s card=sent
feishu_written: true
spreadsheet_token: <REDACTED_FEISHU_SPREADSHEET_TOKEN>
```

## Comparison pattern used

To compare two export timestamps, compare local CSVs under:

```text
~/.hermes/output/exports/handover-realtime-sync
```

Example timestamps:

- 13:00 run: `20260507_130135`
- rerun after restore: `20260507_192829`

Observed result:

- Structure unchanged across all four CSVs.
- 学员明细 row count: `9550 -> 9577`, net +27.
- Added rows were all `支付类型` in `全款` / `尾款`, confirming restored `T1.pay_type IN (2,3)` did not allow 首款.
- Common rows had large dynamic-field changes, especially:
  - `二阶学管`
  - `加微时间`
  - `加微状态`
  - `加入轨次日期`
  - `加入营期日期`
  - `选期状态`

This pattern suggests upstream handover / external-user source changes rather than the pay_type restore.

## Lost-WeChat status export pattern

When user asks for users who were previously `已加微` and now `未加微`, compare the two 学员明细 CSVs by `flow_no`:

- old: `加微状态 == '已加微'`
- new: `加微状态 == '未加微'`

For the 2026-05-07 13:00 vs 19:29 comparison, this yielded:

- 398 orders
- 398 unique `union_id`
- concentrated heavily in `钢琴院长【亲授班】` and `声乐院长【特别班】`
- common pattern: old `二阶学管=王晶`, new `二阶学管=唐倩倩`, with `加微时间` blanking out

Generated workbook path in that session:

```text
/Users/zheng/.hermes/output/exports/handover-realtime-sync-diff/加微状态丢失用户_20260507_1300_vs_1929.xlsx
```

For future reuse, use skill scripts:

```bash
/opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python \
  ~/.hermes/skills/data-science/handover-realtime-sync-maintenance/scripts/compare_handover_runs.py \
  20260507_130135 20260507_192829

/opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python \
  ~/.hermes/skills/data-science/handover-realtime-sync-maintenance/scripts/export_lost_wechat_users.py \
  20260507_130135 20260507_192829
```
