---
name: internal-data-query
description: 通用内部数据查询 skill，适用于安装/配置内部数据查询能力、配置 Metabase/ClickHouse/ODPS/MaxCompute/MySQL 只读账号、刷新 schema/DDL/metadata、查数据、写只读 SQL、搜索 Metabase card/dashboard、找表字段、导出数据、验证报表口径、沉淀 data-query-work 知识。安装或配置时必须把凭证写入用户本机 data-sources.yaml，不得写入 skill 包、业务仓库或聊天记录；刷新 schema/DDL 前必须先说明会拉取的元数据范围并取得用户同意。
license: Internal Use Only
metadata:
  version: 0.1.3
  author: Hermes Agent
  hermes:
    version: 0.1.3
    author: Hermes Agent
    tags: [sql, data-query, odps, clickhouse, metabase, mysql, internal-data, schema-kb]
---

# Internal Data Query

## Core Contract

Use this skill to turn a business data question into a reproducible readonly query workflow.

Never invent tables, fields, row counts, credentials, query results, join keys, status enums, amount units, or metric definitions. Prefer existing evidence first: current repo files, refreshed schema index, Metabase, user-provided historical SQL index, and `data-query-work/knowledge/`.

This skill package must stay generic. It must not ship real business schema, historical SQL, exports, credentials, or default knowledge.

## Install And Configure

When the user asks to install, unpack, activate, or configure this skill, do not stop at "installed". Installation is only the first step; the agent must actively guide the user through readonly account/server configuration next.

Follow this flow:

1. Install or unpack the skill into the AI tool's skills directory or another user-selected local directory.
2. Confirm `SKILL.md` and `scripts/setup_connections.py` exist.
3. Run lightweight local checks when possible:

```bash
python scripts/scan_sensitive_info.py .
python scripts/post_install_check.py --offline-ok
```

4. Immediately ask which readonly sources to configure: Metabase, ClickHouse, ODPS / MaxCompute, MySQL.
5. Explain the required fields:
   - Metabase: base URL plus API key, session id, or username/password.
   - ClickHouse: host, port, database, username, password, secure/TLS.
   - ODPS / MaxCompute: endpoint, project, access id/access key, tunnel/project settings.
   - MySQL: host, port, database/schema, username, password, SSL/TLS.
6. Write credentials only to a user-owned local config path, defaulting to `~/.internal-data-query/data-sources.yaml`.
7. If a config already exists, use merge/add-source behavior. Do not overwrite the full config unless the user explicitly asks.
8. Run a connection smoke check only when network/VPN and real readonly credentials are available.
9. After config, ask whether the user allows a metadata/DDL refresh for the current business repository.
10. Tell the user to restart Codex after installing or replacing the skill.

After installation, use a direct prompt like:

```text
internal-data-query 已安装。接下来需要配置只读数据源，才能真实查数。

你要现在配置哪些数据源？
- Metabase：base URL，API key / session id / 用户名密码
- ClickHouse：host、port、database、username、password、TLS
- ODPS / MaxCompute：endpoint、project、access id/access key、tunnel
- MySQL：host、port、database/schema、username、password、SSL

凭证只会写入本机 ~/.internal-data-query/data-sources.yaml，不会写入仓库或聊天记录。
```

Use:

```bash
python scripts/setup_connections.py
python scripts/setup_connections.py --add-sources odps,mysql --non-interactive
python scripts/check_connections.py --config ~/.internal-data-query/data-sources.yaml --offline-ok
```

Never ask the user to paste passwords, access keys, GitHub tokens, database sessions, or API keys into chat. Never write credentials into `SKILL.md`, README, shared zip files, generated SQL, repository docs, or business repo files.

## Refresh Schema Metadata

After readonly profiles are configured, ask before connecting to real data sources for metadata refresh.

The prompt should make these points clear:

- The refresh reads metadata only: database/project names, table names, columns, types, comments, and available DDL.
- It does not read business rows or execute analytical queries.
- It writes results into the current business repository under `data-query-work/schema/`.
- The generated schema index may reveal internal table and field names, so the user should confirm it is acceptable for that repository.

Run only after user confirmation:

```bash
python scripts/refresh_schema.py --root <target-repo>
```

Useful options:

```bash
python scripts/refresh_schema.py --engine clickhouse --profile default --root <target-repo>
python scripts/refresh_schema.py --engine clickhouse --profile default --table-list tables.txt --default-database dm --root <target-repo>
python scripts/refresh_schema.py --engine clickhouse --profile default --table-list tables.xlsx --table-column table_name --root <target-repo>
python scripts/refresh_schema.py --replace --root <target-repo>
python scripts/refresh_schema.py --limit-tables 200 --root <target-repo>
```

Default outputs:

```text
data-query-work/schema/unified_schema_index.json
data-query-work/schema/ddl/<engine>/<profile>/<database>/<table>.sql
```

If the user declines metadata refresh, continue with repo files, Metabase, user-provided schema index, or live one-off metadata checks as explicitly allowed.

## Workspace Layout

When used inside a business repository, use exactly one default top-level workspace:

```text
data-query-work/
├── briefs/
├── reviews/
├── sql-drafts/
├── discovery-reports/
├── requirement-gaps/
├── exports/
├── schema/
└── knowledge/
```

Default artifact names:

