---
name: odps-clickhouse-schema-kb-workflow
description: "Refresh and use the user's local ODPS/ClickHouse schema knowledge base before writing SQL. Default workflow: local KB lookup first, then live table/value validation, then final SQL."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [odps, clickhouse, schema, sql, metadata, knowledge-base]
---

# ODPS / ClickHouse Schema KB Workflow

## When to use

Use this whenever the user asks for:
- CK / ClickHouse / ODPS SQL
- table lookup, field lookup, or mapping ODPS → ClickHouse
- dashboard SQL, ad hoc query drafting, or schema reconnaissance

This skill exists to avoid guessing physical field names from business wording.

## Core rule

Never go straight from business requirement to final SQL.
Always use this execution flow:

1. **Decide the data source first**: ODPS or ClickHouse, based on user instruction, source-of-truth needs, dashboard/latency needs, and whether the target source actually contains the required fields.
2. **Check the corresponding schema / common-table inventory** for that source before drafting SQL.
3. **Verify live structure and values** against the actual source: fields, types, join keys, enum values, and sample rows.
4. **Draft candidate SQL from verified knowledge**, then review business logic and grain: denominator/numerator, SKU/camp/cci fields, joins, time fields, and filters.
5. **Check SQL dialect and table-specific rules** before running:
   - ClickHouse: `FINAL`, `_sign > 0`, 21.8 syntax limits, String-vs-Date comparisons, JOIN limitations, ASCII aliases for driver stability, and avoid `local` tables unless explicitly verified.
   - ODPS: partition pruning, `${param}` substitution, MaxCompute function/type/window syntax, and large-table join scope.
6. **Run locally before output**: start with small range / `LIMIT`, fix syntax or logic failures, sanity-check row counts and key metrics, then run the intended scope.
7. **Only then output** the executable SQL plus results or result path. If the run fails, fix or switch source instead of presenting the failed SQL as final.

## Environment

- Python env: `hermes-sql`
- Project dir: `${HERMES_HOME:-~/.hermes}/python/projects/sql-metadata-index`
- Main refresh script: `${HERMES_HOME:-~/.hermes}/python/projects/sql-metadata-index/refresh_schema_kb.py`
- Outputs:
  - `${HERMES_HOME:-~/.hermes}/cleaned/projects/sql-metadata-index/index/unified_schema_index.json`
  - `${HERMES_HOME:-~/.hermes}/cleaned/projects/sql-metadata-index/index/field_to_tables.json`
  - `${HERMES_HOME:-~/.hermes}/cleaned/projects/sql-metadata-index/index/table_mapping.json`
  - `${HERMES_HOME:-~/.hermes}/cleaned/projects/sql-metadata-index/index/refresh_summary.json`
  - `${HERMES_HOME:-~/.hermes}/cleaned/projects/sql-metadata-index/index/schema_kb.md`

## Refresh workflow

### Full refresh

```bash
export HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
eval "$(conda shell.bash hook)"
conda activate hermes-sql
python "$HERMES_HOME/python/projects/sql-metadata-index/refresh_schema_kb.py"
```

### Single-source refresh

```bash
python "$HERMES_HOME/python/projects/sql-metadata-index/refresh_schema_kb.py" --source odps
python "$HERMES_HOME/python/projects/sql-metadata-index/refresh_schema_kb.py" --source clickhouse
```

### What the script does

- ODPS: pulls table inventory, compares `inventory_signature`, then fetches detailed schema only for added/changed tables.
- ClickHouse: pulls `system.tables`, compares `metadata_modification_time + create_table_query_hash`, then fetches detailed columns only for added/changed tables.
- Builds unified cross-source index and field reverse index.
- Writes a human-readable markdown summary.
- Includes retry logic for transient ODPS connection resets.

## How to use the KB before writing SQL

### Step 1: check the local KB

For quick file inspection, read:
- `refresh_summary.json` → freshness + change counts
- `schema_kb.md` → high-level mapping summary
- `field_to_tables.json` → which tables contain a field
- `unified_schema_index.json` → full per-table schema

Typical quick checks:
- does `union_id` exist in the candidate table?
- is the product field `sku`, `camp_sku`, or `main_goods_sku`?
- is the CK target same-name or `tock_`-prefixed?

### Step 2: validate live structure

Do not trust the KB alone. Run minimal live SQL.

#### ClickHouse structure check

```sql
SELECT name, type
FROM system.columns
WHERE database = 'drh'
  AND table = 'your_table'
ORDER BY position
```

#### ClickHouse enum/value check

```sql
SELECT some_field, count()
FROM your_table
GROUP BY some_field
ORDER BY count() DESC
LIMIT 20
```

#### ODPS structure check

Use ODPS metadata / describe commands available in the user's environment to confirm fields when needed.

### Step 3: write final SQL

Only after steps 1 and 2 are done.

## User-specific conventions to apply

### Data-source priority

For business requests involving the user's data:
1. ODPS user-named frequent tables
2. all `dwd_` / `dws_`
3. cron/project-referenced tables
4. relevant `ods_` sync tables

