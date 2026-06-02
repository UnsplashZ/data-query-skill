---
name: internal-data-query
description: 通用内部数据查询 skill，适用于任意仓库或 AI 助手。Use when the user asks to 查数据, 写 SQL, 看 Metabase, 搜看板/卡片, 找字段, 接页面字段到表, 导出订单/退款/GMV, 验证报表口径, 选择数据源, 搜索 schema KB 或历史 SQL, 编写只读 Metabase/ODPS/MaxCompute/ClickHouse/MySQL SQL, 复核查询假设, 保存 Query Brief/SQL 草案/复核/发现报告/本地导出, 或安装/配置数据查询 skill、配置内部数据源账号。安装或配置时，必须引导用户把 Metabase、ClickHouse、ODPS/MaxCompute、MySQL 等只读凭证写入本机 data-sources.yaml，不得写入 skill 包或仓库。
license: Internal Use Only
metadata:
  version: 1.0.0
  author: Hermes Agent
  hermes:
    version: 1.0.0
    author: Hermes Agent
    tags: [sql, data-query, odps, clickhouse, metabase, mysql, internal-data, schema-kb]
---

# Internal Data Query

## Mandatory Installation Contract

If the current task is to install, unpack, activate, or configure this skill, do not stop at "installed".

Follow this standard path:

```text
receive zip/link
-> unpack into the AI tool's skills directory or a user-selected local directory
-> confirm SKILL.md, manifest.json, and scripts/setup_connections.py exist
-> run package validation and sensitive-info scan when available
-> ask which readonly data sources the user wants to configure
-> create a local data-sources.yaml
-> run a smoke check
-> tell the user they can trigger queries with natural language
```

Required installation behavior:

- After installation, report the activation state: package present, manifest checked or not checked, sensitive scan checked or not checked, config path, configured sources, smoke check result, and remaining setup gaps.
- Ask whether to configure Metabase, ClickHouse, ODPS/MaxCompute, and/or MySQL now.
- If the user agrees and a TTY is available, run `python scripts/setup_connections.py`.
- If no TTY is available, run `python scripts/setup_connections.py --non-interactive --output <local-path> --overwrite` only for a local user-owned path, then ask the user to edit the placeholders locally.
- The default local config path is `~/.internal-data-query/data-sources.yaml`; the setup script should set file permissions to `0600` where the OS allows it.
- Never write credentials into `SKILL.md`, README, manifests, shared zip files, generated SQL, repository docs, or chat transcripts.
- After config, run at least one non-sensitive smoke check such as `python scripts/setup_connections.py --help`, `python scripts/search_schema.py refund --limit 3`, `python scripts/check_connections.py --config <path> --offline-ok` if available, `python scripts/discover_data_sources.py --config <path>` if available, `select 1`, or a Metabase search.

Suggested user-facing activation message:

```text
internal-data-query 已安装。要执行真实查询，还需要配置只读数据源。
我可以现在帮你配置 Metabase、ClickHouse、ODPS/MaxCompute 或 MySQL。
请确认要配置哪些数据源；凭证只会写入你的本机 ~/.internal-data-query/data-sources.yaml。
```

Natural-language triggers after setup include: "帮我查一下数据", "写个 SQL", "看一下 Metabase 里有没有这个指标", "这个页面字段应该接哪张表", "导出某个时间段的订单/退款/GMV", "验证这个报表口径", "配置内部数据源账号".

## Overview

Use this skill to turn a business data question into a reproducible query workflow. It is repository-agnostic and does not rely on any fixed project workflow or directory. Work in the user's current repository or folder, and store generated outputs in a local work directory.

Core rule: never invent tables, fields, row counts, credentials, or results. Choose the source, inspect schema or prior SQL, write a scoped readonly query, validate it, then deliver the SQL/result with assumptions and residual risk.

## AI Operating Contract

Follow these rules for every task:

- Search existing dashboards, schema KB, current repo files, and historical SQL before writing new SQL.
- Do not guess table names, field names, join keys, status enums, amount units, or metric definitions.
- If execution is available, run a small sample or `LIMIT` query before the full query.
- If execution is unavailable, label the SQL/result `unverified` and list the missing checks.
- Final output must include source, metric definition, validation performed, and remaining risks.
- Prefer reusing an existing Metabase card/dashboard when it matches the user question; only write new SQL after checking existing assets.
- Store reusable artifacts in `data-query-work/` or the user-selected local folder.

## Default Output Directory

