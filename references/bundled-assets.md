# Bundled Assets

本文件说明包内资产如何用于通用数据查询。不要把这些资产当作某个项目的强制流程；它们只是 schema、历史 SQL、方法经验和检索材料。

## Schema KB

路径：

```text
references/sql-query-method-internal/references/schema-kb/
```

主要文件：

- `schema_kb.md`: schema 知识库说明。
- `unified_schema_index.json`: 统一 schema 索引。
- `field_to_tables.json`: 字段到表的反查索引。
- `table_mapping.json`: 表映射。
- `clickhouse_manifest_latest.json`: ClickHouse 表结构快照。
- `odps_manifest_latest.json`: ODPS 表结构快照。

推荐命令：

```bash
python scripts/search_schema.py order --limit 20
python scripts/search_schema.py refund --file unified_schema_index.json --limit 20
```

## Historical SQL

规范化后的 SQL 路径：

```text
references/old-sql/sql/
```

索引：

```text
references/historical-sql-index.md
```

历史 SQL 仅作为参考，不保证当前可直接执行。索引中的 `trust_level` 用来提示复用风险：

- `medium`: 有执行产物或较清楚的项目来源，但仍需复核。
- `low`: 历史草案、旧项目 SQL 或来源不完整，只能提取字段和思路。
- `needs-review`: 信息不足，必须重新审查。

推荐命令：

```bash
python scripts/search_old_sql.py gmv --limit 20
python scripts/search_old_sql.py refund --domain refund --trust medium --limit 20
```

## Method Skills

路径：

```text
references/sql-query-method-internal/references/method-skills/
```

这些文件记录了特定业务主题的查询、报表或同步经验。它们是参考资料，不是可安装的独立 skill。使用方式：

1. 先按用户问题匹配业务域。
2. 再读取对应 method reference 的 `SKILL.reference.md` 或 references。
3. 提取口径、字段、join、状态过滤和历史坑。
4. 回到当前任务重新生成 SQL，不直接照搬旧 SQL。

## Local Outputs

任意仓库或本地目录都使用：

```text
data-query-work/
├── briefs/
├── reviews/
├── sql-drafts/
├── discovery-reports/
├── requirement-gaps/
└── exports/
```

不要强制创建任何项目专属目录。

## Connection Templates

Connection templates live under:

```text
templates/connections/
```

Use `data-sources.yaml.example` for multi-engine profiles, or engine-specific env files when a simple local setup is enough. `scripts/setup_connections.py` can create a local config interactively. Scripts read credentials in this order:

1. `--config <yaml>`
2. `INTERNAL_DATA_QUERY_CONFIG`
3. `data-query-work/config/data-sources.yaml`
4. `local/data-sources.yaml`
5. `~/.internal-data-query/data-sources.yaml`
6. `--env-file <env>`
7. process environment variables

Never write filled credentials back into this package.

## Execution And Metabase Scripts

- `scripts/run_query.py`: unified query runner for ClickHouse, ODPS, MySQL, and Metabase.
- `scripts/setup_connections.py`: interactive local connection setup for Metabase, ClickHouse, ODPS, and MySQL.
- `scripts/metabase_search.py`: find existing cards or dashboards before writing SQL.
- `scripts/metabase_get_card.py`: inspect a card and its native SQL.
- `scripts/metabase_run_card.py`: run a card and export CSV/XLSX.

## Output Templates

- `templates/query-brief.md`
- `templates/sql-review.md`
- `templates/result-summary.md`
- `templates/feature-data-dependency.md`
