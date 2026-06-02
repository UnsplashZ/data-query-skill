---
name: handover-realtime-sync-maintenance
description: Maintain the user's Hermes realtime handover sync SQL and metric semantics, including which outputs automatically inherit SQL fields and how refund exclusion affects open-rate numerators.
version: 1.0.0
---

# Handover realtime sync maintenance

Use when:
- the user wants to change fields in the Hermes realtime handover sync
- the user asks whether a SQL field change will affect 学员明细 / 营期明细 / 日明细
- the user asks where a Feishu output sheet's data comes from, or whether a sheet is produced directly by SQL vs by Python aggregation
- the user wants to adjust refund handling in the realtime sync metrics
- the user refers to the Hermes handover realtime cron / Feishu sync outputs

## Main files

- SQL used by the Hermes realtime sync:
  - `~/.hermes/sql/projects/handover-realtime-sync/交接数据-实时.sql`
- Runtime config:
  - `~/.hermes/python/projects/handover-realtime-sync/config.yaml`
- Sync script:
  - `~/.hermes/python/projects/handover-realtime-sync/run_sync.py`
- Session-specific reference for the May 2026 Feishu Docx chart correction:
  - `references/refund-handover-docx-chart-correction-2026-05.md`
- Session-specific reference for the May 2026 pay_type restore, cron rerun concurrency pitfall, and 13:00-vs-rerun data comparison:
  - `references/rerun-after-pay-type-restore-2026-05.md`
- Session-specific reference for the May 2026 handover card cache / old-card callback compatibility issue:
  - `references/card-cache-callback-compatibility-2026-05.md`
- Session-specific reference for the May 2026 card top metric range rollback, May backend-track filter, and calligraphy 105期+ display rule:
  - `references/card-top-range-and-may-track-filter-2026-05.md`
- Reusable local comparison scripts:
  - `scripts/compare_handover_runs.py` compares two export timestamps and highlights row/metric/status deltas
  - `scripts/export_lost_wechat_users.py` exports users whose `加微状态` regressed from `已加微` to `未加微` into Excel

Observed config linkage:
- `config.yaml` points `sql_file` to `~/.hermes/sql/projects/handover-realtime-sync/交接数据-实时.sql`
- the cron job named `交接实时数据同步到飞书` uses this project/script path, so updating that SQL changes future realtime sync runs

## Important output behavior

### 1. 学员明细 automatically inherits SQL columns
In `run_sync.py`:
- query result is loaded into `raw_df`
- `raw_df.columns = [str(c) for c in raw_df.columns]`
- CSV / Excel / Feishu upload for 学员明细 use the dataframe columns dynamically

Implication:
- adding a new column in the SQL (for example `营期轨次`) automatically appears in 学员明细
- no separate script change is needed for 学员明细 field propagation
- if the user wants a row-level derived metric that is **not** in SQL (for example `开课间隔 = 开课日期 - 支付时间`), patch `build_detail()` to append it before export/writeback

### 2. 营期明细 / 日明细 / 团队明细 do NOT automatically inherit arbitrary SQL columns
These sheets are rebuilt from helper dataframes in `run_sync.py` using explicit groupings and output column lists.

Implication:
- adding a SQL column alone does **not** make it appear in 营期明细 / 日明细 / 团队明细
- if the user wants a new field there, update the corresponding summary builder explicitly
- currently the realtime sync has these summary builders:
  - `build_camp_summary(..., today)` -> 营期明细
  - `build_daily_summary()` -> 日明细
  - `build_team_daily_summary()` -> 团队明细
- if the user says to keep those summaries unchanged, leave the script alone

Verified example added successfully:
- when SQL added `衔接课开课状态`, `build_detail()` was patched to derive row-level `helper['衔接课开课人数'] = ((helper['衔接课开课状态'] == '已开课') & helper['退款时间'].isna()).astype(int)`
- then `build_camp_summary()` was patched to:
  - aggregate `衔接课开课人数`
  - cast it as an integer summary column
  - append it as the **last column** in 营期明细
- this change affects only 营期明细; 日明细 / 团队明细 remain unchanged unless explicitly patched too

### 2.1 Adding maturity metrics to 营期明细
A proven local pattern for new camp-level metrics that depend on "as of today" aging:

1. change `build_camp_summary` signature to accept `today: pd.Timestamp`
2. create a row-level boolean in the camp-summary source, for example:
   - `source['是否支付满7天'] = ((today.normalize() - source['支付日期']).dt.days >= 7)`
3. aggregate with a mask inside `agg(group)`
4. add the new fields to:
   - the returned `out` dict
   - `cast_int_columns(...)`
   - the final ordered column list
5. update the call site in `main()` from:
   - `build_camp_summary(helper_df)`
   to
   - `build_camp_summary(helper_df, today)`
6. update `test_run_sync_metrics.py` to pass `today` into `build_camp_summary(...)`

Verified example added successfully:
- `支付满7天订单数`: count of rows where `支付日期` is at least 7 days earlier than the run date
- `支付满7天加微数`: among those mature orders, count of rows with `已加微人数 > 0`

Important semantic note:
- this is an **as-of-today mature-order pool** metric
- it is **not** the same as `支付后7天加微人数` / `支付7天加微数`
- wording difference matters:
  - `支付满7天加微数` = paid at least 7 days ago, and currently added on WeChat
  - `支付后7天加微数` = added on WeChat within 7 days after payment
- before shipping this kind of metric change to the user's live Feishu sheet, explicitly confirm which wording/口径 the business owner wants. In practice the user's initial wording can still differ from the boss's intended metric, and this may require reverting the patch after a manual run.
- if the user asks to roll back such a change, revert all three places together:
  1. `build_camp_summary` signature/body
  2. the `main()` call site
  3. the matching assertions in `test_run_sync_metrics.py`
- after rollback, manually rerun the cron job `交接实时数据同步到飞书` so the Feishu sheet is overwritten back to the old structure.

### 3. Current grouped metrics include average open gap where configured
Observed local implementation:
- 学员明细 adds row-level `开课间隔`
- 营期明细 / 日明细 / 团队明细 add grouped `平均开课间隔`
- formula: `开课日期 - 支付时间` in days, using non-null opened rows only, rounded to 2 decimals
- 团队明细 current dimensions are:
  - `支付日期`
  - `团队`
  - `商品SKU`
  - `营期SKU`
  - `商品价格`

## Adding 前端营期轨次

For the realtime SQL, the front-end camp track can be added as:
- output field: `营期轨次`
- source: `dim_camp_df.camp_group_name`

Pattern used successfully:
1. add `camp_group_name` to the front-end camp dimension subquery / join
2. expose it in the a1/base select as `营期轨次`
3. include it in the final export select list

Result:
- 学员明细 gets the new `营期轨次` column automatically
- 营期明细 / 日明细 remain unchanged unless the script is modified

## Refund handling semantics in realtime sync

### Original behavior
`run_sync.py` originally did:
- `订单数 = 1` for every row
- `退费人数 = 退款时间.notna()`
- `已开课人数 = (开课状态 == '已开课')`

So refund orders were counted separately in `退费人数`, but were **not** excluded from `已开课人数`.
If the sheet formula uses `已开课人数 / 订单数`, refunded orders still remain in the denominator, and previously could also remain in the numerator.

### User-requested partial exclusion: numerator only
If the user wants **only** the open-rate numerator adjusted, keep all other metrics unchanged and patch:

```python
helper['已开课人数'] = ((helper['开课状态'] == '已开课') & helper['退款时间'].isna()).astype(int)
```

This means:
- `已开课人数`: only opened and not-refunded orders
- `订单数`: unchanged
- `退费人数`: unchanged
- `已选期人数` / `已加微人数`: unchanged
- summaries continue using the same columns, but the open-rate numerator becomes refund-excluded

