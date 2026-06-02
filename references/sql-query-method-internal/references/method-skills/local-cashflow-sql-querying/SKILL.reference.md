---
name: local-cashflow-sql-querying
description: Query the user's local cashflow ClickHouse and ODPS data sources using saved key files and the dedicated conda environment.
---

# Local cashflow SQL querying

Use this when the user wants Hermes to query their local **ClickHouse** or **ODPS** cashflow data sources, especially for ad hoc SQL, result exports, or validating business metrics.

## Preconditions

- Always run Python scripts in the conda environment:
  - `hermes-sql`
- Saved credentials live under:
  - `~/.hermes/config/keys/clickhouse_key.json`
  - `~/.hermes/config/keys/odps_key.json`
- Compatibility symlinks also exist:
  - `~/.hermes/clickhouse_key.json`
  - `~/.hermes/odps_key.json`
- Do **not** persist broad local project snapshots as generic config. Keep only key/credential files as the durable local config.

## Directory conventions

Use these directories under `~/.hermes/`:

- SQL scripts:
  - `~/.hermes/sql/clickhouse/`
  - `~/.hermes/sql/odps/`
  - `~/.hermes/sql/common/`
- Python scripts:
  - `~/.hermes/python/clickhouse/`
  - `~/.hermes/python/odps/`
  - `~/.hermes/python/common/`
- Outputs:
  - `~/.hermes/output/query_results/`
  - `~/.hermes/output/exports/`
  - `~/.hermes/output/temp/`
  - `~/.hermes/output/logs/`
- Cleaned results:
  - `~/.hermes/cleaned/cashflow/`
  - `~/.hermes/cleaned/projects/`
  - `~/.hermes/cleaned/archive/`

## ClickHouse workflow

### Credentials

`~/.hermes/config/keys/clickhouse_key.json`

Expected JSON shape:

```json
{
  "host": "...",
  "port": 9000,
  "user": "...",
  "password": "...",
  "database": "drh"
}
```

### Minimal connection test

```bash
eval "$(conda shell.bash hook)"
conda activate hermes-sql
python - <<'PY'
import json
from clickhouse_driver import Client
with open('/Users/zheng/.hermes/config/keys/clickhouse_key.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)
client = Client(**cfg)
print(client.execute('SELECT version()'))
print(client.execute('SELECT currentDatabase()'))
print(client.execute('SELECT 1'))
client.disconnect()
PY
```

### Query pattern

Use `clickhouse_driver.Client(...).query_dataframe(sql)` when the user wants exports or tabular post-processing with pandas.

Typical script structure:

```python
import json, os
from datetime import datetime
import pandas as pd
from clickhouse_driver import Client

with open('/Users/zheng/.hermes/config/keys/clickhouse_key.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

client = Client(**cfg)
df = client.query_dataframe(SQL)
client.disconnect()

out_dir = os.path.expanduser('~/.hermes/output/query_results')
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, f'result_{datetime.now():%Y%m%d_%H%M%S}.csv')
df.to_csv(out_path, index=False, encoding='utf-8-sig')
```

## ODPS workflow

### Credentials

`~/.hermes/config/keys/odps_key.json`

Expected JSON shape:

```json
{
  "access_id": "...",
  "secret_key": "...",
  "project": "drh_prod_odps",
  "endpoint": "http://service.cn-beijing.maxcompute.aliyun.com/api"
}
```

### Main local project script

The user's ODPS main script is:

`/Users/zheng/Desktop/PrivateProject/Python/项目/现金流数据-odps/main.py`

### Minimal connection test

```bash
eval "$(conda shell.bash hook)"
conda activate hermes-sql
python - <<'PY'
import json
from odps import ODPS
with open('/Users/zheng/.hermes/config/keys/odps_key.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)
o = ODPS(cfg['access_id'], cfg['secret_key'], cfg['project'], cfg['endpoint'])
inst = o.execute_sql('select 1 as x')
inst.wait_for_success()
with inst.open_reader() as reader:
    print(list(reader))
PY
```

## Important template/parameter pitfalls

### ClickHouse template style from the user's local project

The local ClickHouse SQL executor uses placeholders like:

- `{{start_date}}`
- `{{end_date}}`

and often optional blocks like:

- `[[AND toDate(a1.pay_time) <= {{end_date}}]]`
- `[[AND {{main_goods_sku}}]]`

**Important:** placeholders such as `{{main_goods_sku}}` may represent a **full predicate**, not just a scalar value.

So before substituting, clarify whether the business meaning is:

- `a1.main_goods_sku = '声乐'`
- `a1.camp_sku = '声乐'`
- `a1.main_goods_name like '%声乐%'`
- or some broader product-line definition.

Do **not** assume the correct field if the user’s metric wording is ambiguous.

### ClickHouse validation pitfalls discovered locally

When rendering / sanity-checking templated SQL against ClickHouse, do not assume every date-like filter column is actually a `Date` type.

Verified in this environment:

- `dwd_order_flow_df.dt` is a `String`
- `dwd_order_flow_df.pay_time` is a `DateTime`

So for ad hoc validation or placeholder substitution:

- predicates on `toDate(a1.pay_time)` should use `toDate('YYYY-MM-DD')`
- predicates on `a1.dt` should use quoted string literals like `'YYYY-MM-DD'`
- do **not** substitute `a1.dt >= {{start_date}}` with `a1.dt >= toDate('YYYY-MM-DD')` or ClickHouse may error with a String-vs-Date type mismatch

Also verified in this environment for `dwd_order_flow_df`-based handover queries:

- `nick_name` is not present directly on `dwd_order_flow_df`; a workable source is `tock_applet_user` via `applet_user_id` + `argMax(nick_name, create_time)`
- `营期开课日期` / `营期封板日期` / `营期阶段` can be aligned to the realtime query by joining `dim_camp_df` on `camp_id`
- In `交接数据-实时.sql`, the optional placeholder `[[AND {{main_goods_sku}}]]` sits inside the `drh_business_line` subquery and effectively filters **商品sku / business line name**, not `camp_sku` / `营期sku`
- Because of that, filtering `main_goods_sku` to `声乐` / `钢琴` can still return cross-product rows where `商品sku` is one of those values but `营期sku` belongs to another line (observed examples: `声乐IP季课`, `口琴`, `朗诵`, `养生`)
- If the user asks for a **strict SKU subset** for handover results, validate both columns after query and, if needed, post-filter on **both** `商品sku` and `营期sku` (or change the SQL explicitly) rather than trusting `main_goods_sku` alone
- When recreating a Feishu-style handover workbook locally, first generate a local Excel preview from the SQL result if the user has not explicitly asked for online writeback
- For the Hermes realtime handover project at `~/.hermes/python/projects/handover-realtime-sync/`, the SQL file is configured by `config.yaml` and raw-detail output is column-dynamic: adding a new SQL column will automatically flow into the exported/Feishu-written `学员明细` dataset because `run_sync.py` writes `raw_df` columns as-is. However, `营期明细` and `日明细` are rebuilt in Python; `build_camp_summary()` uses explicit `group_cols` / returned columns, so newly added SQL fields (for example `营期轨次`) do **not** appear there unless `run_sync.py` is updated too. When changing handover SQL schemas, always inspect the downstream Python summary builders before saying cron/script changes are unnecessary.

### ODPS template style from the user's local project

The ODPS project uses `${param}` style placeholders, e.g.:

- `${start_date}`
- `${end_date}`

## Cross-source table mapping: ODPS vs ClickHouse

Do **not** assume ODPS and ClickHouse table names are always identical.

Empirical findings from the user's local environment:

- ClickHouse database: `drh`
- Many ODPS-synced tables in ClickHouse use a `tock_` prefix rather than the original ODPS name.
- Another common pattern is `drh_*` tables landing as `drh_*_local` in ClickHouse.
- Some tables do remain exactly the same name across both systems.
- Some ODPS tables have **no clear ClickHouse counterpart** and should be treated as ODPS-only unless verified.

Examples already verified in this environment:

- `dwd_order_flow_df` -> ClickHouse same name `dwd_order_flow_df`
- `dwd_order_refund_df` -> `tock_dwd_order_refund_df`
- `dws_cash_account_indicators_md_pdf` -> `tock_dws_cash_account_indicators_md_pdf`
- `ods_feishu_refund_approval_detail_all_d` -> `tock_ods_feishu_refund_approval_detail_all_d`
- `dwd_order_handover_df` -> ClickHouse same name `dwd_order_handover_df`
- `dws_netcashflow_gmv_df` -> ClickHouse same name `dws_netcashflow_gmv_df`
- `ods_offline_finance_subject_df` -> no verified ClickHouse counterpart yet
- `dws_netcashflow_cost_df` -> no verified ClickHouse counterpart yet
- `dws_pl_cost_md_pdf` -> no verified ClickHouse counterpart yet

### Recommended lookup order when the user gives a business scenario

1. Start from the user's explicitly common tables if relevant.
2. In ODPS, prioritize `dwd_` / `dws_` tables.
3. Then check cron / project SQL referenced tables.
4. If the result needs ClickHouse, check in this order:
   - exact same table name
   - `tock_<odps_table_name>`
   - likely `drh_*_local` candidate
5. Validate by comparing columns rather than trusting the name alone.
6. If the scenario is approval / sync / raw-detail oriented, also inspect `ods_` tables.

### Local schema knowledge base first, then live verification

A reusable local metadata KB now exists under:

- `~/.hermes/cleaned/projects/sql-metadata-index/index/unified_schema_index.json`
- `~/.hermes/cleaned/projects/sql-metadata-index/index/field_to_tables.json`
- `~/.hermes/cleaned/projects/sql-metadata-index/index/table_mapping.json`
- `~/.hermes/cleaned/projects/sql-metadata-index/index/refresh_summary.json`
- `~/.hermes/cleaned/projects/sql-metadata-index/index/schema_kb.md`

The incremental refresh script is:

- `~/.hermes/python/projects/sql-metadata-index/refresh_schema_kb.py`

### Recommended workflow for ad hoc CK / ODPS SQL (important)

When the user asks for a new SQL metric or dashboard query, do **not** jump straight to final SQL from business wording.

Use this order:

1. Check the local schema KB first to shortlist likely tables, fields, and ODPS↔CK mappings.
2. Run live metadata checks against the actual source before writing the final SQL.
3. Validate important value enumerations / examples.
4. Only then write the formal SQL.