For any repository, create a local folder named `data-query-work/` unless the user gives another path:

```text
data-query-work/
├── briefs/
├── reviews/
├── sql-drafts/
├── discovery-reports/
├── requirement-gaps/
└── exports/
```

Default saves:

- Query Brief: `data-query-work/briefs/<date>_<topic>.md`
- Query Review: `data-query-work/reviews/<date>_<topic>-review.md`
- SQL Draft: `data-query-work/sql-drafts/<date>_<topic>.sql`
- Discovery Report: `data-query-work/discovery-reports/<date>_<topic>.md`
- Requirement Gap: `data-query-work/requirement-gaps/<date>_<topic>.md`
- Query output/export: `data-query-work/exports/<date>_<topic>.*`

If the repository has its own docs, analytics, notebook, or reports folder, use it only when the user asks or it is clearly the local convention.

## Installation Guidance

When helping a user install or configure this skill with an AI assistant, treat installation as incomplete until a local connection profile exists.

For zip/link installs, the AI assistant should first unpack the package into the target skills directory or another user-selected local directory, then verify these files exist:

- `SKILL.md`
- `manifest.json`
- `scripts/setup_connections.py`

When available, run:

```bash
python scripts/validate_manifest.py
python scripts/scan_sensitive_info.py
```

If those checks cannot run, say so in the installation status report instead of silently skipping them.

After unpacking or installing the skill, the AI assistant must ask whether the user wants to configure Metabase, ClickHouse, ODPS/MaxCompute, and/or MySQL now. If yes, run:

```bash
python scripts/setup_connections.py
```

This writes a local profile to `~/.internal-data-query/data-sources.yaml` by default. Query scripts read this path automatically. The user can also set `INTERNAL_DATA_QUERY_CONFIG`, pass `--config <path>`, or use a copied template such as `data-query-work/config/data-sources.yaml`.

If the assistant cannot open an interactive terminal, ask the user which source accounts to configure in chat, then either help them fill `templates/connections/data-sources.yaml.example` into a local path or run `python scripts/setup_connections.py --non-interactive` and edit the generated YAML. Do not stop at "installed" when the user's goal is to use real data.

After setup, report:

- package location
- config path
- configured source names
- credential boundary
- whether the config file was set to `0600`
- smoke checks run
- what still needs user input before real queries can execute

Ask them to provide the accounts or access material needed for actual queries:

- Metabase: base URL plus API key, session id, or username/password.
- ClickHouse: host, port, database, username, password, secure/TLS flag, and readonly profile.
- ODPS / MaxCompute: endpoint, project, access id/access key or the team's approved credential method, plus tunnel/project settings if required.
- MySQL or other SQL engines: host, port, database/schema, username, password, SSL/TLS settings, and readonly role.

Keep credentials in the target user's local environment, secret manager, or local config file. Do not write credentials into `SKILL.md`, shared zip files, generated SQL, manifests, committed docs, or chat transcripts.

Install optional runtime dependencies only when real execution is needed:

```bash
python -m pip install -r requirements.txt
```

## Workflow

### 1. Turn The Request Into A Query Brief

Extract:

- metric/entity: GMV, refund, order, cashflow, profit, ROI, conversion, retention, cohort, user, channel
- time range and time field: pay date, refund date, handover date, event date, snapshot date, month
- grain: order, user, day, month, SKU, camp, product, channel, stage, class
- filters/scope: product, front/back end, channel, camp, stage, status, official class, region, owner
- output shape: SQL, table, CSV/XLSX, dashboard input, report, chart, diagnosis
- use of result: one-off answer, meeting, recurring report, dashboard, API design, QA evidence

Ask one concise clarification question only when the missing choice changes the result materially. Otherwise proceed with explicit assumptions.

### 2. Choose The Data Source Before SQL

Search in this order:

1. Current repository docs, SQL files, scripts, reports, notebooks, and data catalogs.
2. Bundled schema KB: `references/sql-query-method-internal/references/schema-kb/`.
3. Normalized historical SQL index: `references/historical-sql-index.md`.
4. Bundled method skills: `references/sql-query-method-internal/references/method-skills/`.
5. Live schema inspection through the user's readonly connection.

Source decision rules:

- ODPS / MaxCompute: standard warehouse definitions, DWD/DWS, finance/cashflow, offline reports.
- ClickHouse: fast exploration, dashboard-backed tables, large indexed exports, near-real-time checks.
- Metabase: existing dashboard SQL and question/card context; treat as evidence unless the owner confirms it is canonical.
- MySQL: application truth, read models, snapshots, and backend-aligned checks.
- Historical SQL: field and logic evidence only; revalidate before reuse.

