# 🔎 内部数据查询 Skill

这是一个面向 Codex / AI 助手的内部数据查询 skill，用来把“查数据、找字段、写 SQL、复核口径、沉淀知识”这类工作固定成可复用流程。

仓库只保留通用工具和模板，不放实际业务数据、schema KB、历史 SQL、团队知识库、真实 host、账号、密码或导出结果。

## 🧩 能力

- 配置本机只读数据源：Metabase、ClickHouse、ODPS / MaxCompute、MySQL
- 刷新表结构、字段、注释、DDL 等 schema 信息
- 搜索业务仓库或外部提供的 schema index / historical SQL index
- 搜索、读取和运行 Metabase card
- 检查 SQL 只读安全性，拦截 DDL/DML、危险函数、外部 table function、system 表等风险
- 执行只读查询并导出 CSV/XLSX
- 在业务仓库内沉淀查询 brief、SQL draft、review、discovery report 和可复用知识

## 🔐 安全边界

真实查询需要用户准备只读账号：

- Metabase：base URL，以及 API key、session id 或用户名密码。
- ClickHouse：host、port、database、username、password、secure/TLS 配置。
- ODPS / MaxCompute：endpoint、project、access id/access key、tunnel/project 配置。
- MySQL：host、port、database/schema、username、password、SSL/TLS 配置。

凭证只写入用户本机配置，默认路径：

```text
~/.internal-data-query/data-sources.yaml
```

不要把 GitHub token、数据库密码、access key、session id、真实 host、schema 快照或查询导出提交到这个 skill 仓库。

## 📁 业务仓库工作区

安装后在其他业务仓库使用时，默认只创建一个工作目录：

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

- `schema/` 保存从只读数据源刷新出的 `unified_schema_index.json` 和 DDL 快照。
- `knowledge/` 保存经过 capture / review / approval 的团队可复用知识。
- `exports/` 可能包含查询结果，提交前应按团队安全要求处理。

`data-query-work/` 默认不要整体加入业务仓库 `.gitignore`，因为它承载多人协作的过程记录和知识沉淀。若有敏感导出，只忽略具体敏感文件或团队约定的本地子路径。

## 💬 给使用者

把仓库链接或 release zip 发给 Codex / AI 助手安装即可。安装完成后，它应该继续引导你配置只读数据源，并在你确认后刷新 schema / DDL。

常见触发方式：

```text
帮我配置内部数据源账号
帮我刷新这个仓库的数据表结构
帮我查一下数据
写个 SQL
看一下 Metabase 里有没有这个指标
这个页面字段应该接哪张表
验证这个报表口径
```