This workflow was adopted after a real failure where `tock_applet_user` was assumed to have `main_goods_sku`, but the real field was `sku`.

### Live metadata checks to run before final SQL

At minimum, validate:

- physical field existence
- join keys
- business-line field names
- stored enum values / example values
- ClickHouse-version-specific syntax constraints

For ClickHouse, a good minimum set is:

```sql
SELECT table, name, type, position
FROM system.columns
WHERE database = currentDatabase()
  AND table IN ('tock_applet_user', 'dwd_order_flow_df', 'drh_emp_external_user', 'drh_emp_external_user_del')
ORDER BY table, position;
```

Then inspect candidate values, e.g.:

```sql
SELECT sku, count()
FROM tock_applet_user
GROUP BY sku
ORDER BY count() DESC
LIMIT 50;
```

```sql
SELECT pay_type_name, pay_status_name, count()
FROM dwd_order_flow_df
GROUP BY pay_type_name, pay_status_name
ORDER BY count() DESC
LIMIT 50;
```

### dwd_order_flow_df only-first-payment order exports

Session-specific reference for appending `休学/冻课` analysis sheets to a leadership workbook for this order pool is available at `references/first-payment-only-stop-freeze-report-20260429.md`. It records the verified rest/freeze sources (`drh_handover_plus`, `dev_stop_stu_record`), order-number join rule, ClickHouse driver alias-prefix workaround, and Excel timestamp cleanup.

For large user relationship exports combining refund users, first-payment users, Enterprise WeChat friend rows, recent message interaction, learning records, service status, and official-class flags, see `references/clickhouse-user-relationship-export-20260519.md`. It records the stable chunking approach, ClickHouse 21.8 query pitfalls, and the Excel column-completion guard needed before writing multi-sheet workbooks.

For the preferred compact version of this class of export, see `references/clickhouse-user-relationship-export-userlevel-20260519.md`: split queries, merge locally in pandas, and summarize friend relations per `union_id` instead of exporting one row per friend relation.

For the 2026-05-08 historical all-data Feishu workbook (`20260508_历史首款/冻课学员`), including four-tab writing, class-attendance enrichment from `tock_ast_process_data`, the latest `tock_handover_plus` + `drh_handover_plus.stop_study_status` 休学冻课口径, summary layout preferences, numeric-format rules, and Feishu write pitfalls, see `references/first-payment-stop-freeze-feishu-20260508.md`.

A newer reference for the historical full-data Feishu four-tab workflow is available at `references/first-payment-stop-freeze-history-feishu-20260508.md`. Use it when rebuilding `首款订单汇总 / 首款订单明细 / 冻课汇总 / 冻课明细`, especially for the combined `休学冻课` concept, the newer user-provided `休学/未分配` flag SQL, class-attendance join to `tock_ast_process_data`, extra detail fields (`成交人/交接学管/课包价格/成交营期阶段`), and Feishu write pitfalls including the 5M-cell limit. Latest corrections for the 2026-05-08 workflow are in `references/first-payment-stop-freeze-history-feishu-20260508-latest.md`: do not UNION the `tock_order NOT IN tock_handover_plus` branch into 未分配, allow empty `service_camp_name` when `stop_study_status=1` for 休学, include 手机号 and 商品名称 in detail exports, and rebuild overgrown Feishu detail sheets when legacy grid size triggers `cells excess:5000000`.

When the user asks for “只付首款 / 仅首款未付尾款 / 首款 flow_no 没有被尾款关联” from `dwd_order_flow_df`, use the order-flow linkage rather than only user-level counts. 首款 flow_no 没有被尾款关联” from `dwd_order_flow_df`, use the order-flow linkage rather than only user-level counts.

Verified field mapping in ClickHouse:
- `pay_type_code = 1`, `pay_type_name = '首款'` = first payment row
- `pay_type_code = 2`, `pay_type_name = '尾款'` = tail payment row
- `flow_no` = current order-flow number
- `relate_flow_no` on tail-payment rows = related first-payment `flow_no`
- `refund_amount` on `dwd_order_flow_df` can be used as the order row's corresponding refund amount when the user wants refund included alongside `pay_amount`

Recommended grain and anti-join:

```sql
WITH tail_pay AS (
    SELECT relate_flow_no
    FROM dwd_order_flow_df
    WHERE pay_status_name = '支付成功'
      AND pay_type_code = 2
      AND pay_type_name = '尾款'
      AND relate_flow_no != ''
    GROUP BY relate_flow_no
)
SELECT
    formatDateTime(toStartOfMonth(f.pay_time), '%Y-%m') AS pay_month,
    count() AS order_cnt,
    round(sum(f.pay_amount), 2) AS pay_amount,
    round(sum(f.refund_amount), 2) AS refund_amount
FROM dwd_order_flow_df f
LEFT JOIN tail_pay t ON f.flow_no = t.relate_flow_no
WHERE f.pay_status_name = '支付成功'
  AND f.pay_type_code = 1
  AND f.pay_type_name = '首款'
  AND f.main_first_level = '课程'
  AND t.relate_flow_no = ''
GROUP BY pay_month
ORDER BY pay_month
```

Important interpretation/validation rules:
- This is **order-flow grain**, not user grain. A user can have multiple orders, some with tail payments and some without; do not collapse to user-level unless explicitly requested.
- Always verify `count() = uniqExact(f.flow_no)` before claiming the result is not duplicated.
- If the amount looks too high, split by `main_first_level`; broad all-category scope can include high-ticket `权益` / travel / activity products and materially inflate totals.
- For business “课程 only” use `f.main_first_level = '课程'` unless the user explicitly wants all product categories.
- Keep `pay_amount` as GMV when requested; add `refund_amount` separately rather than silently switching to `net_received_amount`.
- For user-facing files, export `.xlsx` with Chinese headers and numeric cell formats, then reopen the workbook to verify numeric cell types.

### 商品名称关键词订单明细导出

For ad hoc requests like “导一份某月所有商品名称包含 A 或 B 的订单明细”, use the reusable pattern in `references/order-keyword-detail-export.md`: ClickHouse `dwd_order_flow_df`, `pay_time` natural-month window, `main_goods_name` keyword matching via `positionUTF8`, default `pay_status_name='支付成功'`, Excel with `口径说明/汇总/状态校验/订单明细/字段校验/SQL`, and reopen validation for row counts and numeric cells.

## Mini-program / merchant-specific order lookup pattern

When the user asks for orders like “某小程序支付的，且收款商户号是某个 `mch_id` 的订单明细”, do **not** rely on `dwd_order_flow_df.pay_source` alone.

Also verify the physical columns on `dwd_order_flow_df` before promising a pure-`dwd_order_flow_df` solution.

Verified locally in this environment:
- `dwd_order_flow_df` has `mch_id`
- `dwd_order_flow_df` does **not** have `app_id`
- therefore `dwd_order_flow_df` can strictly filter **merchant-level paid orders** for a given `mch_id`
- but it cannot, by itself, strictly isolate a specific mini-program/app under that merchant

Practical implication:
- if the user insists on `dwd_order_flow_df`, the safe export is:
  - `WHERE mch_id = '<target_mch_id>' AND pay_status_name = '支付成功'`
- and you must explicitly call out that this is a merchant-scope export, not an app-scope export
- if the user wants strict app / mini-program scope, you still need another table that carries `app_id` (for example `drh_common_order` / `drh_common_order_local` or another verified source) to resolve that mapping first

Verified locally:

- `dwd_order_flow_df.pay_source` comment is `支付类型 1-微信 2-支付宝 3-微信小程序 4-蚂蚁花呗 默认1`
- but for merchant `1616437306`, the actual distribution still showed mostly `pay_source = 1`
- the WeChat bill detail tables
  - `tock_ods_odps_qw_bill_detail_plus_rf`
  - `ods_ots_qw_bill_detail_plus_rf`
  had `0` rows for that merchant in this environment, so they were **not** usable as the source of truth for this request

A more reliable pattern was:

1. Look up the merchant/app mapping in `drh_wx_pay_base`:

```sql
SELECT mch_id, app_id, name, app_type
FROM drh_wx_pay_base FINAL
WHERE _sign > 0
  AND mch_id = '1616437306'
```

2. Identify the target mini-program by `name` / `app_id`.

Verified example:
- `mch_id = 1616437306`
- `app_id = wx874eac9ca7c7e9b2`
- `name = 华彩畅学园`
- `app_type = 28`

3. Pull the order detail from a business order table using that exact `app_id`.

For the verified “华彩畅学园” case, `drh_common_order_local` worked:

```sql
SELECT
    c.order_no,
    c.union_id,
    c.goods_id,
    c.price / 100.0 AS amount_yuan,
    c.pay_time,
    c.pay_status,
    c.pay_origin,
    c.pay_no,
    c.mch_id,
    c.app_id,
    p.name AS app_name,
    p.app_type,
    c.camp_id,
    d.camp_name,
    c.category,
    c.is_class,
    c.buy_count
FROM drh_common_order_local c FINAL
LEFT JOIN (
    SELECT mch_id, app_id, any(name) AS name, any(app_type) AS app_type
    FROM drh_wx_pay_base FINAL
    WHERE _sign > 0
    GROUP BY mch_id, app_id
) p ON c.mch_id = p.mch_id AND c.app_id = p.app_id
LEFT JOIN dim_camp_df d ON c.camp_id = d.camp_id
WHERE c._sign > 0
  AND c.mch_id = '1616437306'
  AND c.app_id = 'wx874eac9ca7c7e9b2'
  AND c.pay_status = 2
ORDER BY c.pay_time DESC
```

4. If the user wants all attempts instead of only successful payments, remove or relax `c.pay_status = 2`.

### Practical findings for this pattern

- `drh_common_order_local.pay_origin` showed `applet` for the verified 华彩畅学园 records.
- In this environment, `drh_common_order_local.pay_status` used:
  - `1`
    - pending / not-successful-yet
  - `2`
    - paid successfully
- A request phrased as “通过某小程序支付的订单明细” should usually be interpreted as **paid-success orders**, but if the user may want all order attempts, clarify or provide both counts.
- Joining `drh_common_order_local.order_no` directly to `dwd_order_flow_df.flow_no` / `collect_order_no` did **not** match for the verified 华彩畅学园 sample, so do not assume those IDs are interchangeable.

### ClickHouse 21.8 / drh table pitfalls discovered locally

In this environment, the user is on ClickHouse `21.8.2.1` and `drh_*` tables often require special handling.