File location where this patch was applied successfully:
- `~/.hermes/python/projects/handover-realtime-sync/run_sync.py`

## Mixed SKU threshold and template-placeholder pattern

When the realtime sync needs different minimum price thresholds for different SKU groups, do not force a single `goods_price` across all products.

A proven pattern for this project:

- keep the SQL template generic with placeholders such as:
  - `{{main_goods_sku}}`
  - `{{camp_sku}}` when the SQL filters the joined front-end camp dimension (`dim_camp_df.camp_sku`)
  - `{{goods_price}}`
- run the SQL multiple times with different SKU predicates / thresholds
- concatenate the raw results and de-duplicate before downstream summary building
- apply the same SKU-specific threshold guard again in Python before summary generation

Verified implementation detail:
- `run_sync.py::render_sql(...)` must replace every required placeholder in the SQL template before optional blocks are stripped
- if the SQL introduces `{{camp_sku}}`, add a `camp_sku_condition` render argument and pass it from `query_target_raw_df(...)` using `rule['camp_skus']`, for example:
  - `camp_sku_condition=f"camp_sku in ({sql_in_list(rule['camp_skus'])})"`
- after template changes, explicitly validate the rendered SQL has no residual:
  - `{{...}}`
  - `[[...]]`
- keep unresolved optional filters such as `status3` safe by leaving them inside `[[...]]`; if no value is provided, the existing optional-block stripper removes them

Verified example:
- 声乐 / 钢琴 / 朗诵: `name in (...)` and `camp_sku in (...)` with `goods_price >= 1880`
- 口琴 / 书法: `name in (...)` and `camp_sku in (...)` with lower SKU-specific threshold where configured
- SQL query layer can inject both 商品SKU and 营期SKU predicates when the SQL contains both placeholders
- Python post-filter should still key the minimum-price rule off 商品SKU only; do not require 营期SKU to match unless the user explicitly asks for that stricter behavior
- after merge, keep price bucketing unchanged (`<= 2381 -> 1880`, `> 2381 -> 2980`)

This is safer than weakening the global threshold, and keeps the realtime cron aligned with the configured SKU rules.

## 新增：衔接课开课状态

A verified SQL-only pattern was added successfully to `交接数据-实时.sql`:

- keep the existing `开课日期` / `开课状态` unchanged
- add a second derived date from `tock_ast_process_data` without the course-name whitelist
- expose a final field `衔接课开课状态`

Implementation pattern in SQL:
1. keep the original `a3` subquery:
   - `study_time > 0`
   - plus the existing `multiMatchAny(course_name, [...首课规则...])`
   - this still feeds `开课日期`
2. add a new `a4` subquery:
   - `study_time > 0`
   - **no** `multiMatchAny(course_name, ...)` filter
   - `min(class_time) AS min_class_time`
   - join on `a1.union_id = a4.union_id AND a2.class_camp_id = a4.camp_id`
3. expose:
   - `nullIf(a4.min_class_time, toDateTime('1970-01-01 08:00:00')) AS 衔接课开课日期`
4. append at the end of `export_base`:
   - `衔接课开课状态`
   - logic mirrors existing `开课状态`, but uses `衔接课开课日期`

Current verified formula:
```sql
if(
  `承接状态` = '已承接'
  AND `二阶学管` <> ''
  AND `加微时间` <> ''
  AND `衔接课开课日期` <> ''
  AND toString(today()) >= `衔接课开课日期`,
  '已开课',
  '未开课'
) AS `衔接课开课状态`
```

This change affects 学员明细 automatically because raw SQL columns flow through dynamically.
营期明细 / 日明细 / 团队明细 still require explicit Python changes if the new field must appear there.

Verified summary-sheet propagation pattern for `衔接课开课人数`:
- in `build_detail()`, derive row-level `helper['衔接课开课人数'] = ((helper['衔接课开课状态'] == '已开课') & helper['退款时间'].isna()).astype(int)`
- in `build_camp_summary()`, aggregate it and append it as the last column of 营期明细
- in `build_daily_summary()`, aggregate it and append it as the last column of 日明细
- in `build_team_daily_summary()`, aggregate it and append it as the last column of 团队明细

Verified daily-summary dimension change pattern for `销售团队`:
- if the user means a real daily split rather than a display-only column, set `source['销售团队'] = source['团队']`
- add `销售团队` to `group_cols` in `build_daily_summary()`
- include `销售团队` as the last returned column
- update the sort keys to include `销售团队`
- expect 日明细 row count to increase materially after this change; this is expected, not a regression

Verified camp-summary dimension change pattern for `销售团队`:
- if the user wants 营期明细 also split by team, set `source['销售团队'] = source['团队']` in `build_camp_summary()`
- add `销售团队` to `group_cols`
- include `销售团队` as the last returned column
- update the sort keys to include `销售团队`
- expect 营期明细 row count to increase after this change because one camp can split into multiple team rows

Verified one-off multi-SKU extraction pattern without changing the permanent cron:
- use this when the user asks to “用前端交接数据同步的 SQL 跑一份包含 X/Y/Z SKU 的数据” or similar, and they do **not** explicitly ask to modify the live scheduled Feishu sync
- do **not** patch `SKU_QUERY_RULES` in `run_sync.py` for a one-off export; import `run_sync.py` as a module and temporarily override `rs.SKU_QUERY_RULES` in the ad hoc Python process
- reuse the normal pipeline so derived columns and summaries stay consistent:
  1. load `config.yaml` and SQL template
  2. set temporary SKU rules in memory
  3. call `query_target_raw_df(...)`
  4. call `build_detail(raw_df, today)`
  5. call `build_camp_summary(...)`, `build_daily_summary(...)`, and `build_track_summary(...)`
  6. export Excel/CSV under a one-off output directory such as `~/.hermes/output/exports/handover-realtime-sync-oneoff/`
- for a local preview/export, do not write Feishu unless requested; use local Excel attachment delivery if the user asks for the data
- verify the generated workbook with `openpyxl` or equivalent before responding: file exists, non-zero size, sheet names, row counts, and column counts
- if extra SKUs have unclear minimum-price thresholds, state the assumption explicitly in the response; do not silently persist that assumption into cron config

Example skeleton:
```python
import importlib.util, sys
from pathlib import Path
import pandas as pd

project = Path.home() / '.hermes/python/projects/handover-realtime-sync'
spec = importlib.util.spec_from_file_location('run_sync', project / 'run_sync.py')
rs = importlib.util.module_from_spec(spec)
sys.modules['run_sync'] = rs
spec.loader.exec_module(rs)

rs.SKU_QUERY_RULES = [
    {'name': 'oneoff_main', 'goods_skus': ['声乐', '钢琴', '朗诵', '口琴'], 'camp_skus': ['声乐', '钢琴', '朗诵', '口琴'], 'min_price': 1880},
    {'name': 'calligraphy', 'goods_skus': ['书法'], 'camp_skus': ['书法'], 'min_price': 880},
]

cfg = rs.load_yaml(project / 'config.yaml')
sql_template = Path(cfg['sql_file']).read_text(encoding='utf-8')
end_date = pd.Timestamp.today().date().isoformat()
today = pd.Timestamp(end_date)
raw_df = rs.query_target_raw_df(
    sql_template,
    start_date=cfg['start_date'],
    end_date=end_date,
    stage=cfg['stage'],
    base_goods_price=int(cfg['goods_price']),
)
detail_df, helper_df = rs.build_detail(raw_df, today)
camp_df = rs.build_camp_summary(helper_df)
daily_df = rs.build_daily_summary(helper_df, today)
track_df = rs.build_track_summary(helper_df)
rs.write_excel([
    ('学员明细', detail_df),
    ('营期明细', camp_df),
    ('日明细', daily_df),
    ('承接轨次', track_df),
], xlsx_path)
```