Do not silently switch sources. State why a source was chosen and what risk remains.

### 3. Search Bundled Assets

Use scripts when available:

```bash
python scripts/metabase_search.py refund --config local/data-sources.yaml
python scripts/search_schema.py --field order_no --engine clickhouse --limit 20
python scripts/search_old_sql.py refund --domain refund --context 3 --limit 20
python scripts/run_query.py --engine clickhouse --sql-file data-query-work/sql-drafts/example.sql --config local/data-sources.yaml
python scripts/setup_connections.py
python scripts/validate_manifest.py
python scripts/scan_sensitive_info.py
```

Load `references/bundled-assets.md` to understand the packaged schema KB, old SQL, and method references.

### 4. Write Scoped Readonly SQL

Write from the target grain upward:

1. Base CTE at the correct grain.
2. Time, status, and scope filters early.
3. Explicit date boundaries and amount units.
4. Joins only after checking join keys and cardinality.
5. Aggregation after grain control.
6. Stable output aliases and ordering.

Avoid DDL, DML, deletes, updates, grants, or production mutations unless the user explicitly changes the task from query to database operation.

### 5. Validate

When execution is available:

1. Inspect schema or run a dry-run/metadata query.
2. Run a small date range or `LIMIT`.
3. Check enum/status distribution.
4. Check join cardinality.
5. Check aggregate sanity.
6. Run full scope.

If execution is unavailable, deliver SQL as `unverified` and list the missing checks.

### 6. Deliver

Return:

- result or output file path, if produced
- executable SQL, if requested or useful
- source used and rejected alternatives
- key filters, grain, dates, amount units, status handling
- validation performed
- assumptions, limitations, and next checks

Persist reusable work in `data-query-work/` using the default layout.

## Role-Based Use

- AI quick data lookup: clarify the question, search Metabase/schema/history, run a small query, return concise result plus caveats.
- Product metric exploration: create `templates/query-brief.md`, compare candidate sources, label metric risk, then produce a result summary.
- Development field mapping: use `templates/feature-data-dependency.md`, map UI/API fields to tables/cards, and identify missing data.
- Existing dashboard reuse: run `metabase_search.py`, inspect cards with `metabase_get_card.py`, run matching cards with `metabase_run_card.py`, then decide whether new SQL is necessary.
- QA data validation: write a focused SQL draft, run sample/full checks, save `templates/sql-review.md` and `templates/result-summary.md`.

## References

- `references/bundled-assets.md`: asset map and how to use packaged schema/SQL/method references.
- `references/query-checklist.md`: end-to-end query checklist.
- `references/historical-sql-index.md`: normalized historical SQL index with trust level and business-domain tags.
- `references/sql-query-method-internal/`: original internal SQL method references, schema KB, and method skills.

## Scripts

- `scripts/validate_manifest.py`: verify manifest file list, byte sizes, and sha256 checksums.
- `scripts/scan_sensitive_info.py`: scan packaged files or a chosen path for likely leaked credentials and high-confidence sensitive values.
- `scripts/setup_connections.py`: prompt for Metabase, ClickHouse, ODPS, and MySQL readonly account details and write a local config profile.
- `scripts/search_schema.py`: search bundled schema KB by table, field, engine, or keyword.
- `scripts/search_old_sql.py`: search normalized historical SQL body and metadata with snippets, context, paths, and trust level.
- `scripts/run_query.py`: run readonly ClickHouse, ODPS, MySQL, or Metabase queries and export CSV/XLSX with row count and runtime.
- `scripts/metabase_search.py`: search existing Metabase cards/dashboards before writing SQL.
- `scripts/metabase_get_card.py`: fetch a card and print native SQL/metadata.
- `scripts/metabase_run_card.py`: run a card and export CSV/XLSX.

## Templates

- `templates/connections/data-sources.yaml.example`: multi-source connection config.
- `templates/connections/*.env.example`: engine-specific env examples for ClickHouse, ODPS, Metabase, and MySQL.
- `templates/query-brief.md`: business question and source exploration.
- `templates/sql-review.md`: SQL review checklist and decision.
- `templates/result-summary.md`: result, definition, validation, and risks.
- `templates/feature-data-dependency.md`: feature field mapping and data dependency review.