When querying `drh` sign-based tables:

- prefer `FINAL`
- include `WHERE _sign > 0`
- if you need an alias after `FINAL`, wrap the table first:

```sql
FROM (
    SELECT *
    FROM drh_emp_external_user FINAL
    WHERE _sign > 0
) AS e
```

Do **not** write:

```sql
FROM drh_emp_external_user FINAL e
```

Also remember:
- if the user wants Chinese output headers in ClickHouse, use backticks around the alias names
- but keep intermediate/debug SQL conservative for compatibility with 21.8

### Minimal ClickHouse metadata queries for mapping

List tables:

```sql
SELECT name
FROM system.tables
WHERE database = currentDatabase()
ORDER BY name;
```

List columns for a target table:

```sql
SELECT table, name, type, position
FROM system.columns
WHERE database = currentDatabase()
  AND table = 'target_table'
ORDER BY position;
```

When building a mapping, compare:

- table-name similarity
- shared column names
- partition / sort keys when useful
- whether business-key fields (e.g. `flow_id`, `order_no`, `refund_amount`) line up

## Cohort / refund-rate exports from cashflow-core source files

When the user wants an ad hoc **cohort退款率明细表** (not the existing `run_cohort.py` workbook), a proven local pattern is:

1. Run the Hermes cashflow-core ODPS source queries for at least:
   - `订单明细.sql`
   - `退款明细.sql`
2. Reuse the cashflow-core config under:
   - `~/.hermes/config/projects/cashflow-core/defaults.yaml`
   - `~/.hermes/config/projects/cashflow-core/cashflow_monthly_sheet.yaml`
3. In Python, import `run_cashflow_queries` from:
   - `~/.hermes/python/projects/cashflow-core/automatic/data_sources/cashflow.py`
4. For long-range pulls, pass explicit dates instead of the monthly-sheet task default window, e.g.:
   - `start_date='2025-01-01'`
   - `end_date='<today>'`
5. Build cohort metrics by:
   - parsing `支付日期` into `支付自然月`
   - converting `gmv` / `退款gmv` to numeric
   - grouping `退款明细` by `订单号` first and summing refund amount
   - left-joining the grouped refund back onto `订单明细`
   - aggregating by the requested dimensions
6. A reusable metric definition that matched the user's expectation:
   - `cohort退费 = 订单维度累计退款金额`
   - `cohort退费率 = 退费 / gmv`

### Frontend filter pattern

For requests like “前端 sku×渠道×自然月”, a proven filter is:

- `orders['前后端'].astype(str).str.contains('前端', na=False)`

This matched local values such as:
- `大前端`
- `大前端-华彩乐园`

### Channel dimensions already available in source CSVs

The cashflow source CSVs already contain reusable channel fields:
- `渠道`
- `渠道聚合类型`
- `渠道归属人`

So if the user asks for:
- `sku × 渠道 × 自然月`
- `sku × 渠道聚合类型 × 自然月`
- or similar refund/cohort outputs

prefer building a direct export from `订单明细.csv` + `退款明细.csv` rather than forcing the `run_cohort.py` workbook shape.

## Frontend 渠道聚合类型续费率 from ClickHouse handover/order data

When the user wants a **聚合渠道续费率** based on front-end sell-stage orders rolling into second-stage orders, a proven local pattern is:

### Metric definition used successfully

- scope: `dwd_order_flow_df` joined with `drh_live_camp`
- front-end filter: `a.new_front_end_name LIKE '%前端%'`
- base pool (denominator): paid orders where the joined camp is sell-stage
  - `c.is_class = 0`
- renewal pool (numerator): those base orders whose user later appears in a second-stage paid order
  - second-stage condition:
    - `c.is_class = 1`
    - `c.class_stage = 2`
- time direction: second-stage order must satisfy
  - `second_pay_time > base.pay_time`
- grouping:
  - `支付自然月 = formatDateTime(toStartOfMonth(base.pay_time), '%Y-%m')`
  - `渠道聚合类型 = studio_lv2`
- result fields:
  - `销转订单数`
  - `续费订单数`
  - `续费率 = 续费订单数 / 销转订单数`

### Same-SKU renewal constraint

If the user says the sell-stage order and second-stage order must be SKU-aligned, the working constraint is:

- `base.main_goods_sku = second.camp_sku`

In other words:
- sell-stage side uses `dwd_order_flow_df.main_goods_sku`
- second-stage side uses `dwd_order_flow_df.camp_sku`

This stricter rule materially lowers renewal rates versus a user-only match, so be explicit about which version was used.

### Recommended SQL shape

Use two CTEs plus one order-level flagging step:

1. `base`
   - select `flow_no`, `union_id`, `main_goods_sku`, `pay_time`, `toStartOfMonth(pay_time)`, `studio_lv2`
   - filter to front-end + sell-stage + positive paid amount
2. `second_orders`
   - select `union_id`, `camp_sku`, `pay_time`
   - filter to second-stage + positive paid amount
3. `base_flag`
   - left join `second_orders` on `union_id`
   - compute `max(if(second_pay_time > base.pay_time [and same-sku], 1, 0)) AS renewed_flag`
   - group by `flow_no` so each base order contributes at most one renewed flag
4. final aggregate
   - group by month/channel
   - `count()` as denominator
   - `sum(renewed_flag)` as numerator

### Driver pitfall: avoid Chinese aliases inside the ClickHouse query

A real local failure was observed when using Chinese aliases directly in the SQL and fetching through `clickhouse_driver`:

- error surfaced as a `UnicodeDecodeError` while reading the server exception/result packet

A reliable workaround is:
- keep SQL aliases ASCII-only, such as:
  - `pay_month_str`
  - `channel_type_norm`
  - `base_orders`
  - `renewed_orders`
  - `renew_rate`
- fetch results first
- then rename columns in pandas before export

This avoids fragile encoding behavior in the driver while still producing Chinese headers in the final CSV/XLSX.

## Merchant/app mapping findings for 华彩畅学园-related exports

A reusable ambiguity was found for merchant `1616437306` when the user asks for “华彩畅学园小程序支付订单”. Do not assume a single app id.

### Verified source tables and meanings

- `drh_wx_pay_base`
  - configuration / merchant-app registry
  - contains `mch_id`, `app_id`, `name`, `app_type`
- `drh_common_order`
  - has `mch_id`, `app_id`, `pay_origin`, `pay_status`, `pay_no`, `order_no`
  - usable for app-scoped paid-order exports from the common-order path
- `drh_h5_order`
  - has `mch_id`, `app_id`, `is_callback`, `order_no`, `pay_no`
  - despite the table name, some historical app-like traffic for this merchant lands here
- `dwd_order_flow_df`
  - has `mch_id`, `collect_order_no`, `flow_no`, `pay_amount`, `pay_time`, `main_goods_name`, `main_goods_sku`, `camp_sku`
  - but direct joins from `drh_common_order.pay_no/order_no` to `dwd_order_flow_df.collect_order_no/flow_no` were verified to return 0 rows for the 华彩畅学园 common-order sample, so do not promise a direct join path without re-validating

### Verified app mapping for merchant 1616437306

From `drh_wx_pay_base`:

- `wx874eac9ca7c7e9b2`
  - name: `华彩畅学园`
  - active config row seen with `app_type = 28`, `_sign = 1`
  - older deleted config row also exists with `app_type = 67`, `_sign = -1`
- `wxb3d07ba48aab6de2`
  - older config name `28`
  - observed in `drh_common_order` as the main historical applet order app_id for this merchant
- `wx77ccd99ebd2f86ce`
  - config name `67`
  - observed heavily in `drh_h5_order`
  - whether the user intends this to be counted as “华彩畅学园” is ambiguous and should be confirmed

### Verified paid-order volumes at time of discovery

- `drh_common_order`
  - `app_id = 'wxb3d07ba48aab6de2'`, `pay_origin='applet'`, `pay_status=2` -> `289446`
  - `app_id = 'wx874eac9ca7c7e9b2'`, `pay_origin='applet'`, `pay_status=2` -> `34`
- `drh_h5_order`
  - `app_id = 'wx77ccd99ebd2f86ce'`, `is_callback=1` -> `513742`
  - `app_id = 'wx874eac9ca7c7e9b2'`, `is_callback=1` -> `0`

### Recommended handling when the user asks for 华彩畅学园 orders

1. First check `drh_wx_pay_base` for the merchant's app registry.
2. Then check both `drh_common_order` and `drh_h5_order` for actual paid-order landing tables.
3. If “华彩畅学园” could mean multiple historical app ids (`28` / `67` / current named app), explicitly confirm the inclusion scope before exporting.
4. Only call it a single-app export if the user clearly names the exact `app_id` or confirms the intended historical mapping.

## 轨次续费订单查询（营期轨次 / 二阶续费）

A reusable lookup pattern was verified for requests like:
- “查某个轨次所有的续费订单”
- “查某个营期轨次的二阶/续费订单”

### Verified field mapping

Do not guess the track field from business wording.

Verified locally in ClickHouse:
- `dim_camp_df`
  - has `camp_id`, `camp_name`, `camp_group_name`, `class_stage`, `class_stage_name`, `camp_sku`
  - this is the best first lookup table when the user gives a **轨次名**
- `dwd_order_handover_df`
  - has `class_camp_id`, `class_camp_name`, `camp_group_id`, `camp_group_name`, `class_stage_name`, `join_group_time`, `join_camp_time`, `union_id`
  - this is the better candidate for **交接/续费/二阶营期订单关联** than `dwd_order_flow_df`
- `dwd_order_flow_df`
  - has `camp_name`, `camp_sku`, `in_class_name`, `union_id`
  - but does **not** carry a dedicated `camp_group_name` / `营期轨次` field in this environment
- `dwd_applet_main_df`
  - has `sale_group_name`, but this is **not** the same thing as `camp_group_name`
  - do not assume it can replace 营期轨次 lookup

### Recommended workflow when the user gives a轨次名

1. First search `dim_camp_df.camp_group_name` for the exact track name.
2. If no exact match, search fuzzy candidates with `LIKE` and show the nearest existing轨次 names.
3. Only after the track is confirmed, query `dwd_order_handover_df` by `camp_group_name` / `camp_group_id` and the desired `class_stage_name`.
4. Do **not** jump straight to `dwd_order_flow_df` when the user asks for “轨次所有续费订单”, because the field mapping may be missing there.

### Verified lookup update