Verified integration pattern for `承接轨次` into the main realtime sync:
- if the user wants the existing cron/task to keep updating the `承接轨次` sheet every run, do not create a separate cron first; patch the current `handover-realtime-sync` project so the existing task writes a fourth dataset
- current verified target:
  - sheet title: `承接轨次`
  - sheet_id: `vIajca`
- add `sheet_ids.承接轨次: vIajca` to `config.yaml`
- add a builder in `run_sync.py`:

```python
def build_track_summary(helper: pd.DataFrame) -> pd.DataFrame:
    source = helper.copy()
    source['价格类型'] = source['商品价格']
    source['承接轨次'] = source['二阶轨次']
    summary = (
        source.groupby(['商品SKU', '价格类型', '承接轨次'], dropna=False, as_index=False)
        .agg(
            学员数=('union_id', 'nunique'),
            加微数=('已加微人数', 'sum'),
            衔接课开课人数=('衔接课开课人数', 'sum'),
            正式课开课人数=('已开课人数', 'sum'),
        )
        .rename(columns={'商品SKU': 'sku'})
    )
    summary['承接轨次'] = summary['承接轨次'].replace({'': None})
    summary = cast_int_columns(summary, ['价格类型', '学员数', '加微数', '衔接课开课人数', '正式课开课人数'])
    summary = summary.sort_values(['sku', '价格类型', '承接轨次'], kind='stable')
    return summary[['sku', '价格类型', '承接轨次', '学员数', '加微数', '衔接课开课人数', '正式课开课人数']]
```

- then patch `main()` together in four places:
  1. build `track_df = build_track_summary(helper_df)`
  2. export `承接轨次_交接实时_*.csv`
  3. include `('承接轨次', track_df)` in `write_excel(...)`
  4. call `upload_dataset(..., cfg['sheet_ids']['承接轨次'], track_df)`
- also extend the printed summary JSON with:
  - `rows_track`
  - `track_csv`
- verified current run result after integration:
  - the existing realtime sync task successfully wrote `承接轨次` along with 学员明细 / 营期明细 / 日明细
  - output row count observed locally: `57`
- practical implication:
  - once this patch is in place, the existing cron `交接实时数据同步到飞书` can keep its current schedule and automatically refresh `承接轨次` without a second job

Verified data-lineage explanation pattern for `承接轨次`:
- when the user asks “承接轨次 sheet 的 SQL 是什么” or “是 SQL 直接出来还是 Python 处理出来”, answer precisely:
  - it is **not** produced by a separate standalone SQL
  - the main realtime SQL `交接数据-实时.sql` produces row-level fields in 学员明细, including `二阶轨次`
  - `run_sync.py` then builds the sheet via `build_track_summary(helper_df)`
- SQL lineage for the track name:
  - final row field: `二阶轨次`
  - SQL select: `nullIf(a2.group_camp_name, '') AS 二阶轨次`
  - `a2.group_camp_name` comes from `dim_camp_df.camp_group_name` joined through the latest `drh_handover_plus` row's `class_camp_id` / `stop_camp`
- Python aggregation lineage:
  - `价格类型 = 商品价格` after price bucketing (`<=2381 -> 1880`, `>2381 -> 2980`)
  - `承接轨次 = 二阶轨次`
  - group by `['商品SKU', '价格类型', '承接轨次']`
  - aggregate `学员数 = union_id.nunique()`, `加微数 = 已加微人数.sum()`, `衔接课开课人数 = 衔接课开课人数.sum()`, `正式课开课人数 = 已开课人数.sum()`
- Time window explanation:
  - `承接轨次` inherits the main SQL's `pay_time` window from `config.yaml` / CLI (`start_date` to `--end-date` or today)
  - the Python `build_track_summary()` itself does not add an extra time filter, and does not filter by 加微时间 / 加入轨次日期 / 轨次月份
- This distinction matters because changing SQL can change row-level source fields, but changing the `承接轨次` sheet dimensions/metrics requires patching `build_track_summary()` and its main/export/upload wiring.

Verified dashboard debugging pattern for `承接轨次` source-table displays:
- if a generated dashboard shows empty tracks while `承接轨次` (`vIajca`) has rows, inspect any legacy display-layer filters before changing the sync SQL
- backend-track display exclusions for the handover dashboard are owned by the display scripts, not the source sync SQL. Current dashboard guard tuple in both `~/.hermes/scripts/handover_team_report_card.py` and `~/.hermes/scripts/handover_daily_card.py` should exclude track names containing `0428.fgwh.黄老师综合班`, `弹唱`, or `三阶`; keep future exclusions centralized in `EXCLUDED_TRACK_NAME_GUARDS` rather than scattered inline conditions.
- a concrete failure mode: the dashboard read `p7dKLB!B1:D1` and applied its month value (for example `202604`) as a raw substring filter on track names from `vIajca`; this incorrectly hid tracks whose names do not contain that exact string, such as 书法 `【院长班】书法提升训练营-106期` and 口琴 `0330.fgwh.阿藤月课大盘课`
- baseline direct-source display filtering for `vIajca`:
  - match `sku`
  - require non-empty `承接轨次`
  - optionally filter `价格类型`
  - keep `contains_other_sku(track_name, sku)` guard to avoid cross-SKU dirty rows
- if the user explicitly wants “只看明确当月” for a month such as `202604`, do **not** use only raw substring matching; normalize current-month evidence from track names:
  - accept names containing `202604`
  - accept full date patterns whose year/month match `2026-04`
  - accept MMDD-style names whose month equals `04`, e.g. `0406`, `0420`, `0427`
  - reject off-month MMDD-style names such as `0330` for `202604`
  - if a SKU has no explicit current-month track names after this filter (observed: 书法), show the empty state rather than backfilling ambiguous tracks
- add debug counters when fixing this class of issue: source rows, SKU rows, empty-track rows, cross-SKU guard rows, price-filtered rows, month-filtered rows, included rows, grouped track count, and applied month filter value
- after patching, verify both data and render output: dry-run JSON should show expected `track_count` by SKU, excluded terms should be absent from card/cache payloads, and vision/visual QA should confirm track rows / empty states in the generated image/card
- When a dashboard push target changes, patch both the script constant (`~/.hermes/scripts/handover_daily_card.py::CHAT_ID`) and the Hermes cron job prompt for `每周一周四13:10交接数据经营看板推送`; then run `py_compile` and avoid sending a test card unless the user explicitly asks to push one.
- For a one-off test push to a different Feishu group, do **not** edit the script constant or cron prompt. Temporarily override `handover_daily_card.CHAT_ID` in the Python process, run `handover_daily_card.main()`, and verify the returned `message_id`; then re-read the script constant to confirm the scheduled target remains unchanged. This send path may refresh page cache and upload SKU images, so report that side effect explicitly.

Verified promotion pattern: one-off `承接轨次` sheet -> permanent realtime sync output:
- a previously ad hoc sheet `承接轨次` was successfully promoted into the main realtime sync task
- target workbook/tab:
  - workbook token: `<REDACTED_FEISHU_SPREADSHEET_TOKEN>`
  - sheet title: `承接轨次`
  - sheet_id: `vIajca`
