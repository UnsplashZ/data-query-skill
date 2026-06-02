# sql-query-method-internal

这是内部增强版 Hermes Skill 包，面向同一数据部门伙伴共享。

## 内容

- `SKILL.reference.md`：原 SQL 查询方法论参考文档。为避免 Codex 安装器把本包识别成多个 skill，该文件不再命名为 `SKILL.md`。
- `references/checklist.md`：查询任务检查清单。
- `references/schema-kb/`：已生成的 ODPS / ClickHouse schema KB index 文件。
- `references/schema-kb-index.md`：schema KB 文件清单。
- `references/old-sql/`：历史 SQL，来自 `.hermes/sql` 与 `.hermes/output/query_results`。
- `references/old-sql-index.md`：历史 SQL 文件清单。
- `references/method-skills/`：相关 data-science skills 与 references，用于补充业务口径和维护经验。
- `references/method-skills-index.md`：方法文档清单。
- `manifest.json`：包内文件、大小、sha256。

## 安装方式

复制整个目录到目标用户的 Hermes skills 目录，例如：

```bash
mkdir -p ~/.hermes/skills/data-science
cp -R sql-query-method-internal ~/.hermes/skills/data-science/
```

新会话中可加载使用。

## 内部分享注意

此包包含内部表结构、字段、业务口径和历史 SQL。只适合分享给有权限访问这些数据资产的数据部门伙伴；不要外发。

包内不包含数据库凭证、ODPS/ClickHouse key、Feishu token 或 Python 连接配置。