Verified locally in ClickHouse on 2026-04-21:
- the track `声乐二阶-20251224-赵曼院长班-BLT` **does** have an exact match
  - `dim_camp_df.camp_group_id = 845`
  - `class_stage_name = '二阶营期'`
- `dwd_order_handover_df` also contains this exact track and joins cleanly to `dwd_order_flow_df` by `flow_no`
  - observed rows: `156`
  - observed distinct users: `155`
  - `countIf(joined flow_no)` = `156`
- `drh_live_camp` in this environment still did **not** expose the expected `camp_group_name` / `camp_name` / `camp_sku` fields for this lookup, so do not rely on it first for轨次-name searches

### Practical response rule

For轨次续费订单查询, first distinguish the business definition before pulling data:

1. **交接/续费归属口径**
   - meaning: rows that were handed over / associated to this轨次
   - workflow:
     - first confirm the exact track in `dim_camp_df`
     - then use `dwd_order_handover_df` for the renewal/track membership rows
     - join `dwd_order_flow_df` on `flow_no` when the user needs payment amount / goods / pay status details

2. **订单所属营期口径**
   - meaning: orders whose `camp_id` / `camp_name` belongs to camps under this轨次
   - workflow:
     - first list target camps from `dim_camp_df`
     - then query `dwd_order_flow_df` by `camp_id` (preferred) or validated `camp_name`
     - do not use `dwd_order_handover_df` for this definition, because it can include users associated to the track while the physical order belongs to another camp/order path

3. **轨次级续费汇总口径（学员数 / 续费人数 / GMV / 课程GMV / 平均续费间隔）**
   - meaning:
     - track students and track pay time come from `dwd_order_handover_df`
     - renewal orders / GMV come from `dwd_order_flow_df`
     - join by `union_id + camp_group_name + class_stage_name`
   - proven workflow:
     - build `target_tracks` from `dim_camp_df`
     - if the filter depends on aggregated track attributes like `max(end_class_time_bi)`, compute them in `GROUP BY ... HAVING`, not in `WHERE`
     - build `handover_base` as `class_stage_name + camp_group_name + union_id`, with `min(pay_time)` as the track payment time
     - build the flow side from `dwd_order_flow_df` joined to `dim_camp_df`
     - on this ClickHouse version, do **not** rely on a separate flow CTE exposing aliased columns back into an outer join/aggregate; use an inline subquery and explicit aliases like `camp_group_name2`, `class_stage_name2`
     - because this ClickHouse version is fragile about joined-column name resolution, aggregate with fully qualified joined names such as `f.pay_amount`, `f.main_first_level`, `f.camp_group_name2`
     - `续费人数` = `uniqExactIf(union_id, renewal_gmv > 0)`
     - `课程续费人数` = `uniqExactIf(union_id, renewal_course_gmv > 0)`
     - `课程GMV` can be defined by `main_first_level = '课程'` when the user explicitly wants商品一级类目口径 rather than SKU equality
     - `平均续费间隔` should use the first qualifying course-order pay time per user via `minIf(...)`
   - critical interpretation rule:
     - this handover-based summary is **not** the same as “该轨次营期下全部课程订单 GMV”
     - it is a narrower metric: first restrict to students present in `dwd_order_handover_df`, then look for their renewal orders in `dwd_order_flow_df`
     - therefore this口径 is usually a **subset** of the camp-order scope from `dwd_order_flow_df`
   - proven debugging pattern when the user reports a mismatch between track summary GMV and prior camp-order GMV:
     1. compute camp-order scope directly from `dwd_order_flow_df` by `camp_id IN (target camps)` and `main_first_level='课程'`
     2. compute handover-based scope from `dwd_order_handover_df` + `union_id` overlap + time condition
     3. compare at `flow_no` grain, not only aggregate totals
     4. explicitly measure:
        - `A not in B`
        - `B not in A`
        - missing-row GMV and missing-user count
     5. explain whether the gap comes from:
        - handover-user-pool restriction
        - time restriction (`pay_time >= track_pay_time`)
        - or true query bugs
   - verified example on `声乐二阶-20251224-赵曼院长班-BLT`:
     - camp-order scope (`dwd_order_flow_df`, target camp only, `main_first_level='课程'`): `120` rows / `113` users / `297483` GMV
     - handover-based scope: `69` rows / `67` users / `180962` GMV
     - `A not in B = 0`, `B not in A = 51` rows / `116521` GMV
     - root cause: handover scope was a strict subset because `46` users with target-camp course orders were not present in the track's `dwd_order_handover_df` user pool

4. If the exact轨次 truly does not exist, only then ask the user to confirm the candidate track.

### Excel export validation for user-facing result files

When the user asks to send the result file:
- prefer `.xlsx` over `.csv` if they care about display/typing fidelity
- rename columns to the final Chinese headers before export
- coerce count columns to integer dtype and metric columns to numeric dtype before writing
- after writing with pandas/openpyxl, set cell number formats explicitly so Excel does not display key numeric columns as text
- re-open the workbook and verify sample cells come back as numeric Python types before claiming the file is fixed

### 钢琴月×营期阶段×来源/购买课包价格人头数

For requests like “2025-01-01 至今，表头是 月-营期阶段-来源课包价格-购买课包价格-人头数” after the user clarifies `cci3_name=钢琴` and 商品也是钢琴, use the verified mapping in `references/piano-stage-source-purchase-price-people-20260509.md`.

Key reusable points:
- order pool: `dwd_order_flow_df`, filtered by `pay_status_name='支付成功'`, `main_first_level='课程'`, `cci3_name='钢琴'`, `main_goods_sku='钢琴'`;
- 购买课包价格: `dwd_order_flow_df.total_original_price`;
- 来源课包价格: `tock_order.goods_price` joined by `flow_no = order_no`;
- 营期阶段: prefer `dwd_order_handover_df.class_stage_name`, fallback `tock_order.class_stage`, fallback `dim_camp_df.class_stage_name`;
- do **not** use `dwd_order_handover_df.package_price`; that column is absent in the verified environment;
- 人头数 is `uniqExact(union_id)` per group, so grouped sums can exceed global distinct users.

     - table 1: track students and their track pay time come from `dwd_order_handover_df`
     - table 2: renewal orders / GMV come from `dwd_order_flow_df`
     - final grain: `class_stage_name × camp_group_name`
   - proven workflow:
     - first build `target_tracks` from `dim_camp_df`
       - optional reusable filter: `end_class_time_bi >= toDateTime('YYYY-MM-DD 00:00:00')`
     - `handover_base`:
       - group by `class_stage_name, camp_group_name, union_id`
       - use `min(pay_time)` as `track_pay_time`
     - `flow_with_track`:
       - join `dwd_order_flow_df` to `dim_camp_df` by `camp_id`
       - keep `pay_status_name = '支付成功'`
       - carry `main_first_level`
     - `renewal_by_user`:
       - join by `union_id + camp_group_name + class_stage_name`
       - because ClickHouse 21.8 does not support inequality conditions inside `JOIN ON`, put the time condition in `sumIf` / `minIf` instead of `JOIN ON`
       - `renewal_gmv`: `sumIf(pay_amount, renewal_pay_time >= track_pay_time)`
       - `renewal_course_gmv`: `sumIf(pay_amount, renewal_pay_time >= track_pay_time AND main_first_level = '课程')`
       - `first_course_renewal_pay_time`: `minIf(renewal_pay_time, renewal_pay_time >= track_pay_time AND main_first_level = '课程')`
     - final aggregate:
       - `学员数 = uniqExact(union_id)` from `renewal_by_user`
       - `GMV = sum(renewal_gmv)`
       - `课程GMV = sum(renewal_course_gmv)`
       - `平均续费间隔 = avgIf(dateDiff('day', track_pay_time, first_course_renewal_pay_time), first_course_renewal_pay_time > toDateTime('1970-01-02 00:00:00'))`
   - important findings:
     - do **not** hardcode `class_stage_name = '二阶营期'` unless the user explicitly asks for it
     - for this metric, “课程GMV” should be interpreted as `main_first_level = '课程'`, not `main_goods_sku = camp_sku`
     - if the same `camp_group_name` can exist across stages, keep `class_stage_name` in both the target-track key and the join key to avoid cross-stage mixing

4. If the exact轨次 truly does not exist, only then ask the user to confirm the candidate track.

## 钢琴 SKU teach_help=1 开课前加微率

A reusable mapping and query pattern was verified for requests like:
- 近一个月的钢琴 SKU 的 `teach_help=1` 开课前加微率

### Verified field mapping

Use `dwd_applet_main_df` as the primary source.

Verified columns on `dwd_applet_main_df`:
- `camp_sku` — 营期sku
- `teach_help_name` — 教辅
- `start_class_time` — 营期开课日期
- `add_time` — 加微时间
- `union_id` — 用户去重键

Important finding:
- `dwd_applet_main_df` does **not** carry `teach_help_code`
- for this metric, `teach_help=1` should be mapped via channel-dimension verification to:
  - `teach_help_name = '图书'`

The code mapping was verified from `tock_channel_id_belong`:
- `1 -> 图书`
- `2 -> 盒子`
- `3 -> 无`
- `4 -> 音响`
- `5 -> 麦克风`
- `6 -> 瑜伽垫`
- `7 -> 口琴`

### Recommended metric definition

Interpret “开课前加微率” as:
- denominator: rows matching the requested SKU / teach_help / recent start-class window
- numerator: rows where `add_time` is valid and `add_time < start_class_time`

Use a validity guard for empty/default timestamps:
- `add_time > toDateTime('1970-01-02 00:00:00')`

### Working ClickHouse SQL

```sql
SELECT
    count() AS total_rows,
    countIf(add_time > toDateTime('1970-01-02 00:00:00')
            AND add_time < start_class_time) AS before_add_rows,
    round(before_add_rows / total_rows, 4) AS before_add_rate,
    uniqExact(union_id) AS total_users,
    uniqExactIf(
        union_id,
        add_time > toDateTime('1970-01-02 00:00:00')
        AND add_time < start_class_time
    ) AS before_add_users,
    round(before_add_users / total_users, 4) AS before_add_user_rate
FROM dwd_applet_main_df
WHERE camp_sku = '钢琴'
  AND teach_help_name = '图书'
  AND start_class_time >= today() - 30
  AND start_class_time < today() + 1
```

### Verified result at time of discovery