- the stable implementation pattern is:
  1. add `sheet_ids.承接轨次: vIajca` in `config.yaml`
  2. add a dedicated builder in `run_sync.py`, for example `build_track_summary(helper: pd.DataFrame)`
  3. use `helper_df` directly; no new SQL query is needed because the required fields already exist after `build_detail()`
  4. derive:
     - `价格类型 = 商品价格`
     - `承接轨次 = 二阶轨次`
  5. group by `['商品SKU', '价格类型', '承接轨次']`
  6. aggregate exactly:
     - `学员数 = union_id.nunique()`
     - `加微数 = 已加微人数.sum()`
     - `衔接课开课人数 = 衔接课开课人数.sum()`
     - `正式课开课人数 = 已开课人数.sum()`
  7. rename `商品SKU -> sku`
  8. normalize empty `承接轨次` to `None`
  9. cast numeric columns with `cast_int_columns(...)`
  10. stable-sort by `['sku', '价格类型', '承接轨次']`
  11. wire it into `main()` together with the existing outputs:
      - create `track_df = build_track_summary(helper_df)`
      - export CSV `承接轨次_交接实时_{ts}.csv`
      - include `('承接轨次', track_df)` in `write_excel(...)`
      - add `upload_dataset(token, spreadsheet_token, SheetTarget('承接轨次', cfg['sheet_ids']['承接轨次']), track_df)`
      - include `rows_track` and `track_csv` in the printed summary JSON
- this is the preferred way to convert a proven one-off side-analysis tab into a maintained cron output without duplicating extraction logic or creating a second project

Verified removal pattern for `团队明细` writeback:
- if the user wants the cron/task to stop writing 团队明细, patch `main()` in `run_sync.py`
- remove:
  - `build_team_daily_summary(...)` assignment
  - `团队明细_交接实时_*.csv` output path and `write_csv(...)`
  - the `('团队明细', team_daily_df)` sheet from `write_excel(...)`
  - `upload_dataset(..., cfg['sheet_ids']['团队明细'], team_daily_df)`
  - summary fields `rows_team_daily` and `team_daily_csv`
- leaving `sheet_ids['团队明细']` in config is acceptable when it is unused by the script
- after patching, rerun the sync once so the current output artifact set matches the new behavior; future cron runs then inherit the change automatically

## 当前节点 semantics in realtime sync

`当前节点` is a row-level derived field in `build_detail()` inside `run_sync.py`.

Verified logic now used successfully:

- if `today > 营期封板日期 + 7天`, output `加微封板`
- else if `today > 营期封板日期`, output `营期封板`
- else output `D1/D2/D3/...` based on `(today - 营期开课日期) + 1`

Implementation pattern:

```python
start = row['营期开课日期']
end = row['营期封板日期']
today_norm = today.normalize()
if today_norm > (end + pd.Timedelta(days=7)):
    return '加微封板'
if today_norm > end:
    return '营期封板'
if pd.notna(start):
    day_no = (today_norm - start).days + 1
    if day_no >= 1:
        return f'D{day_no}'
return ''
```

Important nuance:
- before or on `营期封板日期`, keep the running D node instead of collapsing to `营期封板`
- `D` nodes are **not limited to D1-D3**; they continue as `D4/D5/...` until the end date boundary
- the switch points are strict `>` comparisons:
  - `today == 营期封板日期` -> still `D...`
  - `today == 营期封板日期 + 7` -> still `营期封板`
  - `today == 营期封板日期 + 8` -> `加微封板`

Regression-test pattern added successfully in `test_run_sync_metrics.py`:
- assert `D1/D2/D3`
- assert a later in-camp day like `D10`
- assert `营期封板日期 + 1 .. +7` are `营期封板`
- assert `营期封板日期 + 8` becomes `加微封板`

## 营期明细 / 日明细新增：开课节点

Use this pattern when the user asks to add or adjust the summary field `开课节点` in the realtime handover Feishu outputs.

Verified implementation pattern:
- do not change SQL for this field; it is a summary-level derived field in `run_sync.py`
- patch `build_camp_summary(helper, today)` and `build_daily_summary(helper, today)`; if `build_camp_summary` did not already accept `today`, update the `main()` call from `build_camp_summary(helper_df)` to `build_camp_summary(helper_df, today)`
- current verified threshold is SKU-specific:
  ```python
  def open_close_days_for_sku(goods_sku: Any) -> int:
      goods = '' if pd.isna(goods_sku) else str(goods_sku)
      return {
          '声乐': 21,
          '钢琴': 21,
          '口琴': 15,
          '书法': 21,
          '朗诵': 30,
      }.get(goods, 15)
  ```
  This means `声乐` / `钢琴` / `书法` use 21 days, `口琴` uses 15 days, `朗诵` uses 30 days, and unknown SKUs default to 15 days unless the user explicitly changes them.
- for `营期明细`, derive from `营期封板日期` plus the SKU-specific threshold:
  ```python
  today_norm = pd.Timestamp(today).normalize()
  close_dates = pd.to_datetime(source['营期封板日期'], errors='coerce').dt.normalize()
  source['开课节点'] = ''
  valid_close = close_dates.notna()
  close_days = pd.to_timedelta(source.loc[valid_close, '商品SKU'].map(open_close_days_for_sku), unit='D')
  source.loc[valid_close, '开课节点'] = (
      today_norm >= close_dates[valid_close] + close_days
  ).map({True: '开课封板', False: '未封板'})
  ```
- for `日明细`, derive from `支付日期` plus the SKU-specific threshold:
  ```python
  today_norm = pd.Timestamp(today).normalize()
  pay_dates = pd.to_datetime(source['支付日期'], errors='coerce').dt.normalize()
  source['开课节点'] = ''
  valid_pay = pay_dates.notna()
  close_days = pd.to_timedelta(source.loc[valid_pay, '商品SKU'].map(open_close_days_for_sku), unit='D')
  source.loc[valid_pay, '开课节点'] = (
      today_norm >= pay_dates[valid_pay] + close_days
  ).map({True: '开课封板', False: '未封板'})
  ```
- include `开课节点` in the relevant `group_cols`, otherwise rows with different node values can be merged incorrectly
- compare dates with `.normalize()`; null base dates should stay blank, not be treated as either `开课封板` or `未封板`
- do not modify `当前节点`; it is a separate row-level D/营期封板/加微封板 status

Verification pattern:
- run `py_compile` on `run_sync.py`
- run the local `test_run_sync_metrics.py`
- add/keep tests that construct helper rows on both sides of the threshold and assert:
  - `朗诵` at base date + 15 days is still `未封板`
  - `朗诵` at base date + 30 days is `开课封板`
  - `声乐` / `钢琴` and other 15-day SKUs still become `开课封板` at base date + 15 days
  - both `营期明细` and `日明细` are covered
  - `营期明细` final column remains `休学人数` if that field is present
- if local `test_run_sync_metrics.py` fails because old fixtures are missing already-existing fields such as `衔接课开课状态` / `衔接课开课人数`, report that separately; do not confuse that fixture drift with the new `开课节点` logic.

## 营期明细新增：封板加微分子

A verified camp-level field can be added to `build_camp_summary()`:
- field name: `封板加微分子`
- meaning: 截止 `营期封板日期 + 7天` 当天结束时，已完成加微的人数
- output target: `营期明细`

Implementation pattern:
1. in `source`, precompute a row-level boolean so grouped `apply()` does not depend on grouped-away columns:
   ```python
   source['封板加微命中'] = (
       source['已加微人数'].eq(1)
       & pd.to_datetime(source['加微时间'], errors='coerce').dt.normalize().le(
           pd.to_datetime(source['营期封板日期'], errors='coerce') + pd.Timedelta(days=7)
       )
   ).fillna(False)
   ```
2. aggregate with:
   ```python
   out['封板加微分子'] = int(group['封板加微命中'].sum())
   ```
3. add the field to:
   - `cast_int_columns(...)`
   - final returned camp-summary column order
4. rerun sync so Feishu `营期明细` gets the new column

Semantic note:
- cutoff is **inclusive by date** on `营期封板日期 + 7`
- this metric is camp-close-based, not “as of today”
- use `已加微人数 == 1` plus `加微时间` cutoff; if there is no `加微时间`, the row should not count toward this field

