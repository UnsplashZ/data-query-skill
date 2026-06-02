# Query Execution Contract

本契约约束 internal-data-query 的 SQL 查询执行闭环。任何真实查数都必须先确认数据源、SQL 只读性、采样策略和结果可信度；执行不可用时必须显式标记 `unverified`，不能把历史 SQL、示例配置或候选知识当作当前真源。

## 1. 执行前决策

1. 先检索当前仓库、schema KB、历史 SQL、Metabase card/dashboard、method references、`data-query-work/knowledge/`。
2. 先选定 engine/profile，再写 SQL；不能静默切换 ClickHouse、ODPS、MySQL 或 Metabase。
3. SQL 必须只读。默认禁止 DDL、DML、权限、导出、过程执行、维护类语句。
4. 每个查询必须声明时间字段、时间范围、统计粒度、状态过滤、金额单位和业务 scope。
5. 执行路径必须是 `static check -> sample -> validation -> full scope`。无法执行 full scope 时，结果只能标为 `partially_verified` 或 `unverified`。

## 2. Dialect 策略

### ClickHouse

- 日期字段常见为 `dt`、`event_time`、`created_at`、`pay_time`；优先用 `toDate`、`formatDateTime`、`INTERVAL n DAY`。
- 采样优先 `LIMIT n` 和小日期范围；大表聚合先按分区或日期过滤。
- JOIN 前先检查 join key 唯一性或分布，避免一对多膨胀。
- 导出时注意 ClickHouse 类型到 CSV/XLSX 的转换，金额字段必须保留单位。

### ODPS / MaxCompute

- 日期分区常见为 `dt`、`ds`、`biz_date`、`stat_date`；先确认分区字段再扩大范围。
- 日期函数需按 ODPS 方言复核，例如 `to_date`、`dateadd` 等，不要直接套用 ClickHouse 函数。
- 首次执行必须限制日期范围或 `LIMIT`；大结果集优先聚合，不直接明细全量导出。
- 权限不足时不要换表猜测，先回到 schema KB、历史 SQL 和用户确认。

### MySQL

- 日期函数通常使用 `DATE()`、`DATE_FORMAT()`、`DATE_SUB()`。
- 必须使用只读账号；禁止 `SET`、事务写入、临时表写入、锁表、DDL/DML。
- 明细查询必须加 `WHERE` 和 `LIMIT`；聚合查询也要有时间范围和状态过滤。

### Metabase

- Card / dashboard 是正式 source。能匹配时优先复用 card 并运行结果。
- Native SQL 执行必须指定 database/card 上下文；模板变量需要显式传入 parameters。
- Metabase 结果需要记录 card id、database id、参数、运行时间和权限/过滤风险。

## 3. Static Check 规则

运行 `scripts/query_static_check.py` 检查：

- error：非 `SELECT/WITH/EXPLAIN SELECT`、多语句、DDL/DML、权限语句、导出/执行/维护语句。
- warning：缺时间范围、缺 `LIMIT`、缺 `WHERE`/scope、JOIN cardinality 风险、明显方言风险。
- error 必须阻断执行；warning 可以继续 sample，但输出必须记录风险和修正计划。

`scripts/run_query.py` 在有 SQL 的情况下会强制执行 static check。Metabase 纯 card 查询没有 SQL 文本时不做 SQL static check，但仍需要记录 card source 和参数。

`scripts/run_query.py` 的 JSON 报告必须至少包含：

- `static_check`：SQL 静态检查结果；纯 Metabase card 且无 SQL 文本时显式标记 `skipped` 和原因。
- `execution_stage`：`card`、`sample`、`full` 或 `manual`。默认按 `--card-id`、`--sample-limit`、`--full-scope` 推断，也可用 `--execution-stage` 声明；声明只影响报告，不会自动执行额外 sample/full 查询。
- `sample_limit` / `full_scope`：用于说明本次执行的采样或全量语义；调用方仍需自己控制 SQL 范围。
- `confidence`：默认 `card/sample/full -> partially_verified`，`manual -> unverified`；只有外部验证闭环完整时，结果说明中才可升级为 `verified`。
- `validation_notes`：记录静态检查、采样/全量声明、card 参数或人工校验说明。

## 4. 失败修正循环

### 字段不存在

1. 停止扩大查询范围。
2. 回查 schema KB、Metabase SQL、历史 SQL 和当前仓库。
3. 确认字段别名、分区字段、表版本和 engine。
4. 修正后先跑 `LIMIT` 或小日期范围。

### 权限不足

1. 不切换到写账号，不尝试绕过权限。
2. 记录 engine/profile、对象名、权限错误。
3. 优先寻找已授权 Metabase card 或只读替代表。
4. 结果可信度最多 `partially_verified`，除非可运行等价 source。

### 方言错误

1. 确认 engine，不在不同 engine 间静默迁移。
2. 将日期、limit、类型转换、字符串函数改成目标 engine 方言。
3. 对修正 SQL 重新运行 static check。

### Timeout / 资源过大

1. 缩小时间范围、增加分区过滤和 `LIMIT`。
2. 先跑分布枚举和聚合 sanity check。
3. 必要时分日期/分 scope 批量执行，不直接全量明细。

### JOIN 膨胀

1. 分别检查左右表 join key 的 `count(*)` 与 `count(distinct key)`。
2. 先按 join key 采样查看重复行。
3. 对一对多关系先预聚合或去重，再执行主查询。

### 空结果

1. 检查时间范围、状态过滤、scope、时区和分区字段。
2. 用更小字段集查询分布，而不是立即判定业务为 0。
3. 若所有验证都为空，输出中注明验证 SQL 和空结果风险。

## 5. 采样策略

- `LIMIT` sample：首次执行明细查询必须加 `LIMIT`。
- 小日期范围 sample：先跑 1 天、3 天或单个分区，再扩大到目标周期。
- 枚举分布：对状态、渠道、SKU、课程、来源字段先跑 `group by` 分布。
- Join cardinality：JOIN 前验证 key 粒度，必要时预聚合。
- 聚合 sanity check：核心指标至少做行数、去重数、金额总和、空值比例或边界日期检查。
- Full scope：只有 sample 和 validation 通过后才运行完整范围。

## 6. Confidence 标签

- `verified`：使用当前可执行 source 完成 static check、sample、validation 和目标范围查询；结果包含 source、SQL/参数、时间范围和验证记录。
- `partially_verified`：只完成部分验证，例如 sample 通过但 full scope timeout，或 card 可运行但字段口径仍需业务确认。
- `unverified`：没有真实执行，或仅有静态检查/离线证据/用户口述。不得把该结果当作最终事实。
- `historical_only`：只来自历史 SQL、旧 card、旧文档或过期知识。只能作为写 SQL 的线索，不能作为当前结论。

输出结果必须包含 `source`、`metric_definition`、`sql_or_card`、`result`、`validation`、`confidence`、`risk`。