For the last-30-day window in this environment:
- row-level sample size: `28556`
- row-level before-class add count: `22878`
- row-level before-class add rate: `0.8012`
- distinct users: `24571`
- distinct before-class add users: `22678`
- distinct-user before-class add rate: `0.9230`

### Daily trend SQL

```sql
SELECT
    toDate(start_class_time) AS start_day,
    count() AS total_rows,
    countIf(add_time > toDateTime('1970-01-02 00:00:00')
            AND add_time < start_class_time) AS before_add_rows,
    round(before_add_rows / total_rows, 4) AS before_add_rate,
    uniqExact(union_id) AS total_users,
    uniqExactIf(
        union_id,
        add_time > toDateTime('1970-01-02 00:00:00')
        AND add_time < start_class_time
    ) AS before_add_users,
    round(before_add_users / total_users, 4) AS before_add_user_rate
FROM dwd_applet_main_df
WHERE camp_sku = '钢琴'
  AND teach_help_name = '图书'
  AND start_class_time >= today() - 30
  AND start_class_time < today() + 1
GROUP BY start_day
ORDER BY start_day DESC
```

### Pitfall discovered while exporting

Avoid selecting constant string aliases with the same names as filtered columns when building export DataFrames, e.g.:
- `SELECT '图书' AS teach_help_name ...`

In one run this led to a misleading exported summary row count (`389651`) while the real query result was `28556`.
Use distinct output aliases such as:
- `target_sku`
- `target_teach_help`

## Daily cumulative cohort refund-rate comparison for handover monitoring

Detailed session-specific reference for the 声乐-first handover/refund validation pattern is available at `references/vocal-handover-refund-effect-analysis.md`. Use it when the user asks whether 盯交接/交接效率 reduced refund rates, especially if the project landed first in 声乐.

Session-specific details for the corrected 声乐前端 natural-day chart, 2026-03/04 attribution, and boss-facing Feishu report are stored in `references/vocal-frontend-cohort-refund-chart-2026-05.md`. Use that reference when rebuilding the chart/report or explaining why 3月/4月当月退费率升高.

Critical corrections learned from that session:
- To align with the handover optimization report, use `cci3_name='声乐'` and monthly natural day `1-31`, not `main_goods_sku='声乐'` or D0-D90.
- For same-day observed natural-day charts, do **not** group `dwd_order_flow_df.refund_amount` by `pay_time` day; that pulls future refunds back to the pay day and can make day 1 look falsely high. Use `tock_dwd_order_refund_df.refund_time` for the numerator.
- Metric should be: cumulative same-month refund GMV through natural day N / cumulative paid GMV through natural day N.
- Chart presentation preferred by the user: smooth curves, no per-point markers, one shared legend, exact predicates/formula in the footnote and Excel SQL sheet.
- Business interpretation found: 2026-03 starts a high-refund regime; 2026-04 is lower than March but still historically high. Say “高位回落，仍需治理,” not “4 月退费低.”
- 2026-03 abnormality concentrated in `BD1-KOL × 李聿为/汪国炳 × 院长班/1880系统课 × 高价全款 × specific营期`; 2026-04 main risk bucket was `有交接未入群`, while completed `已入群/入班` was much lower.

### Verified source and default scope
For a same-month cohort handover-efficiency analysis with front-end board splits and handover dimensions, see `references/refund-handover-effect-same-month-cohort.md`.

For the May 2026 声乐前端 cohort 退费率 chart correction — including `cci3_name='声乐'` vs `main_goods_sku='声乐'`, natural-month day 1-31 vs D0-D90 elapsed-day cohort, and the user's preferred smooth/no-marker/shared-legend chart style — see `references/vocal-frontend-cohort-refund-chart-2026-05.md`.

For a “类似甘特图”的支付月 × 后续退款月 cohort 退费释放热力图, see `references/vocal-frontend-month-cohort-refund-heatmap-2026-05.md`. Use `tock_dwd_order_refund_df.refund_time` for refund timing, show `M0/M1/...` month offsets, and render future unobserved months as gray/blank rather than 0.

### Verified source and default scope

For this specific monitoring cut, a workable source is `dwd_order_flow_df` directly rather than joining the refund detail table.

Verified locally:
- `dwd_order_flow_df` contains both `pay_amount` and `refund_amount`
- `refund_amount` can be used to build the order-cohort cumulative refund-rate trend at daily cumulative grain
- `pay_status_name='支付成功'` was the only observed status in the filtered pool during validation, but the original handover-style filter set did not require an extra pay-status predicate once `pay_type_name` and the course/order conditions were applied

The verified default order pool used successfully was:
- `main_first_level = '课程'`
- `pay_type_name IN ('全款','尾款')`
- `total_original_price >= 1880`
- `main_goods_sku IN ('声乐','钢琴')`

This mirrors the practical handover-monitoring scope more closely than a full refund-diagnosis scope.

### Metric definition

There are two different “逐日 cohort 退费率”口径. Do not mix them.

#### A. 同日观察 / 月内自然日口径（用于交接优化对比）

Use this when the user wants to compare with the handover-optimization conclusion such as `3.29% -> 2.90%` or says the横轴 is `月内自然日 1-31`.

For each payment month and day-of-month `d`:
- denominator: paid GMV for orders paid from day 1 through day `d` in that payment month
- numerator: refund GMV that **actually occurred within the same payment month** from day 1 through day `d`
- cumulative cohort refund rate:
  - `同日观察累计cohort退费率 = 同月截至d日发生退款GMV / 截至d日支付GMV`

Important source split:
- denominator comes from `dwd_order_flow_df.pay_amount` by `pay_time`
- numerator must come from `tock_dwd_order_refund_df.refund_amount` by `refund_time`
- filter refund rows to the same payment month:
  - `refund_time >= toStartOfMonth(pay_time)`
  - `refund_time < addMonths(toStartOfMonth(pay_time), 1)`

Do **not** use `dwd_order_flow_df.refund_amount` for this chart, because it is the order's current accumulated refund amount. If used by pay day, a refund that occurred later (e.g. 4/9 or 5/6) is attributed back to the original pay day and can make day 1 appear artificially high.

Example interpretation:
- 2 号累计退费率 = 1-2 号支付订单的累计 GMV as denominator, and same payment month 1-2 号 actually occurred refunds as numerator.

Verified alignment for `cci3_name='声乐'`, `new_front_end_name LIKE '%前端%'`:
- 声乐前端全部订单: 2026-03 `3.29%`, 2026-04 `2.90%`
- 声乐前端课程1880+全款/尾款: 2026-03 `3.12%`, 2026-04 `2.44%`

#### B. 当前累计退款按支付日归因口径（慎用）

If using `dwd_order_flow_df.refund_amount` and grouping by `toDayOfMonth(pay_time)`, the meaning is:
- numerator: orders paid through day `d` and their **current accumulated** refund amount
- denominator: orders paid through day `d` and their pay amount

This answers “这些支付日的订单截至现在累计退了多少”, not “同日观察到第 d 天退了多少”. Label it explicitly as current-accumulated-by-pay-day if used.

### D0-D90 payment-age cohort view

When the user asks to “时间拉长一点” / “展示至多90天”, do **not** merely extend the day-of-month chart. Switch to a payment-age cohort curve:

- x-axis: `dateDiff('day', toDate(pay_time), toDate(refund_time))`, shown as `D0-D90`
- denominator: fixed total GMV for that payment-month cohort
- numerator at D<N>: cumulative refund GMV whose refund happened within N days after payment
- metric:
  - `D0-DN cohort退费率 = 支付后N天内累计退款GMV / 该支付月cohort GMV`
- denominator source: `dwd_order_flow_df`
- refund timing source: `tock_dwd_order_refund_df` using `refund_time`

Visualization preferences verified for Zheng on this chart class:
- use smooth curves for visual comparison
- keep only one shared legend across subplots
- remove per-day point markers when plotting D0-D90; they clutter the chart
- keep exact predicates in the footer / SQL sheet

A session-specific reference with working predicates and plotting notes is available at `references/vocal-frontend-cohort-refund-d90-chart.md`.

### Recommended benchmark construction

When the user asks for:
- current month vs prior month
- current month vs past 3-month average
- current month vs past 6-month average

use this structure:

1. Aggregate by `pay_month + day_of_month`
2. Build cumulative GMV / refund within each month using window sums
3. Keep one row per `pay_month, day_of_month`
4. For benchmark averages, average the **monthly cumulative refund rates at the same day_of_month**
   - this is a simple month-level average unless the user explicitly asks for GMV-weighted averaging

### Post-event window check

If the user phrases the question around an intervention date like “4/2 开始关注交接情况之后”, do two checks:

1. Main chart/table:
   - still provide the full current-month daily cumulative series from day 1 onward
2. Intervention-window summary:
   - separately compute the comparison over the aligned day-of-month window, e.g. `day_of_month BETWEEN 2 AND current_latest_day`
   - report the current-month window refund rate and compare it with prior-month / 3-month / 6-month baselines for the same aligned day window

This avoids over-claiming based only on full-month cumulative values when the intervention started mid-month.

### Exact front-end filter vs broad front-end filter

A practical ambiguity appeared in real use:
- sometimes the user wants all front-end traffic
- sometimes they mean only the exact bucket `new_front_end_name = '大前端'`

Do not silently reuse the broad filter when the user gives an exact front-end label.

Use:
- broad front-end scope:
  - `new_front_end_name LIKE '%前端%'`
- exact 大前端 scope:
  - `new_front_end_name = '大前端'`

When the user says things like:
- “只看声乐SKU，new_front_end大前端的订单”

interpret that as the exact-match filter above, not the broader `%前端%` scope.

### Product filter field ambiguity: `main_goods_sku` vs `cci3_name`

A reusable pitfall was verified for the daily cumulative cohort refund-rate chart/doc workflow:
- the same business phrase “声乐” may be implemented with either:
  - `main_goods_sku = '声乐'`
  - `cci3_name = '声乐'`
- these are **not interchangeable** and can materially change both the chart and the summary metrics.

Verified locally on the exact scope:
- `new_front_end_name = '大前端'`
- no `total_original_price` restriction
- no `pay_type_name` restriction
- comparison window: `2026-03` vs `2026-04`

Observed day-20 cumulative cohort refund rates:
- `main_goods_sku = '声乐'`
  - 2026-04 day 20: `1.73%`
  - vs 2026-03: `-2.59pp`
- `cci3_name = '声乐'`
  - 2026-04 day 20: `2.18%`
  - vs 2026-03: `-2.64pp`