- Brief: `data-query-work/briefs/YYYY-MM-DD__domain__topic__brief.md`
- SQL draft: `data-query-work/sql-drafts/YYYY-MM-DD__domain__topic__draft.sql`
- Review: `data-query-work/reviews/YYYY-MM-DD__domain__topic__sql-review.md`
- Discovery report: `data-query-work/discovery-reports/YYYY-MM-DD__domain__topic__discovery.md`
- Requirement gap: `data-query-work/requirement-gaps/YYYY-MM-DD__domain__topic__gap.md`
- Export: `data-query-work/exports/YYYY-MM-DD__domain__topic__sample.*`
- Knowledge candidate: `data-query-work/knowledge/candidates/YYYY-MM-DD__domain__topic__candidate-<id>.md`
- Reviewed knowledge: `data-query-work/knowledge/reviewed/YYYY-MM-DD__domain__topic__reviewed-<id>.md`
- Approved knowledge: `data-query-work/knowledge/approved/YYYY-MM-DD__domain__topic__approved-<id>.md`

Use this Markdown title pattern for generated process files:

```text
# YYYY-MM-DD / domain / topic / artifact type
```

Do not add a blanket `data-query-work/` entry to the target repo `.gitignore` by default. If exports or local temp files are sensitive, ignore only those concrete files or agreed local-only subpaths.

## Query Workflow

For every data question:

1. Clarify metric/entity, time range, grain, filters/scope, output shape, and use of result.
2. Search existing evidence before writing SQL:
   - current repo docs, SQL, scripts, reports, notebooks, data catalogs
   - `data-query-work/schema/unified_schema_index.json`
   - user-provided schema index or `INTERNAL_DATA_QUERY_SCHEMA_INDEX`
   - Metabase cards/dashboards
   - user-provided historical SQL index or `INTERNAL_DATA_QUERY_OLD_SQL_INDEX`
   - `data-query-work/knowledge/`
3. Choose the data source and state why.
4. Write scoped readonly SQL with explicit time range, grain, filters, amount units, and join assumptions.
5. Run static check before execution.
6. If execution is available, run a small sample or `LIMIT` query before full scope.
7. Deliver source, SQL/result, validation performed, assumptions, and remaining risks.

If execution is unavailable, label SQL/result as `unverified` and list missing checks.

## Source Rules

- Metabase: check first when the question likely maps to an existing dashboard/card.
- ClickHouse: use for fast exploration, dashboard-backed tables, larger indexed exports, and near-real-time checks.
- ODPS / MaxCompute: use for warehouse definitions, offline models, DWD/DWS-like data, and batch reporting.
- MySQL: use for application truth, backend-aligned checks, read models, and snapshots.
- Historical SQL: use only as a clue; revalidate fields and metric logic before reuse.

Do not silently switch data sources. State the source choice and residual risk.

## Knowledge Capture

The skill package does not include default knowledge. Capture reusable findings only from the target repository's own evidence.

Use `data-query-work/knowledge/` for candidates, reviews, approved metric definitions, source profiles, joins, golden queries, and semantic notes.

Do not mark old SQL or chat conclusions as approved truth. Write them as candidates first, then require review evidence before promotion.

Relevant scripts:

```bash
python scripts/capture_query_knowledge.py <artifact> --root <target-repo>
python scripts/validate_query_knowledge.py --root <target-repo>
python scripts/search_query_knowledge.py <keyword> --root <target-repo>
python scripts/promote_query_knowledge.py <id-or-path> --to reviewed --reviewer <name> --evidence <path> --root <target-repo>
python scripts/patch_query_knowledge.py --root <target-repo> --patch-file corrections.yaml --dry-run
```

## Scripts

- `scripts/setup_connections.py`: create or merge local readonly data-source config.
- `scripts/check_connections.py`: parse config and optionally smoke-check real readonly connectivity.
- `scripts/refresh_schema.py`: pull metadata, table structure, field details, and available DDL into `data-query-work/schema/`.
- `scripts/sample_tables.py`: generate latest-row sample SQL from schema index, execute ClickHouse sampling when allowed, and write masked JSONL/status/report outputs.
- `scripts/discover_data_sources.py`: summarize configured profiles, drivers, schema index, historical SQL index, and workspace knowledge.
- `scripts/search_schema.py`: search schema index by table, field, engine, or keyword.
- `scripts/search_old_sql.py`: search an external historical SQL index.
- `scripts/query_static_check.py`: check readonly SQL safety.
- `scripts/run_query.py`: run readonly ClickHouse, ODPS, MySQL, or Metabase queries and export CSV/XLSX.
- `scripts/metabase_search.py`: search Metabase cards/dashboards.
- `scripts/metabase_get_card.py`: fetch card SQL and metadata.
- `scripts/metabase_run_card.py`: run a card and export CSV/XLSX.
- `scripts/post_install_check.py`: lightweight install/config status report.
- `scripts/scan_sensitive_info.py`: scan high-confidence secret leaks and optional sensitive field-name risks.
- `scripts/patch_query_knowledge.py`: batch update, deprecate, promote, verify absent keywords, and validate knowledge files.

## References And Templates

- `references/query-checklist.md`: end-to-end query checklist.
- `references/query-execution-contract.md`: query execution and validation contract.
- `templates/query-brief.md`: business question and source exploration.
- `templates/sql-review.md`: SQL review checklist and decision.
- `templates/result-summary.md`: result, definition, validation, and risks.
- `templates/feature-data-dependency.md`: feature field mapping and data dependency review.
