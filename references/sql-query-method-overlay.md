# SQL Query Method Overlay

本文件把外部 `sql-query-method-internal` 包转成通用查询方法。

## Search Order

1. 当前仓库或工作目录中的 docs、SQL、scripts、notebooks、reports。
2. `references/sql-query-method-internal/references/schema-kb/`。
3. `references/historical-sql-index.md` 和 `references/old-sql/sql/`。
4. `references/sql-query-method-internal/references/method-skills/`。
5. 真实数据库的 readonly schema inspection。

## Source Choice

- ODPS / MaxCompute：标准仓库口径、DWD/DWS、财务/现金、历史一致性报表。
- ClickHouse：快速探查、看板支撑表、近实时问题、大量明细导出。
- Metabase：已有看板 SQL、参数、业务使用线索；默认作为 evidence，不自动认定为 canonical。
- MySQL：应用事实源、读模型、快照、后端对齐校验。
- Historical SQL：字段、join、过滤和报表形态参考；必须重新确认。

## Review Points

- 业务口径和物理字段分层。
- 时间字段：支付、退款、交接、事件、快照、月份不能混用。
- 金额单位：分、元、GMV、实收、退款、净收入、现金流、利润要区分。
- 粒度：用户、订单、营期、SKU、渠道、日期、阶段不能随意混 join。
- 状态过滤：支付成功、取消、退款、尾款、转班、审批状态等要明确。
- join 放大：先做 cardinality check，再聚合。
- 方言：ClickHouse、ODPS、MySQL 的日期函数、空值处理、窗口函数和 join 限制不同。
- 验证：没有执行权限时，SQL 只能标记为 `unverified`。

## Historical SQL Reuse

可以复用：

- 候选表名、字段名、参数名。
- 常见过滤条件和 join key。
- 历史报表输出维度。
- 已知坑和修正记录。

不能直接复用：

- 已过期时间范围。
- 未确认业务口径。
- 旧敏感明细输出。
- 当前引擎不兼容语法。
- 缺少 scope 或时间边界的全表 SQL。

## Save Outputs

默认保存到当前工作目录的 `data-query-work/`，不创建项目专属流程目录：

- Query Brief: `data-query-work/briefs/`
- Query Review: `data-query-work/reviews/`
- SQL Draft: `data-query-work/sql-drafts/`
- Discovery Report: `data-query-work/discovery-reports/`
- Requirement Gap: `data-query-work/requirement-gaps/`
- Export: `data-query-work/exports/`
- Reusable Knowledge: `data-query-work/knowledge/`

过程文件和知识条目统一使用 `YYYY-MM-DD__domain__topic__artifact-type.ext`，Markdown 首标题使用 `# YYYY-MM-DD / domain / topic / artifact type`。