## 商品关键词排除规则

A verified source-SQL exclusion exists in the realtime/front-end handover SQL at the base order filter layer.

Current exclusion in realtime/front-end SQL:
```sql
AND NOT multiMatchAny(T3.goods_name, ['.*进阶班.*', '.*名师班.*', '.*祝老师.*'])
```

Current split-SQL ownership:
- 前端-二讲 / realtime sync uses:
  - `~/.hermes/sql/projects/handover-realtime-sync/交接数据-实时.sql`
  - keep the exclusion above
- 高阶交接 sync uses:
  - `~/.hermes/sql/projects/high-handover-feishu-sync/高阶交接数据.sql`
  - do **not** include the exclusion above, because high-stage rows can have 商品名称 containing `进阶班`

Implications:
- changing `交接数据-实时.sql` affects 学员明细 / 营期明细 / 日明细 / 承接轨次 for the realtime/front-end job
- changing `高阶交接数据.sql` affects only the 高阶交接明细全量写入飞书 job
- do not re-merge these two SQL files unless the user explicitly wants the same product-name filtering for both front-end and high-stage datasets

## Removing 新单 / payment-type restrictions

Use this pattern when the user asks to remove “新单口径”, `pay_type_name IN (...)`, or a payment-type restriction from the realtime/front-end handover SQL.

Current verified location in `交接数据-实时.sql`:
- the final exported field is `支付类型 = a1.pay_type_name`
- `pay_type_name` is derived from numeric `T1.pay_type`:
  - `1 -> 首款`
  - `2 -> 尾款`
  - `3 -> 全款`
- the actual restrictive predicate can be numeric rather than alias-based, for example:
  ```sql
  AND T1.pay_type IN (2, 3)
  ```

If the user says “去掉新单口径：`pay_type_name IN ('首款','全款')`这个限制” or similar:
1. Do not search only for the exact alias predicate; also search for `T1.pay_type IN (...)`, `pay_type`, `支付类型`, `首款`, `尾款`, and `全款`.
2. Create a timestamped backup beside the SQL file before patching.
3. Remove only the restrictive predicate, keeping the `pay_type_name` CASE expression and output column intact.
4. Run render validation and explicitly assert the old numeric and alias predicates are absent from the rendered SQL.
5. Do not automatically refresh Feishu unless the user explicitly asks for live writeback; report that the SQL change affects future sync runs.

Verified minimal patch example:
```diff
 WHERE T3.first_level_name = '课程'
-  AND T1.pay_type IN (2, 3)
   AND round(ifNull(T1.total_price, 0) / 100, 4) >= {{goods_price}}
```

## Feishu Sheets API retry hardening for realtime sync

If `交接实时数据同步到飞书` sends a failure card but the traceback points to `open.feishu.cn` during sheet writes, distinguish business failure from Feishu API/network failure.

Observed recoverable failures:
- `requests.exceptions.SSLError` / `SSLEOFError` / `UNEXPECTED_EOF_WHILE_READING` in `sheet_put_values`
- Feishu response `code=90217, msg='too many request'` during `sheet_put_values`, especially after a recent failed cron run or manual rerun

Hardening pattern in `~/.hermes/python/projects/handover-realtime-sync/run_sync.py`:
- wrap Feishu HTTP calls in a shared `feishu_request(method, url, **kwargs)` helper
- retry transient request exceptions: `SSLError`, `ConnectionError`, `Timeout`
- retry HTTP statuses: `429, 500, 502, 503, 504`
- honor `Retry-After` when present; otherwise exponential backoff with a cap
- use that helper for `feishu_token`, `get_sheet_metadata`, `append_dimension_range`, and `sheet_put_values`
- additionally retry Feishu JSON business error `code=90217` in `sheet_put_values` with a short exponential backoff before raising

Operational sequence:
1. Inspect latest `session_cron_3449f705d7a3_*.json` terminal output for `task='交接实时数据同步到飞书' exit_code=... card=...`.
2. If the failure is Feishu API/network only, do not change SQL or business logic.
3. Check no existing `handover-realtime-sync/run_sync.py` process is still running before a manual rerun.
4. Rerun with proxies cleared and verify `feishu_written: true` plus row counts.
5. Reopen the generated workbook and verify expected sheets and row counts.
6. Refresh the Notion memo after the row is back to `正常`, otherwise the memo may correctly continue showing the latest failure.

## Final-output SQL filters and live Feishu refresh

Use this pattern when the user asks to add exclusion conditions to “最后输出结果”, “最终输出”, or the final data written to the front-end handover Feishu workbook.

Current final result filter location in `交接数据-实时.sql`:

```sql
SELECT *
FROM export_base
WHERE 1 = 1
[[AND `营期阶段` = {{stage}}]]
[[AND `选期状态` = {{status}}]]
[[AND `加微状态` = {{status2}}]]
[[AND multiMatchAny(`union_id`, [replace({{union_id}}, ',', '|')])]]
-- add permanent final-output filters here
ORDER BY `支付时间` DESC
```

Guidelines:
- Put final-output filters in this last `WHERE` block when the user wants the exported/written result filtered after `export_base` derived fields are available.
- This is appropriate for filters on final aliases such as `商品名称`, `flow_no`, `选期状态`, `加微状态`, etc.
- Keep these filters outside `[[...]]` if they should always apply to the cron/live sync.
- Example verified filters:
  ```sql
  AND NOT multiMatchAny(`商品名称`, ['黄老师|祝老师'])
  AND `flow_no` NOT IN ('k2026040909310864166388')
  ```
- After changing the SQL and if the user asks to update Feishu immediately, run the business script directly with the absolute conda-env Python and proxies cleared; do not report `cronjob(action='run')` as completion unless you verified it actually ran.

Verified direct refresh command:

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy \
  /opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python \
  /Users/zheng/.hermes/python/projects/handover-realtime-sync/run_sync.py \
  --config /Users/zheng/.hermes/python/projects/handover-realtime-sync/config.yaml \
  --write-feishu
