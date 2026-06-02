# 🔎 内部数据查询 Skill

这是一个给 AI agent 使用的内部数据查询技能包。它让 agent 能在任意业务仓库中查数据、写只读 SQL、搜索 Metabase、查 schema、复用历史 SQL、验证报表口径，并把可复用经验沉淀为团队知识。

适用场景：

- 查询订单、退款、GMV、现金流、转化、续费、用户关系等业务数据
- 为页面字段、接口字段或报表指标寻找数据来源
- 复核已有 Metabase 卡片、看板和历史 SQL 是否能复用
- 编写并检查 ClickHouse / ODPS / MySQL / Metabase 只读 SQL
- 把经过验证的查询口径沉淀到团队共享知识库

## 🚀 安装

最简单的安装方式是把仓库链接或 release zip 发给正在使用的 AI agent：

```text
帮我安装这个 skill：https://github.com/UnsplashZ/data-query-skill
```

安装完成后，首次真实查询前需要准备只读数据源信息：

- Metabase：base URL，以及 API key、session id 或用户名密码
- ClickHouse：host、port、database、username、password、secure/TLS 配置
- ODPS / MaxCompute：endpoint、project、access id/access key，以及 tunnel/project 配置
- MySQL：host、port、database/schema、username、password、SSL/TLS 配置

这些信息只应配置到本机，默认配置路径是 `~/.internal-data-query/data-sources.yaml`。不要把 GitHub token、数据库密码、access key 或 session id 粘贴进聊天，也不要写入仓库文件。

安装后建议先运行：

```bash
python scripts/post_install_check.py --offline-ok
```

如果本机已有部分数据源配置，补缺失源时不要覆盖整份配置：

```bash
python scripts/setup_connections.py --add-sources odps,mysql --non-interactive
```

状态口径：

- `installed`：skill 包、manifest 和离线校验可用。
- `configured`：本机配置存在，且至少有一个数据源 profile 字段完整、非占位。
- `connected`：真实只读连接 smoke check 通过；默认离线验收会跳过。
- `query_verified`：已有真实只读查询或明确 mock/card 证据，不能由配置解析成功自动推导。

安装或覆盖 skill 后，重启 Codex 以稳定拾取新 skill。

## 🧩 能力

| 能力 | 说明 |
| --- | --- |
| 安装引导 | 校验包体、扫描敏感信息、生成本机连接配置 |
| 数据源配置 | 支持 Metabase、ClickHouse、ODPS / MaxCompute、MySQL 只读连接 |
| schema 搜索 | 搜索打包的 ODPS / ClickHouse schema KB |
| 历史 SQL 搜索 | 查找历史 SQL，作为字段、join 和指标口径证据 |
| Metabase 复用 | 搜索、读取、运行卡片，避免重复写 SQL |
| SQL 安全检查 | 拒绝 DDL/DML、危险函数、外部 table function、system 表等 |
| 查询执行 | 执行只读查询并导出 CSV/XLSX |
| 知识沉淀 | 捕获 candidate、review、approval、冲突检查和同步报告 |
| 离线验证 | 用 fixture 和 mock 覆盖安装、SQL 安全、Metabase、知识库流程 |

## 💬 怎么使用

安装并配置账号后，可以直接对 AI 说：

```text
帮我查一下数据
写个 SQL
看一下 Metabase 里有没有这个指标
这个页面字段应该接哪张表
导出某个时间段的订单/退款/GMV
验证这个报表口径
配置内部数据源账号
```

agent 应先查当前仓库、Metabase、schema KB、历史 SQL 和方法参考，再决定是否新写 SQL。历史 SQL 只能作为证据，不能直接当当前口径。

## 🔐 账号和安全边界

真实查询必须配置只读数据源。需要准备的信息包括：

- Metabase：base URL，以及 API key、session id 或用户名/密码
- ClickHouse：host、port、database、username、password、secure/TLS 配置和只读 profile
- ODPS / MaxCompute：endpoint、project、access id/access key 或团队批准的认证方式，以及 tunnel/project 配置
- MySQL：host、port、database/schema、username、password、SSL/TLS 配置和只读角色

凭证只允许放在使用者本机环境变量、secret manager 或本机配置文件中。不要写进 skill 包、共享 zip、manifest、仓库文档、聊天记录或生成的 SQL。

这个 skill 不会自动做这些事：

- 不会提交、push、pull、merge、创建 PR 或切分支
- 不会写入生产库，不执行 DDL/DML
- 不会把真实凭证打包进 zip
- 不会把本机连接配置同步到仓库
- 不会把历史 SQL 标记为已验证口径，除非重新完成当前验证

## 📁 工作目录

这个 skill 安装一次后，可以在其他业务仓库中使用。默认把当前业务仓库作为任务工作区，并创建：

```text
data-query-work/
├── briefs/
├── reviews/
├── sql-drafts/
├── discovery-reports/
├── requirement-gaps/
├── exports/
└── knowledge/
```

目录语义：

- `briefs/`：需求梳理和业务问题边界
- `sql-drafts/`：SQL 草稿
- `reviews/`：SQL review、结果复核和风险结论
- `discovery-reports/`：schema、Metabase、历史 SQL、仓库证据探索报告
- `requirement-gaps/`：口径不清、字段缺失、权限缺口
- `exports/`：一次性结果导出，默认本机保留
- `knowledge/`：团队复用知识库，保存指标口径、source profile、join contract、golden query 和知识 review 记录

过程文件和知识文件统一使用可排序命名，方便多人共享：

```text
YYYY-MM-DD__domain__topic__artifact-type.ext
```

Markdown 文件首标题建议使用：

```text
# YYYY-MM-DD / domain / topic / artifact type
```

进入共享知识库时先写为 `candidate`，经过 review / promotion 后才成为 `reviewed` 或 `approved`。旧项目里如果已有顶层 `data-query-knowledge/`，新版脚本只把它作为只读兼容来源；新写入都进入 `data-query-work/knowledge/`。

agent 不应默认把整个 `data-query-work/` 加入目标业务仓库的 `.gitignore`。这个目录包含团队可复用知识和可 review 的过程记录；如有敏感导出或本机临时文件，只对具体文件或团队约定的本地子路径做忽略。

## 🧠 旧版用户如何沉淀知识

如果同事已经用旧版数据 skill 查了一段时间，升级后不要把旧 SQL 或聊天结论直接标记为 approved truth。推荐流程：

1. 安装新版 skill，并保留原来的只读数据源配置在本机。
2. 覆盖 skill 包后运行 `python scripts/post_install_check.py --offline-ok`。
3. 用 `python scripts/setup_connections.py --add-sources <sources> --non-interactive` 补缺失源。
4. 重启 Codex。
5. 在目标业务仓库使用 `data-query-work/` 存放过程产物和团队知识。
6. 如果旧项目已有 `data-query-knowledge/`，把它作为只读来源迁到 `data-query-work/knowledge/`。
7. 从旧查询记录、SQL review、结果总结或用户确认中生成 `candidate`。
8. 人工补齐 domain、metric、source、grain、validation evidence。
9. reviewer 复核后提升为 `reviewed`。
10. 有真实查询证据和 approver 后再提升为 `approved`。

原则：旧经验可以加速定位表、字段和指标口径；进入共享知识库时先是 candidate；只有重新完成当前验证、review 和 approval 后，才可以作为团队可复用的 approved knowledge。