Practical rule:
- if the user says “用 `cci3_name='声乐'` 跑一版”， treat it as a **one-off run instruction for that output**, not a permanent default override
- if you are rebuilding an existing chart/doc, keep every other condition unchanged and swap only the target product predicate unless the user explicitly asks to change more
- in the final delivered file, write the exact predicate into the summary sheet / caption so the metric definition is auditable later
- when aligning charts with the handover-optimization report wording for 声乐前端, use `cci3_name='声乐'` and a **月内自然日 1-31** x-axis by default; do not substitute a D0-D90 elapsed-day cohort chart unless the user asks for “支付后第 N 天 / D0-D90” explicitly

### Splitting the daily cumulative cohort trend by `main_first_level`

A reusable follow-up pattern was verified for the exact scope:
- `main_goods_sku = '声乐'`
- `new_front_end_name = '大前端'`
- `pay_type_name IN ('全款','尾款')`
- `total_original_price >= 1880`

If the user asks to “按商品类型看趋势” and explicitly clarifies they mean `main_first_level`, then:

1. aggregate daily GMV / refund by:
   - `pay_month`
   - `day_of_month`
   - `main_first_level`
2. compute cumulative GMV / refund within each month and each `main_first_level`
3. compare current April vs March / past 3-month avg / past 6-month avg at the same day-of-month
4. export:
   - one sheet with full daily rows
   - one summary sheet with latest-day comparison and counts of post-4/2 days below benchmark
5. draw a 2x2 trend chart with:
   - `整体`
   - each observed `main_first_level`

Practical caution from this environment:
- for this exact scope, volume was overwhelmingly in `main_first_level = '课程'`
- `权益` / `电商` had very small sample sizes
- so business interpretation should focus on `课程` / `整体`, and explicitly mark the minor categories as low-sample reference only

### Tooling quirk seen while generating charts locally

A real Hermes terminal quirk was observed:
- some foreground `terminal()` calls that start with `eval "$(conda shell.bash hook)" && ...` were falsely rejected as if the command used shell `&` backgrounding
- in longer inline Python commands, even replacing `&&` with `;` could still trigger the same false positive

Reliable fallback order:

1. First try semicolon chaining:

```bash
eval "$(conda shell.bash hook)"; conda activate hermes-sql; python ...
```

2. If the false `&`-backgrounding error still appears, stop fighting the shell wrapper and use the environment's absolute interpreter path directly, e.g.:

```bash
/opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python /path/to/script.py
```

3. For long chart/export jobs, prefer writing the Python to a temporary or Hermes-managed `.py` file and then executing that file with the absolute interpreter path instead of embedding a very long heredoc inside `terminal()`.

Practical rule:
- for short one-off checks, `; conda activate hermes-sql; python - <<'PY' ...` is fine
- for longer plotting/export pipelines, write a script file and call the absolute `hermes-sql` Python binary

This avoids repeated false failures from the terminal wrapper and is the most stable path for pandas/matplotlib export jobs.

### Practical conclusion rule

A strong business statement like “退费率下降” is supported when both are true:
- the latest available current-month cumulative rate is below the selected benchmarks
- and the current-month cumulative curve stays below those benchmarks for nearly all or all checked days after the intervention start

Still explicitly label causality carefully:
- say the result is **consistent with** the intervention helping
- do **not** claim the intervention alone caused the decline without a stricter causal design

### Export expectations for this pattern

Save at least:
- a CSV/XLSX with one row per `day_of_month`
- columns for current month, prior month, 3-month average, 6-month average, and point differences in pct points
- a compact JSON or textual summary with:
  - latest day values
  - mean post-event difference vs each benchmark
  - count of post-event days where current month stayed below each benchmark

## 析出渠道 × SKU × D0-D14 日GMV比例 / 日预算GMV拆分

Use this pattern when the user references the legacy `tock_order` SQL that buckets payment dates into `D0`-`D14`, asks for “析出渠道（小程序/企微）对应各个 SKU 的 D0-D14”, or wants to use D-bucket GMV proportions to split a monthly budget into daily budget GMV.

Important naming correction:
- If the numerator is `D日GMV` and the denominator is `该析出渠道 × SKU 总GMV`, call the metric **日GMV比例** / **GMV比例**, not “转化率”.
- “转化率” should be reserved for count/funnel conversions with a real denominator such as leads/orders/users, not GMV distribution shares.

### Verified source and fields

A verified ClickHouse source is `tock_order`.

Relevant columns verified locally:
- `camp_sku` — SKU / 营期 SKU dimension used by the legacy SQL
- `last_time` — recent-window filter in the legacy SQL
- `class_time` — class date used for D-bucket anchor
- `pay_time` — payment date used for D-bucket
- `pay_price` — GMV numerator for each D bucket
- `first_level`, `front_end`, `camp_date_type` — business filters
- `market_belong` — best observed field for 析出渠道 split

Observed `market_belong` mappings for this metric:
- `market_belong = '析出-小程序'` -> `小程序`
- `market_belong = '析出-企微&公众号'` -> `企微`

Important ambiguity:
- Do not silently replace this with `pay_source = '企业微信收款'`; that is a payment-source dimension and gives a different口径.
- If the user says “企微” but seems to mean payment collection channel, explicitly call out the distinction.

### Metric definition from `tock_order`

Default scope matching the provided legacy SQL:
- `last_time >= today() - 180`
- `last_time <= today()`
- `first_level = '课程'`
- `front_end = '前端'`
- `camp_date_type = '大盘'`
- `market_belong IN ('析出-小程序', '析出-企微&公众号')`

D-bucket logic:
- `toDate(pay_time) < toDate(class_time)` -> `D0`
- `toDate(pay_time) = toDate(class_time)` -> `D1`
- `toDate(pay_time) = addDays(toDate(class_time), 1)` -> `D2`
- ...
- `toDate(pay_time) = addDays(toDate(class_time), 12)` -> `D13`
- everything else -> `D14`

GMV-ratio definition:
- `日GMV比例 = D日GMV / 该析出渠道 × SKU 总GMV`
- denominator must be grouped by both `析出渠道` and `camp_sku`, not SKU alone.
- If exporting to Excel, use sheet/column names like `日GMV比例透视`, `日GMV比例`, `GMV透视`, and `比例校验` instead of `转化率透视` / `转化率`.

### `dwd_order_flow_df` version of the same distribution

If the user asks to “换成 dwd_order_flow_df 来算”, use `dwd_order_flow_df` as the order-flow source and join `dim_camp_df` for class-date and big-market filters.

Verified mapping:
- order source: `dwd_order_flow_df f`
- camp/date dimension: `dim_camp_df d ON f.camp_id = d.camp_id`
- time filter: `f.pay_time >= <start>` and `< <end>`
- course filter: `f.main_first_level = '课程'`
- frontend filter: usually `f.new_front_end_name LIKE '%前端%'`, unless the user asks for exact `大前端`
- big-market filter: `d.camp_date_type_name = '大盘'`
- paid filter: `f.pay_status_name = '支付成功'`
- 析出渠道 mapping:
  - `f.f_market_belong = '析出-小程序'` -> `小程序`
  - `f.f_market_belong = '析出-企微&公众号'` -> `企微`
- SKU: `f.camp_sku`
- GMV: `f.pay_amount`
- D-bucket anchor: compare `toDate(f.pay_time)` to `toDate(d.class_time)`

Useful sanity checks:
- Before using this source, probe `f_market_belong` / `o_market_belong` distribution because these can differ.
- `dim_camp_df` uses `camp_date_type_name`, not `camp_date_type`.
- Keep SQL aliases ASCII for `clickhouse_driver`; rename to Chinese in pandas before exporting.
- For user-facing files, include order counts as context but label the main metric as `日GMV比例`.

### Daily budget GMV splitting with D-bucket ratios

When the user asks to compute something like “5月1日-5月31日日预算GMV” in this context, interpret it as: use D-bucket historical GMV ratios to split a monthly budget GMV into daily budget GMV, **not** as another rate table.

Required inputs:
1. Monthly budget GMV by the same grain as the ratio, usually `析出渠道 × SKU × 月份`.
2. A D-bucket ratio table, usually from the latest 180-day history: `析出渠道 × SKU × D0-D14 -> 日GMV比例`.
3. A way to map each calendar date in the target month to D0-D14 for each relevant camp/class-date. If only a monthly budget exists without camp/class-date schedule, clarify the allocation assumption before calculating.

Verified local table availability caveat observed in this environment:
- `daily_gmv_budget` contained daily budget rows through 2026-04 but had no 2026-05 rows at time of check.
- `tock_budget` contained 2025-05 monthly budget rows but no 2026-05 rows at time of check.
- `tock_budget_district_rate` only has `sku/day_num/rate`, no monthly budget amount or channel split.

Therefore, if the user requests a future month like 2026-05 and no budget source exists locally, do not fabricate daily budget GMV. Ask for the 2026-05 monthly budget source or confirm using a historical/simulated budget source.

Formula once inputs are available:
```text
日预算GMV = 月预算GMV(析出渠道, SKU) × 日GMV比例(析出渠道, SKU, D日)
```

If multiple camps/class dates exist in the month, allocate at the matching camp-date/D-bucket grain first, then aggregate to calendar dates; do not simply map May 1 -> D1 unless the campaign schedule actually supports that mapping.

### Working ClickHouse SQL shape

Keep aliases ASCII in the ClickHouse query when using `clickhouse_driver`, then rename to Chinese in pandas/export if needed.