```

Successful output should include JSON keys such as:
- `rows_raw`, `rows_camp`, `rows_daily`, and usually `rows_track`
- `xlsx_path`
- `feishu_written: true`
- `spreadsheet_token: <REDACTED_FEISHU_SPREADSHEET_TOKEN>`

Report row counts and the latest xlsx path briefly.

## Feishu Docx / analysis-report metric pitfall: use daily-push handover口径

When rebuilding Feishu Docx reports or charts about “交接效率优化对退费率的影响”, do **not** recompute 选期率 / 加微率 from ad hoc `dwd_order_handover_df` logic unless the report explicitly says it is a separate exploratory口径.

Report-writing style learned from the 2026-05 Feishu Docx correction:
- Treat the output as a business report, not a process log. Do not include debugging/provenance wording in the final Docx such as “误用”, “修正口径”, “上一版”, source table names, or pipeline names.
- Keep the report concise. Prefer 3–4 sections: conclusion,口径, key SKU performance, overall judgment. Remove redundant method narration, local file paths, and long action lists unless the user explicitly asks for an appendix.
- State business口径 plainly, e.g. “交接指标按支付月 cohort 截止到月底 + 7 天”, instead of exposing implementation details.

Verified correction from the May 2026 refund-handover report:
- Wrong low口径 that caused mismatch with daily push:
  - source: `dwd_order_handover_df`
  - selected flag: `ast_emp_name/class_camp_id/class_camp_name` non-empty
  - wechat flag: `ast_friend_time` non-empty
  - denominator: non-refund orders
  - produced obviously low 声乐 values such as 3月选期率 `61.41%`, 4月选期率 `52.22%`
- Correct daily-push aligned口径:
  - source pipeline: `~/.hermes/sql/projects/handover-realtime-sync/交接数据-实时.sql` + `~/.hermes/python/projects/handover-realtime-sync/run_sync.py`
  - handover source: `drh_handover_plus`
  - wechat source: `drh_emp_external_user`
  - selected: final row field `选期状态 = '已选期'`
  - wechat: final row field `加微状态 = '已加微'`
  - for声乐 report scope, show both:
  - 全部订单
  - 核心口径：课程 + 全款/尾款 + 1880+ + 销转营期
  This was an explicit user correction: do not only show the core high-price course scope.
- Verified May 2026 声乐日常推送口径 values:
  - 全量订单分母：3月选期率 `92.73%`，加微率 `86.98%`；4月选期率 `97.63%`，加微率 `95.18%`
  - 非退费订单分母：3月选期率 `95.05%`，加微率 `90.90%`；4月选期率 `98.83%`，加微率 `96.85%`

Recommended workflow for future report/chart rebuilds:
1. Import `run_sync.py` and reuse `query_target_raw_df(...)` + `build_detail(...)` rather than hand-writing a parallel handover join.
2. Temporarily override `SKU_QUERY_RULES` in-memory for a one-off report if only one SKU is needed; do not patch the live cron config for one-off analysis.
3. For cohort-style report metrics, fix the observation window by pay month: `cohort_cutoff = pay_month_end + 7 days` (inclusive date). Example: April orders observe selection/add-WeChat events only through `4/30 + 7 days`; March orders observe only through `3/31 + 7 days`. This prevents older months from looking artificially higher because they had more time to complete handover.
4. Compute report selection/add-WeChat metrics from event timestamps, not current final status alone:
   - selection numerator: `加入营期日期 <= cohort_cutoff`
   - add-WeChat numerator: `加微时间 <= cohort_cutoff`
   - selected+WeChat rate: `(加入营期日期 <= cutoff AND 加微时间 <= cutoff) / selected_by_cutoff`
5. For声乐/refund-handover reports, include both the all-order scope and the core high-price course scope. Do not show only `课程订单 + 全款/尾款 + 1880+` unless the user explicitly asks to narrow it.
6. Make the chart/report wording business-facing; do not include debugging/process notes such as “误用”, “修正口径”, table names, or source-pipeline names in final report prose.
7. After replacing Feishu Docx images, verify raw content no longer contains stale low口径 values such as `61.41%` / `52.22%`, and no process/debug wording remains.
8. Keep refund-rate口径 separate from handover口径: refund rate can still come from the refund-analysis workbook / dwd order flow if that is the validated denominator, but handover percentages should use the fixed cohort window above.

## Dashboard/backend health-check pattern

Use this when the user asks whether the `交接数据看板` backend/service is normal. Do not assume there is a long-lived web service: this dashboard is primarily produced by scheduled scripts and cache files.

Recommended checks:
1. Check cron status first:
   - realtime sheet sync: job `3449f705d7a3` / `交接实时数据同步到飞书`
   - dashboard card push: job `e18060afea77` / `每周一周四13:10交接数据经营看板推送`
   - cache refresh: jobs `6118d99d625a` and `931371ae16d4`
2. Inspect latest session JSONs, not only cron `.md` output:
   - sync success should show `exit_code=0`, `feishu_written=true`, and row counts such as `rows_raw`, `rows_camp`, `rows_daily`, `rows_track`
   - card push success should show pre-run output `ok=true`, generated image paths, `page_cache_path`, `sku_image_keys`, and a `message_id`
3. Inspect cache file freshness:
   - `~/.hermes/cache/handover_daily_card_page_cache.json`
   - expected `sku_image_keys`: `书法`, `口琴`, `声乐`, `朗诵`, `钢琴`
4. Check for active long-lived processes only as a secondary signal. Absence of `handover` / dashboard processes is not necessarily abnormal because the normal path is cron-triggered script execution.
5. If checking process state through the Hermes terminal wrapper trips a false “long-lived server/watch process” guard on `ps` / `pgrep`, use `execute_code` with Python `subprocess` to run `ps aux` and filter lines.
6. If Docker is involved, verify Docker daemon separately. A failure like `failed to connect to the docker API at unix:///Users/zheng/.docker/run/docker.sock ... no such file or directory` means Docker Desktop/daemon is unavailable; it does not by itself prove the handover dashboard cron/script chain is broken.

Reporting rule:
- Say the business chain is normal only if recent sync/card/cache checks succeeded.
- Separately state whether any Docker/long-lived backend service is running or unavailable; do not conflate that with the cron-script dashboard pipeline.

## 营期明细新增：休学人数

Use this pattern when the user asks to add `休学人数` to the realtime handover Feishu workbook's `营期明细`.

Current lineage:
- SQL already emits row-level `休学状态` from `交接数据-实时.sql`.
- `build_detail()` must turn that row status into a numeric helper metric.
- `build_camp_summary()` must explicitly aggregate and return it; summary sheets do not inherit arbitrary SQL columns automatically.

Verified implementation pattern:
1. Do not change SQL if `休学状态` is already present in 学员明细.
2. In `build_detail(raw_df, today)`, add:
   ```python
   helper['休学人数'] = (helper['休学状态'] == '已休学').astype(int)
   ```
3. In `build_camp_summary(helper, today)`, add:
   - `休学人数` to the `agg()` output as `int(group['休学人数'].sum())`
   - `休学人数` to `cast_int_columns(...)`
   - `休学人数` to the returned column order
4. Column position for 营期明细:
   - put `休学人数` as the **last column** unless the user explicitly asks for a different position
   - verified final order tail: `... '衔接课开课人数', '销售团队', '开课节点', '休学人数'`
   - do not place it after `退费人数`; that was corrected by the user after the first implementation
5. Do not modify 日明细 / 承接轨次 / 团队明细 unless the user explicitly asks for the field there too.
6. Update tests/fixtures for any helper-level tests so they include both existing required helper fields and the new `休学人数`; if testing `build_detail()`, fixture raw rows need `休学状态` and existing required fields such as `衔接课开课状态`.

Verification pattern:
- run `python -m py_compile run_sync.py`
- run the local `test_run_sync_metrics.py`; this file is `unittest`-based, so if `python -m pytest ...` is unavailable in the selected conda env, run it directly with the same env Python:
  ```bash
  /opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python \
    /Users/zheng/.hermes/python/projects/handover-realtime-sync/test_run_sync_metrics.py
  ```
- render SQL and assert no residual `{{...}}` or `[[...]]` when SQL/template rendering changed; for a column-order-only Python change this can be skipped if no SQL/render code changed
- if the user says “不要重发”, “不要写飞书”, or only wants a local fix/verification, do **not** run the cron job and do **not** pass `--write-feishu`; validate with `run_sync.py --skip-feishu` so the script generates local CSV/XLSX only and prints `feishu_written: false`
- verify the generated workbook/CSV after local validation or refresh:
  - `营期明细` contains `休学人数`
  - its column order has `休学人数` as the final column
  - local workbook has expected sheets and non-zero size
  - optionally compute the `休学人数` total from the generated workbook/CSV as an extra sanity check
- after live refresh only when explicitly requested, report `feishu_written: true`, row counts, xlsx path, and the observed `休学人数` total if checked; if no live refresh was requested, explicitly report that Feishu was not written and `feishu_written: false`.

Operational note from the verified correction:
- If the user corrects the display order after a successful write, perform a minimal Python-only order change in `build_camp_summary()` and update the matching test assertion; then rerun the sync so Feishu is overwritten with the corrected column order.

## 交接数据经营看板卡片顶部指标调整

Use this pattern when the user asks to change the metrics shown at the top of the Feishu handover dashboard push card / SKU section, especially when they says “仅修改卡片服务，不重复执行推送”.

