# Internal Data Query Skill

这是一个给用户和 AI 助手使用的通用内部数据查询 skill。拿到 zip 或链接后，它可以帮助 AI 在任意仓库里查数据、写只读 SQL、搜索 Metabase 卡片、找字段、验证报表口径，并把查询过程产物保存在本机工作目录。

## 安装后必须做什么

AI 助手安装或解压后不能只回复“安装完成”。必须继续执行这条路径：

```text
收到链接/zip
-> 解压到 AI 工具可读取的 skills 目录或用户指定目录
-> 确认存在 SKILL.md、manifest.json、scripts/setup_connections.py
-> 运行 manifest 校验和敏感信息扫描
-> 提示用户配置哪些只读数据源
-> 生成本机 data-sources.yaml
-> 运行 smoke check
-> 告诉用户后续可直接用自然语言触发查数
```

推荐安装后先运行：

```bash
python scripts/validate_manifest.py
python scripts/scan_sensitive_info.py
python scripts/setup_connections.py
```

如果没有交互式终端，用本机路径生成占位配置，再让用户在本机补齐：

```bash
python scripts/setup_connections.py --non-interactive --output ~/.internal-data-query/data-sources.yaml --overwrite
```

## 账号配置

真实查询必须配置只读数据源。默认配置文件是：

```text
~/.internal-data-query/data-sources.yaml
```

脚本会尽量把权限设置为 `0600`。查询脚本会自动读取该路径，也可以用 `INTERNAL_DATA_QUERY_CONFIG` 或 `--config <path>` 指定其他本机配置。

可配置的数据源：

- Metabase：base URL，以及 API key、session id 或用户名/密码。
- ClickHouse：host、port、database、username、password、secure/TLS 配置和只读 profile。
- ODPS / MaxCompute：endpoint、project、access id/access key 或团队批准的认证方式，以及必要 tunnel/project 配置。
- MySQL 或其他 SQL 引擎：host、port、database/schema、username、password、SSL/TLS 配置和只读角色。

凭证只允许放在使用者本机环境变量、secret manager 或本机配置文件中。不要写进 skill 包、共享 zip、manifest、仓库文档、聊天记录或生成的 SQL。

## 状态确认

安装和配置后，AI 助手应输出状态报告：

- 包是否存在：`SKILL.md`、`manifest.json`、`scripts/setup_connections.py`。
- manifest 校验是否已运行。
- 敏感信息扫描是否已运行。
- 本机配置路径是什么。
- 已配置哪些数据源。
- 配置文件权限是否为 `0600`。
- 已运行哪些 smoke check。
- 真实查询前还缺什么。

可用的无敏感 smoke check 示例：

```bash
python scripts/setup_connections.py --help
python scripts/check_connections.py --config ~/.internal-data-query/data-sources.yaml --offline-ok
python scripts/discover_data_sources.py --config ~/.internal-data-query/data-sources.yaml
python scripts/search_schema.py refund --limit 3
python scripts/search_old_sql.py 退款 --limit 3
python scripts/run_query.py --help
python scripts/metabase_search.py --help
python scripts/metabase_search.py refund --mock-file evals/fixtures/metabase-mock/search.json --json
python scripts/metabase_get_card.py 321 --mock-file evals/fixtures/metabase-mock/card-321.json --json
```

`setup_connections.py --non-interactive` 生成的是占位配置，只能用于 `check_connections.py --offline-ok` 和 `discover_data_sources.py` 这类解析/发现检查。不要把占位 Metabase URL 当作真实查询 smoke；真实 `metabase_search.py`、`metabase_run_card.py` 或 `run_query.py --engine metabase` 需要先在本机补齐只读连接。

## 后续怎么触发

安装并配置后，用户可以直接对 AI 说：

- “帮我查一下数据”
- “写个 SQL”
- “看一下 Metabase 里有没有这个指标”
- “这个页面字段应该接哪张表”
- “导出某个时间段的订单/退款/GMV”
- “验证这个报表口径”
- “配置内部数据源账号”

AI 应先查当前仓库、Metabase、schema KB、历史 SQL 和方法参考，再决定是否新写 SQL。历史 SQL 只能当证据，不能直接当当前口径。

## 不会自动做的事

- 不会自动提交 git、push、pull、merge、创建 PR 或切分支。
- 不会自动写入生产库，不会执行 DDL/DML，不会 grant/drop/truncate/insert/update/delete。
- 不会把真实凭证打包进 zip。
- 不会把本机 `data-sources.yaml` 同步到仓库。
- 不会把历史 SQL 标记为已验证口径，除非重新完成当前验证。

## 多人协作边界

可以随包或仓库同步：

- `SKILL.md`
- `README.md`
- `scripts/`
- `templates/`
- `references/`
- `manifest.json`

必须留在个人本机：

- `~/.internal-data-query/data-sources.yaml`
- `.env.local`
- `local/data-sources.yaml`
- 任何包含真实 host、token、password、access key、session id 的文件

安装到 AI 工具后，在其他仓库内工作时，默认把该仓库的当前工作目录当作任务工作区，并在其中创建本地过程目录：

```text
data-query-work/
├── briefs/
├── reviews/
├── sql-drafts/
├── discovery-reports/
├── requirement-gaps/
└── exports/
```

这个目录用于个人本地过程产物、SQL 草稿、review、discovery report 和导出结果；默认不作为多人共享真源。多人协作和信息同步应把稳定、可复用、已验证的口径沉淀为 `data-query-knowledge/` candidate，再经过 review / promotion 后进入共享仓库。真实凭证、原始导出、本机配置和临时 SQL 不进入共享仓库。

只有执行真实查询或导出 XLSX 时才需要安装依赖：

```bash
python -m pip install -r requirements.txt
```