```sql
WITH base AS (
    SELECT
        multiIf(
            market_belong = '析出-小程序', '小程序',
            market_belong = '析出-企微&公众号', '企微',
            NULL
        ) AS sy_channel,
        camp_sku,
        multiIf(
            toDate(pay_time) < toDate(class_time), 'D0',
            toDate(pay_time) = toDate(class_time), 'D1',
            toDate(pay_time) = addDays(toDate(class_time), 1), 'D2',
            toDate(pay_time) = addDays(toDate(class_time), 2), 'D3',
            toDate(pay_time) = addDays(toDate(class_time), 3), 'D4',
            toDate(pay_time) = addDays(toDate(class_time), 4), 'D5',
            toDate(pay_time) = addDays(toDate(class_time), 5), 'D6',
            toDate(pay_time) = addDays(toDate(class_time), 6), 'D7',
            toDate(pay_time) = addDays(toDate(class_time), 7), 'D8',
            toDate(pay_time) = addDays(toDate(class_time), 8), 'D9',
            toDate(pay_time) = addDays(toDate(class_time), 9), 'D10',
            toDate(pay_time) = addDays(toDate(class_time), 10), 'D11',
            toDate(pay_time) = addDays(toDate(class_time), 11), 'D12',
            toDate(pay_time) = addDays(toDate(class_time), 12), 'D13',
            'D14'
        ) AS day_num,
        pay_price
    FROM tock_order
    WHERE last_time >= today() - 180
      AND last_time <= today()
      AND first_level = '课程'
      AND front_end = '前端'
      AND camp_date_type = '大盘'
      AND market_belong IN ('析出-小程序', '析出-企微&公众号')
      AND camp_sku != ''
), agg AS (
    SELECT sy_channel, camp_sku, day_num, sum(pay_price) AS day_gmv
    FROM base
    GROUP BY sy_channel, camp_sku, day_num
), total AS (
    SELECT sy_channel, camp_sku, sum(day_gmv) AS total_gmv
    FROM agg
    GROUP BY sy_channel, camp_sku
)
SELECT
    agg.sy_channel AS sy_channel,
    agg.camp_sku AS sku,
    agg.day_num AS day_num,
    round(agg.day_gmv, 2) AS day_gmv,
    round(total.total_gmv, 2) AS total_gmv,
    round(agg.day_gmv / total.total_gmv, 6) AS rate
FROM agg
INNER JOIN total
    ON agg.sy_channel = total.sy_channel
   AND agg.camp_sku = total.camp_sku
ORDER BY sy_channel, sku, toUInt8(replaceAll(day_num, 'D', ''))
```

### Export pattern

For user-facing delivery:
- export `.xlsx` under `~/.hermes/output/query_results/`
- include at least:
  - `转化率透视`
  - `GMV透视`
  - `明细长表`
  - `SQL`
- format rate cells as percentages and GMV cells as numeric values.
- reopen the workbook with `openpyxl` and verify sheet names, row counts, and numeric cell types before claiming completion.

## Legacy `drh_order` dashboard SQL vs `dwd_order_flow_df` GMV reconciliation

Use this pattern when a legacy dashboard/report SQL based on `drh_order` disagrees with a `dwd_order_flow_df` GMV check.

- First identify the SKU field/route in each query:
  - legacy `drh_order` dashboard SQL may map SKU through `drh_live_camp.category -> drh_business_line.name`
  - `dwd_order_flow_df` checks may use `camp_sku`, `main_goods_sku`, or `cci3_name`; these are not interchangeable
- Check whether the comparison includes all `main_first_level` values or only `main_first_level = '课程'`.
- Decompose the legacy SQL one join at a time and measure `count`, distinct user/order key, and GMV after each join.
- Treat inner joins to attribution/dimension tables as likely filters, not harmless enrichments. In particular, `drh_kk_group_team` on `drh_order.emp_num = emp_id` can remove valid paid orders whose employee is missing from the active team table.
- If the metric should be total GMV, prefer `LEFT JOIN` for team/channel enrichment and only apply team filters when the user explicitly selects a team.
- Session reference with a worked calligraphy/书法 April reconciliation: `references/drh-order-vs-dwd-order-flow-gmv-reconciliation.md`.
- Follow-up reference after the user changed `drh_kk_group_team` to `LEFT JOIN`: `references/drh-order-current-1sql-left-join-followup.md`. In that current SQL shape, the remaining `1,859` April `书法` GMV gap came from `drh_channel_emp` still being an `INNER JOIN`; `drh_goods` and `tock_channel_id_belong` no longer reduced the GMV.

## SQL mismatch debugging pattern: source SQL vs `dwd_order_flow_df`

Use this pattern when the user asks why an existing SQL result differs from a `dwd_order_flow_df` control total.

1. Read the actual SQL file first and identify the **fact table, metric expression, time field, SKU field, frontend filter, and every `INNER JOIN`** before explaining.
2. Reproduce the user's control total in `dwd_order_flow_df` and split by important口径 fields such as:
   - `main_first_level`
   - `main_goods_sku`
   - `camp_sku`
   - `new_front_end_name`
3. Rebuild the existing SQL's metric source step-by-step, adding one join/filter at a time and recording row count / user count / GMV after each step.
4. Attribute differences by the exact join/filter that drops rows, not by broad guesses.
5. For dashboard SQL with optional filters, do not let dimension joins filter facts by default. Preferred pattern:
   - default dimension enrichment: `LEFT JOIN`
   - optional filter behavior: `[[AND fact_key IN (SELECT key FROM dim WHERE ... {{filter}} ... )]]`
6. If a dimension condition is only relevant to a secondary metric, keep it inside conditional aggregation instead of filtering the whole GMV fact set. Example: `goods_sort = 1` should not filter total GMV if the control total includes all product categories; use it inside 商品成本 / 正价课学员数 calculations only.

Verified example from 2026-04 calligraphy GMV investigation:
- `/Users/zheng/Desktop/1.sql` used `drh_order` and mapped SKU by `drh_order.camp_id -> drh_live_camp.category -> drh_business_line.name = '书法'`.
- `dwd_order_flow_df` control total for 2026-04 frontend `camp_sku='书法'` was `291323`, split as `课程 268880` + `电商 22443`.
- Existing SQL narrowed this through inner joins/filters to `182920`; main drops were `drh_kk_group_team` (`84500`), `drh_goods goods_sort=1` (`22044`), and `drh_channel_emp` (`1859`).
- `tock_channel_id_belong` did not drop rows in that sample but is still structurally risky as an unconditional `INNER JOIN`.

### 营期阶段 × 来源课包价格 × 购买课包价格人头数

For reports shaped as `月 / 营期阶段 / 来源课包价格 / 购买课包价格 / 人头数`, do not infer 来源课包价格 from the same current order. The user's corrected definition is: current order's previous-stage order price for the same `union_id`; `销转营期` source price is blank; if there are multiple previous-stage orders, take the latest one before the current order's `pay_time`. See `references/stage-source-package-price-by-previous-stage.md` for the verified ClickHouse pattern, stage mapping, and pitfalls.

### 钢琴二/三/四阶交接营期转化统计

For 钢琴二/三/四阶 conversion reports where the user says “先从交接表获取已开课营期和交接学员数，再统计这些学员在对应营期内的订单数”, use the handover-camp cohort pattern in `references/piano-stage-conversion-by-handover-camp-20260509.md`.

Key rules:
- denominator comes from `dwd_order_handover_df` at `class_camp_id × union_id` grain, not from order table totals;
- source package price is the handover source `flow_no`'s `dwd_order_flow_df.total_original_price`;
- target conversion is a paid course order for the same `union_id` and same target `class_camp_id`; do not require target order `pay_time >= start_class_time` because high-stage renewals often pay before opening;
- use stage-specific maturity windows to exclude unfinished cohorts: 二阶 130 days, 三阶 180 days, 四阶 300 days after `dim_camp_df.start_class_time`.

### 钢琴二/三/四阶交接营期转化率

For reports that should start from `dwd_order_handover_df` rather than the order table — “先从交接表获取 24 年至今已开课营期和交接学员数，再统计这些学员在对应营期内的订单数/转化率” — use `references/piano-stage-conversion-by-handover-camp-20260509.md`.

Key rule:
- denominator comes from `dwd_order_handover_df.class_camp_id × union_id`;
- source package price comes from `handover.flow_no -> dwd_order_flow_df.total_original_price`;
- target conversion is an order for the same `union_id` and same `class_camp_id` (`dwd_order_flow_df.camp_id = class_camp_id`), not necessarily after the class start date;
- exclude immature camps explicitly, e.g. start date less than 90 days ago as a first-pass threshold, or stricter stage-specific thresholds if the user wants conservative reporting.


Preferred workflow:

1. Locate the source script or managed SQL under `~/.hermes/python/projects/` or `~/.hermes/sql/` using `search_files`.
2. If the SQL is embedded in Python string constants, extract the exact SQL constants from the script rather than reconstructing from memory.
3. Replace script placeholders such as `{START}` / `{END}` with the concrete values used in that run when they are defined in the same script.
4. Write standalone `.sql` files under `~/.hermes/output/query_results/<descriptive-folder>/`.
5. Add a short `README.txt` with source script path, time window, and target report/link if relevant.
6. Zip the folder, verify the zip contents with Python `zipfile` or `unzip -l`, then return `MEDIA:/absolute/path.zip`.
7. Keep the reply short: list included files and source path only. Do not repeat口径来源 or business explanation unless the user asks.

Session example: for historical `首款订单 / 休学冻课` Feishu workbook, the source SQL was embedded in `/Users/zheng/.hermes/python/projects/first-payment-only/refresh_feishu_with_class_attendance.py` as `FIRST_WITH_CLASS_SQL` and `REST_FREEZE_SQL`; exporting those constants into two `.sql` files plus a README and zip was the right deliverable.


## Stage-to-stage source package price for renewal-stage order summaries

Use this pattern when the user asks for a table like `月-营期阶段-来源课包价格-购买课包价格-人头数`, especially after providing a base SQL grouped by `dim_camp_df.class_stage_name` and `dwd_order_flow_df.total_original_price`.

### Correct interpretation

- `购买课包价格` = the current order's `dwd_order_flow_df.total_original_price`.
- `来源课包价格` is **not** a same-order field from `tock_order.goods_price` and should not be joined by `flow_no = order_no`.
- `来源课包价格` = the previous-stage order's product price for the same user, selected from the user's earlier orders.
- For `销转营期`, source package price should be blank.
- For `二阶营期`, source stage is `销转营期`.
- For `三阶营期`, source stage is `二阶营期`; for later stages use the immediately previous stage.
- If the previous stage has multiple qualifying orders, use the **last previous-stage order before the current order pay_time**.

Verified stage coding in `dim_camp_df`:
- `class_stage = 0` -> `销转营期`
- `class_stage = 2` -> `二阶营期`
- `class_stage = 3` -> `三阶营期`
- `class_stage = 4` -> `四阶营期`
- `class_stage = 5` -> `五阶营期`

So the source-stage expression is:

```sql
if(o.class_stage = 2, 0, o.class_stage - 1)
```

### Filter ownership

Keep the user's current-order filters exactly on the `current_orders` CTE. Example from the correction session:

```sql
a1.dt >= '2025-01-01'
AND a1.cci3_name = '钢琴'
AND a1.main_goods_sku = '钢琴'
AND a1.pay_type_name IN ('全款','尾款')
AND a1.main_first_level = '课程'
```