For the May 2026 top-metric time-range rollback, backend-track month switch, and calligraphy `105期+` display rule, first read `references/card-top-range-and-may-track-filter-2026-05.md`. It captures the current stable settings: `CAMP_START_DATE = 2026-03-30`, `DEFAULT_TRACK_MONTH_FILTER = 202605`, fixed service-side month selection instead of Feishu cell `p7dKLB!D1`, and the pitfall where `>=2026-05-01` makes mature open-rate mostly 0 because `开课节点=开课封板` has not matured for most May camps.

Recent verified card-service adjustment pattern:
- When the user asks to change the card's displayed time range, patch the presentation-layer constant in `~/.hermes/scripts/handover_team_report_card.py`, not the realtime sync SQL, unless they explicitly ask to change source data extraction.
- Current verified top-metric display range can be controlled with:
  - `CAMP_START_DATE = date(2026, 5, 1)`
  - `CAMP_RANGE_LABEL = f"营期开课日期≥{CAMP_START_DATE.isoformat()}"`
- Add the range label visibly in both image and Feishu interactive card text, not just in debug:
  - SKU image section header, e.g. `营期汇总｜营期开课日期≥2026-05-01`
  - overall image subtitle
  - interactive-card markdown, e.g. `指标范围：营期开课日期≥2026-05-01`
  - validation/debug summary fields such as `camp_range`
- If the new time range leaves no `开课封板` rows for a SKU, do not fail the whole card on `bridge_open = None`; display `开课率` as `0.0%` while keeping 加微率 / 选期率 computable. This avoids blocking cache refresh while still making the lack of mature open-rate data visible.

Backend-track month switching pattern:
- The card reads backend tracks from `承接轨次` sheet `vIajca`, then filters in `collect_track_source_rows(...)`.
- To switch backend tracks from April to May, set `DEFAULT_TRACK_MONTH_FILTER = "202605"`.
- If the card must reliably use the requested month, make `read_track_filter(...)` return `DEFAULT_TRACK_MONTH_FILTER` instead of inheriting stale Feishu filter cells such as `p7dKLB!D1 = 202604`; otherwise cache refresh can still show April even after changing the default constant.
- Keep `价格类型` from the Feishu filter if needed, but treat the month as a card-service controlled display setting when the user explicitly asks to switch it.

Verified calligraphy backend-track exception:
- For 书法 in May, business expects `105期及以后` to display even when track names do not contain explicit `202605`, `2026-05`, or `05xx` date tokens.
- Implement this as a SKU-scoped exception only, not a global month-filter relaxation:
  - `CALLIGRAPHY_MAY_MIN_TRACK_PERIOD = 105`
  - parse `(?<!\d)(\d{2,3})\s*期`
  - when `sku == "书法"` and `month_key == "202605"`, accept tracks whose parsed period is `>= 105`
  - keep `104期` excluded and keep non-书法 SKUs on normal month matching
- Add debug fields such as `month_filter_policy` and `calligraphy_may_min_track_period` so future diagnosis can distinguish normal month matching from the 书法 exception.

Safe validation after card-service changes:
1. Run syntax checks only first:
   ```bash
   /opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python -m py_compile \
     /Users/zheng/.hermes/scripts/handover_team_report_card.py \
     /Users/zheng/.hermes/scripts/handover_daily_card.py
   ```
2. Run local non-network assertions for constants and filters:
   - `CAMP_START_DATE.isoformat() == '2026-05-01'` when that is the requested range
   - `DEFAULT_TRACK_MONTH_FILTER == '202605'`
   - 书法 `105期` / `106期` pass for `202605`
   - 书法 `104期` does not pass
   - non-书法 tracks still use normal month matching
3. If the user expects existing card buttons to reflect the new logic, run cache-only refresh, not a new push:
   ```bash
   env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy \
     PYTHONPATH=/Users/zheng/.hermes/scripts \
     /opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python \
     /Users/zheng/.hermes/scripts/handover_daily_card.py --update-cache-only
   ```
4. Verify `~/.hermes/cache/handover_daily_card_page_cache.json` after refresh:
   - each SKU debug `total_metrics_source.start_date_min` matches the requested date
   - each SKU `track_source.applied_month_filter` is the requested month, e.g. `202605`
   - for 书法, `track_count` is non-zero and names include 105期及以后
   - `sku_image_keys` contains all five SKUs
5. Visual QA at least the affected SKU image, for example `~/.hermes/output/screens/handover_team_report/sku_sections/04_书法_handover_section.png`, to confirm the range label is visible and the expected backend tracks appear.

Current card-service files:
- primary card/SKU renderer: `~/.hermes/scripts/handover_team_report_card.py`
- push/cache wrapper importing it: `~/.hermes/scripts/handover_daily_card.py`

Important scope rule:
- This is a presentation-layer card-service change only.
- Do not run the realtime sync script, do not write Feishu sheets, do not run cron, and do not send a duplicate card unless the user explicitly asks.
- Do not use `--send-interactive-card` or `--update-cache-only` for validation when the user says not to push/re-run.

Verified implementation pattern for top metrics `开课率 / 加微率 / 选期率`:
- patch `build_sku(...)["totals"]` in `handover_team_report_card.py`
- keep the existing metric formulas; only change display title/order and remove `选期加微率` from top display:
  - `开课率` uses existing `bridge_open`
  - `加微率` uses existing `current_wechat`
  - `选期率` uses existing `select`
- verified target order:
  ```python
  "totals": [
      {"key": "bridge_open", "title": "开课率", ...},
      {"key": "current_wechat", "title": "加微率", ...},
      {"key": "select", "title": "选期率", ...},
  ]
  ```
- also update the text helpers so the Feishu card header/status matches the same three metrics:
  - `compact_sku_summary(...)`
  - `sku_status_markdown(...)`
  - `build_summary_table(...)` if used by the card path
  - `validation_summary(...)`
- it is okay to leave backend-track sections saying `后端轨次衔接课开课率` / `衔接课开课率` when those sections specifically describe track-level bridge-open metrics; do not rename every occurrence globally.

Safe validation without pushing:
1. create a timestamped backup beside the script.
2. run syntax checks only:
   ```bash
   /opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python -m py_compile \
     /Users/zheng/.hermes/scripts/handover_team_report_card.py \
     /Users/zheng/.hermes/scripts/handover_daily_card.py
   ```
3. validate card construction with local mock data rather than Feishu reads/uploads/sends. Expected evidence:
   - `total_titles == ['开课率', '加微率', '选期率']`
   - first markdown contains `开课率 ... 加微率 ... 选期率`
   - no `message_id` is produced.
4. Inspect the diff against the timestamped backup, not repo `git diff`, because `~/.hermes/scripts` may not be inside the active Git worktree.

Operational pitfall:
- If a Codex CLI run appears to hang after printing a coherent diff, inspect the file before retrying. It may have already written the patch even if the PTY does not exit cleanly. Re-read the target file before applying manual patches to avoid double edits.
- Updating the page cache is not a pure no-op for existing cards. Old Feishu cards keep their old button payloads, but the gateway callback rebuilds the clicked page from the **current** `handover_daily_card_page_cache.json` plus current `handover_team_report_card.py`.
- When removing a metric from top display, do not necessarily remove its underlying `totals` entry from cached datasets unless every callback/helper no longer calls `total_metric(..., that_key)`. A concrete failure observed after changing top metrics to `开课率 / 加微率 / 选期率`: cache-only refresh wrote `datasets[*]['totals']` without `selected_wechat`; old card clicks reached the gateway but failed with `Failed to build handover daily page card for sku=声乐: 'selected_wechat'`, making the old card appear unresponsive.
- Safer pattern for presentation-only top metric changes: separate **display metric order** from **cached metric inventory**. Keep compatibility-only metrics such as `selected_wechat` available in cached `totals` or make `total_metric`/text helpers robust to its absence, then verify an old-card-style callback can rebuild from the refreshed cache.
- If an old card stops responding after cache refresh, inspect `~/.hermes/logs/gateway.log` and `gateway.error.log` for `Failed to build handover daily page card`, `Patched handover daily card`, and missing-key errors before sending any new card. This is a callback/cache compatibility issue, not necessarily a Feishu gateway outage.