Default querying preference:
- ODPS first for source-of-truth analysis
- ClickHouse mainly for dashboard / acceleration / lookups

### ODPS ↔ CK mapping caveat

Do not assume the same table name across ODPS and ClickHouse.
Many CK synced tables use `tock_` prefix, e.g.:
- `dwd_order_refund_df` → `tock_dwd_order_refund_df`
- `dws_cash_account_indicators_md_pdf` → `tock_dws_cash_account_indicators_md_pdf`
- `ods_feishu_refund_approval_detail_all_d` → `tock_ods_feishu_refund_approval_detail_all_d`

### CK duplicate joins and null/blank flags

When cleaning or rewriting ClickHouse ad hoc SQL with multiple left joins:
- First identify the intended output grain, then test each join source at that grain with `GROUP BY join_keys HAVING count() > 1`; do not assume a join is one-to-one.
- For `tock_emp_external_user`, same `(union_id, external_user_id)` can have many rows. If the desired current/primary relation is intended, verify and prefer `WHERE union_id_rn = 1 AND belong_rn = 1` before grouping; this removes join multiplication in known cases, but still validate live counts.
- If the main table is itself duplicated at the intended grain, aggregate it in a `base` CTE first. Use deterministic aggregates such as `max(time_field)` plus `argMax(value, ifNull(time_field, toDateTime('1970-01-01')))` for latest-row attributes.
- Do not write presence flags as `x IS NOT NULL OR x <> ''`; that can misclassify null/empty values. Use `if(notEmpty(ifNull(x, '')), '是', '否')`, or derive the flag from an already aggregated metric, e.g. `if(ifNull(gmv, 0) >= 2980, '是', '否')`.
- ClickHouse 21.8 may incorrectly resolve aggregate aliases when an aggregate alias reuses an original column name inside a CTE, producing errors like `Aggregate function ... is found in WHERE`. Avoid alias reuse for aggregated columns: use names like `max_create_time`, `base_nick_name`, `camp_gmv`, then alias back only in the outermost SELECT.

### Business wording vs physical fields

Do not map business wording directly to field names. Example pattern:
- order table may use `main_goods_sku`
- 领课/用户行为表 may use `sku`

Always validate on the actual table before final SQL.

### Metabase ClickHouse SQL conventions

When converting SQL for a Metabase ClickHouse dashboard:
- Prefer Metabase template variables over ClickHouse native query parameters. Do **not** output `{as_of_date:String}` / `{sku:String}` unless the user explicitly asks for native ClickHouse parameters; Metabase may not bind them and can raise `Query parameter ... was not set`.
- Use ordinary Metabase variables for computed dates, e.g. `toDate({{as_of_date}})` or `formatDateTime(toDate({{start_month}}), '%Y%m')`. Date variables are better than Field Filters when the value is used for month/date arithmetic rather than filtering one physical date column.
- For optional filters, use Metabase optional clauses, e.g. `[[AND t.sku1 = {{sku}}]]`. Leave `sku` blank to mean all SKU; avoid synthetic defaults like `all` unless the user explicitly wants that behavior.
- If the user wants a dashboard that can select months, output a monthly-grain query (`GROUP BY mn`) rather than a single `as_of_date` query. Build a `month_ctx` with `mn`, `month_start`, and the month’s max available `p_date` as `month_end`; compute balance at `month_end` and month-start previous balance at `month_start`.
- ClickHouse 21.8 can be fragile with CTE column names and JOIN aliases. When joining a CTE such as `balance`, explicitly alias join keys (`m.mn AS balance_month`) and join on that alias (`r.mn = b.balance_month`) instead of relying on `b.mn`.
- If a Metabase variable is configured as a Field Filter, the SQL clause should usually be `[[AND {{sku}}]]`; if it is a normal Text variable, use `[[AND t.sku1 = {{sku}}]]`.

## Recommended response pattern for future SQL requests

When asked for SQL, follow this structure internally:

1. identify likely candidate tables from KB
2. inspect live fields and key value enums
3. note any ambiguities needing user clarification
4. output final SQL only after field confirmation

If user explicitly asks to “先澄清不明确的地方”, still do local KB + live validation first, then ask only the minimum necessary business questions.

## Pitfalls

- **Do not guess field names** from business language.
- **Do not assume same table names across ODPS and CK.**
- **Do not skip live validation** just because the KB looks clear.
- **Do not forget CK version constraints** when drafting SQL.
- **Do not forget `FINAL + _sign > 0`** for `drh` tables when the user's convention requires it.
- ODPS refresh may show recurring `changed` tables because source metadata changes; this does not always mean a broken refresh pipeline.

## Verification checklist

Before sending final SQL, confirm:
- [ ] candidate table chosen from KB
- [ ] live column check completed
- [ ] key enum/value check completed
- [ ] join key confirmed (`union_id`, `external_userid`, etc.)
- [ ] CK-specific conventions applied when relevant
- [ ] final SQL uses actual physical field names, not guessed names