For `source_orders`, do **not** automatically copy every current-order filter. The user explicitly corrected that `来源课包` does not need `cci3_name = '钢琴'`. In that case the source CTE kept:

```sql
a1.pay_status_name = '支付成功'
AND a1.main_goods_sku = '钢琴'
AND a1.pay_type_name IN ('全款','尾款')
AND a1.main_first_level = '课程'
```

If many source prices are blank, diagnose which source filter is excluding the prior-stage order. Common blockers are `main_goods_sku`, `pay_type_name IN ('全款','尾款')`, `main_first_level='课程'`, missing prior-stage rows, or prior-stage `pay_time >= current pay_time`.

### ClickHouse 21.8-safe SQL shape

ClickHouse 21.8 does not support inequalities in `JOIN ON`, so do not write `src.pay_time < o.pay_time` inside the join condition. Join only by user, then put the time/stage condition inside `argMaxIf`:

```sql
WITH
current_orders AS (...),
source_orders AS (...),
enriched AS (
    SELECT
        o.pay_month,
        o.class_stage_name,
        if(
            o.class_stage_name = '销转营期',
            NULL,
            argMaxIf(
                src.purchase_price,
                src.pay_time,
                src.class_stage = if(o.class_stage = 2, 0, o.class_stage - 1)
                AND src.pay_time < o.pay_time
            )
        ) AS source_price,
        o.purchase_price,
        o.union_id
    FROM current_orders o
    LEFT JOIN source_orders src ON o.union_id = src.union_id
    GROUP BY o.pay_month, o.class_stage_name, o.class_stage, o.pay_time, o.purchase_price, o.union_id
)
SELECT
    pay_month AS month,
    class_stage_name AS stage,
    if(isNull(source_price) OR source_price <= 0, '', toString(toInt64(round(source_price)))) AS source_package_price,
    toString(toInt64(round(purchase_price))) AS purchase_package_price,
    uniqExact(union_id) AS people_cnt
FROM enriched
GROUP BY month, stage, source_package_price, purchase_package_price
```

### Pitfall from correction

If the user asks “为什么来源课包为空 / 为什么被过滤了”, separate:
- intentional blank source for `销转营期`; from
- non-sale stages with no matched prior-stage order under the current `source_orders` filters.

Do not call the same-order `tock_order.goods_price` a source package price.


- include the table link and current headline numbers;
- mention sheet names only if useful for navigation;
- omit口径来源、source table names、join logic、SQL details, and long explanations of derived fields;
- convert decimal rates to readable percentages in prose unless the user is asking for spreadsheet cell values.

This is distinct from technical SQL/report documentation, where exact口径 and predicates still must be preserved for auditability.

## Auditing Hermes cashflow / profit sync tasks

When the user asks which scripts are currently used by the Hermes cashflow / profit sync jobs, do not guess from memory. Use this audit order:

1. List cron jobs with `cronjob(action='list')`.
2. Read `~/.hermes/cron/jobs.json` to get the exact command behind each relevant job.
3. Resolve entry scripts under `~/.hermes/python/projects/`.
4. Read the entry script and any directly imported / subprocess-called child scripts.
5. Read the matching config files under `~/.hermes/config/projects/` to identify concrete SQL files, sheet targets, and task names.

Verified current patterns in this environment:
- `cashflow_daily_feishu`, `cashflow_monthly_sheet`, `cashflow_sheet_date_marker`
  - entry: `~/.hermes/python/projects/cashflow-core/run_task.py`
  - task implementations under `automatic/tasks/`
- cost-detail sync jobs
  - entry: `~/.hermes/python/projects/cost-detail/run_daily_job.py`
  - child scripts: `query_cost_detail.py` and `write_feishu_sheet.py`
- profit / GMV related sync jobs can also live outside cashflow-core, e.g.:
  - `~/.hermes/python/projects/gmv-daily/vocal_gmv_refund_daily/run_job.py`
  - `~/.hermes/python/projects/gmv-monthly-update/run_job.py`

Practical rule:
- distinguish the cron entry script from the downstream child scripts and from the SQL files.
- when reporting to the user, prefer a table like:
  - job name
  - cron entry command
  - actual Python entry script
  - child scripts
  - SQL / config file

## Profit-table gap analysis against cash-account result tables

A reusable pattern was verified for questions like:
- can `dws_pl_cost_md_pdf` support a result table similar to `dws_cash_account_md_pdf`?
- what must be added while keeping the profit-calculation口径?

### Verified table shapes in ODPS KB
- `dws_cash_account_md_pdf`
  - comment: `现金账户数据表`
  - 57 columns
- `dws_pl_cost_md_pdf`
  - comment: `经营利润_成本表`
  - 8 columns: `p_date, org_name1, org_name2, cci2_name, cci3_name, studio_lv2, indicators_name, cost_amount`
- `dwd_finance_cash_cost_md_pdf`
  - comment: `净现金成本明细表`
  - contains operational fields that are lost in the profit cost aggregate, including:
    - `from_table`
    - `expensetypecategory`
    - `expensetypename`
    - `subject`
    - `sku1`, `sku2`
    - `prepay_type1`, `prepay_type2`
    - `realpaymentdate`, `createddate`
    - `paymentlinestatusdesc`
    - `sy_type`
- `dwd_order_receipt_refund_md_pdf`
  - comment: `订单收款退款流水表`
  - already contains the revenue-side fields needed to rebuild profit GMV / refund metrics

### Key conclusion
`dws_pl_cost_md_pdf` alone is not enough to build a profit result table shaped like `dws_cash_account_md_pdf`.

Reason:
- it is already an aggregated profit-cost fact table
- it loses fields needed for result-wide metrics such as:
  - paid vs unpaid / due split
  - labor-cost subtype split
  -析出 (`sy_type`) split
  - raw subject mapping
  - direct `sku1` / `sku2` style output dimensions

### Minimum fields that must be preserved in a profit-cost detail layer
If building a profit result table, keep or rebuild a more detailed profit-cost layer with at least:
- `subject`
- `expensetypecategory`
- `expensetypename`
- `paymentlinestatusdesc`
- `realpaymentdate`
- `createddate`
- `sy_type`
- `sku1`, `sku2` (or an explicit mapping from `cci2_name`, `cci3_name` to them)
- optionally `from_table`, `prepay_type1`, `prepay_type2` for auditability

### Result-table design rule
Prefer a three-layer model:
1. revenue layer from `dwd_order_receipt_refund_md_pdf`
2. enhanced profit-cost detail layer (not just `dws_pl_cost_md_pdf`)
3. final profit result wide table, e.g. a `dws_pl_account_md_pdf`-style table

Do not keep piling result-table-specific fields directly onto `dws_pl_cost_md_pdf` unless the user explicitly wants that denormalized direction.

For the 声乐 `GMV和退费` daily Feishu sync, including cron/script lookup, Feishu token mismatch notes, `声乐-月课` independent-stage handling for `张大伟月课`, the later restore of ordinary 声乐 二/三/四/五阶 stage filters, and the 2026-05-18 supplemental `罗一豪二阶` column that must stay outside `STAGE_ORDER`, see `references/vocal-gmv-refund-daily-month-course-stage-20260511.md`.

For questions about whether `tock_ods_feishu_refund_approval_detail_all_d` can distinguish stage, or finding backend-team orders when the user gives business-side labels that do not match `camp_name` / `camp_group_name`, see `references/refund-approval-stage-and-backend-team-order-lookup-20260518.md`. Key points: the approval table has no native stage/camp fields, but `order_no = dwd_order_flow_df.flow_no` then `camp_id -> dim_camp_df.class_stage_name` works; team-like labels may actually land in `order_emp_name`, and business category names may require an external mapping rather than exact track-name search.

Current verified script behavior as of 2026-05-18:
- cron job: `声乐GMV和退费日报` / `28862874b814` / daily `10:05`
- entry script: `/Users/zheng/.hermes/python/projects/gmv-daily/vocal_gmv_refund_daily/run_job.py`
- target sheet id: `a5qFM6`
- the user-facing wiki URL may contain token `U1ugw3E1TiBmXJksyZcc6U6VnZc`, while the script writes underlying spreadsheet token `<REDACTED_FEISHU_SPREADSHEET_TOKEN>`; report both instead of assuming they are identical
- ordinary `cci3_name='声乐'` rows are currently restricted to `class_stage_name IN ('二阶营期','三阶营期','四阶营期','五阶营期')` and `new_front_end_name LIKE '%后端%'`
- `cci3_name='声乐-月课'` remains a separate displayed bucket `张大伟月课`
- `后端整体` currently sums the visible STAGE_ORDER buckets after reindexing, not broader non-visible stages
- live sync verification should include script syntax/command result and, when a write was actually run, Feishu readback of `a5qFM6!B1:G7`

Pitfall: an older session temporarily removed the ordinary 声乐 stage filter; this was later corrected. Do not apply the older “后端整体 broader than visible stage columns” rule unless the user explicitly asks to change the口径 again.

## Cash-account indicator table for total income / total expense

When the user asks for “总收入 / 总支出” by SKU or SKU bundle, prefer the cash-account indicator table instead of reconstructing from separate GMV and cost-detail tables.

Verified ClickHouse mapping:
- ODPS/business table: `dws_cash_account_indicators_md_pdf`
- ClickHouse table: `tock_dws_cash_account_indicators_md_pdf`
- date field: `p_date`
- SKU fields: `sku1`, `sku2`
- metric field: `indicators_name`
- value field: `data_d`

Use `indicators_name IN ('总收入','总支出')` and aggregate `data_d`. For current-month-to-date, filter `toDate(p_date) >= toStartOfMonth(today()) AND toDate(p_date) <= today()`.

Session-specific examples and pitfalls for bundled SKUs such as `口琴(含美妆)` and `声乐IP季课(含冥想瑜伽)`, plus a review checklist for long dashboard SQL based on `/Users/zheng/Desktop/2.sql`, are in `references/cash-account-indicators-and-dashboard-sql-review-20260512.md`.

## Communication style for this user

- Keep replies clear and calm.
- Avoid overly formal or template-heavy formatting.
- In SQL / metric work, ask for clarification when the data definition or filter logic is ambiguous.
- For Feishu-facing SQL debugging explanations, avoid Markdown tables when rendering context is uncertain. Prefer concise plain-text chains or bullets such as `step: value`.