## Validation checklist after changes

Policy note from user:
- Do not modify the scheduled realtime sync task's business logic lightly.
- For this project, treat SQL filters, SKU scope, Python summary builders, and cron prompt/script wiring as production business logic.
- Changes should be minimal, explicitly scoped to the user's requested field/filter/metric, and backed up before patching.
- If a requested rollback only names one condition, restore only that condition and do not opportunistically change other existing diffs.

Before changing the SQL, create a timestamped backup beside the SQL file, for example:

```bash
cp ~/.hermes/sql/projects/handover-realtime-sync/交接数据-实时.sql \
  ~/.hermes/sql/projects/handover-realtime-sync/交接数据-实时.sql.$(date +%Y%m%d_%H%M%S).bak
```

After changing SQL templates or render parameters, run a two-level validation before reporting success:

1. Syntax/import validation:
   ```bash
   python -m py_compile /Users/zheng/.hermes/python/projects/handover-realtime-sync/run_sync.py
   ```
2. Render validation with `render_sql(...)`:
   - load `config.yaml`
   - render the SQL with one `SKU_QUERY_RULES` entry
   - assert there is no residual `{{...}}` or `[[...]]`
   - assert any newly introduced required placeholder such as `{{camp_sku}}` is actually rendered

For live Feishu confirmation, prefer the existing cron wrapper when the user asks to rerun the scheduled task, then verify completion through session output:
- trigger job `3449f705d7a3` / `交接实时数据同步到飞书` only when the user asked for the scheduled task behavior
- the stored cron prompt already runs both the Feishu-card wrapper and child `run_sync.py` with explicit proxy removal:
  - `env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy ...`
  - if the user says “不要走代理”, use `cronjob(action='run', job_id='3449f705d7a3')` first rather than hand-typing a new command, then verify the running process or latest session command line contains those `env -u ...` removals
- `cronjob(action='run')` only queues the immediate run. If a process is not visible after a short sleep, wait/re-list once more before assuming it did not start.
- after `cronjob(action='run')`, check the job's `next_run_at` and current `date`; the scheduler may execute shortly after the queued timestamp without leaving a long-lived process by the time you inspect it.
- before any direct fallback, re-check for a fresh `~/.hermes/sessions/session_cron_3449f705d7a3_*.json` created after the trigger time and inspect its terminal output. A fast successful cron run can finish before `ps` catches it.
- wait until no `handover-realtime-sync/run_sync.py` process from that cron run remains before any fallback
- do **not** launch a direct business-script rerun while the cron-triggered wrapper is still running or may still be queued; this can duplicate Feishu writes and confuse the audit trail even if the data is identical.
- inspect `~/.hermes/sessions/session_cron_3449f705d7a3_*.json` for the wrapper summary; success should include `task='交接实时数据同步到飞书' exit_code=0 ... card=sent`
- do not rely on `~/.hermes/cron/output/3449f705d7a3/*.md` alone because this job intentionally returns `[SILENT]`; the business result is in the latest session JSON's terminal tool output
- output JSON should include `feishu_written: true`, row counts, `xlsx_path`, and expected `spreadsheet_token`

If the cron-triggered run does not start or fails due to cron/gateway plumbing, then run the direct refresh command with proxies cleared and verify process exit code is `0`:

When comparing a rerun against a previous run, use local CSV exports instead of querying Feishu again. A reusable script is available:

```bash
/opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python \
  ~/.hermes/skills/data-science/handover-realtime-sync-maintenance/scripts/compare_handover_runs.py \
  <old_ts> <new_ts>
```

When the user asks for users whose add-WeChat status disappeared, export the regression list with:

```bash
/opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python \
  ~/.hermes/skills/data-science/handover-realtime-sync-maintenance/scripts/export_lost_wechat_users.py \
  <old_ts> <new_ts>
```

Finally, reopen the generated workbook with `openpyxl` or equivalent and verify:
- file exists and has non-zero size
- expected sheet names are present
- row/column counts look plausible

If the user also asks to refresh the handover Feishu card/cache after changing the source SQL, run the cache-only dashboard refresh after the sheet write succeeds. This keeps future SKU button callbacks aligned with the newly written source data without sending a duplicate card:

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy \
  PYTHONPATH=/Users/zheng/.hermes/scripts \
  /opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python \
  /Users/zheng/.hermes/scripts/handover_daily_card.py --update-cache-only
```

Verify the cache refresh by checking:
- process exit code is `0`
- `~/.hermes/cache/handover_daily_card_page_cache.json` exists and has a fresh mtime
- `data_updated_at` in the cache reflects the latest sheet/data refresh time
- `sku_image_keys` contains the expected five SKUs: `书法`, `口琴`, `声乐`, `朗诵`, `钢琴`
- `message_id` is absent or `None`, which is expected for `--update-cache-only`

Operational note for manual cache refresh:
- The cache-refresh cron job `6118d99d625a` / `交接经营看板分页卡片数据缓存更新` is safe to trigger first with `cronjob(action='run', job_id='6118d99d625a')`, but `cronjob(action='run')` can merely move `next_run_at` and not leave an immediate fresh session/process.
- After triggering it, verify there is a new `session_cron_6118d99d625a_*.json`, an active `handover_daily_card.py --update-cache-only` process, or a fresh cache file mtime. Do not assume the cache refreshed only because the tool returned success.
- If there is no fresh session/process/cache update after a short wait, run the direct `--update-cache-only` command above and verify the JSON output plus cache file. Report explicitly that no new Feishu card was sent.

Detailed checklist:

1. If a SQL field was added, confirm whether the request is only for 学员明细 or also for summary sheets.
2. If only 学员明细 matters, verify no script change is necessary.
3. If refund semantics changed, inspect the helper column definitions around:
   - `订单数`
   - `退费人数`
   - `已选期人数`
   - `已加微人数`
   - `已开课人数`
4. If `当前节点` logic changed, test all boundary dates explicitly:
   - `营期开课日期` D1/D2/D3
   - first non-D day
   - `营期封板日期`
   - `营期封板日期 + 7`
   - `营期封板日期 + 8`
5. Keep summary output columns unchanged unless the user explicitly asks for new fields there.
6. If asked to preview data with the new SQL, run the SQL directly and save CSV under `~/.hermes/output/query_results/`.

## Communication notes for this user

- Be precise about whether a field belongs to:
  - 订单来源营期（前端营期）
  - 二阶/承接营期
- When discussing “剔除退费”, confirm whether to change only the numerator, only the denominator, or both.
- If the user says “别的都不动”, make the smallest patch possible and say explicitly which metrics stay unchanged.
- Unless the user specifies another position, append newly added summary fields as the last column of the relevant realtime handover Feishu sheet.
- Handover dashboard/card push target, when needed for this workflow: Feishu group `oc_56753346ea5a491750fbfd6bfd3470c3`.
- If the user asks to modify dashboard/card service only and says not to push, patch only `~/.hermes/scripts/handover_team_report_card.py` / `~/.hermes/scripts/handover_daily_card.py`, run local validation, and do **not** run `--send-interactive-card`, `--update-cache-only`, or any Feishu send/upload path unless explicitly requested. Code changes do not refresh `~/.hermes/cache/handover_daily_card_page_cache.json`; if the user later asks whether backend data updated, check cache mtime/data_updated_at and say it is unchanged unless a cache-only refresh actually ran.
