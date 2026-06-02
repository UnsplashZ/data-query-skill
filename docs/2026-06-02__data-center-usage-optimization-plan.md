# 2026-06-02 / data-center usage / internal-data-query optimization plan

## 背景

本轮在 data-center 目录的实际使用暴露出 `internal-data-query` skill 的几类缺口：定向刷新 schema、按表抽样并脱敏、knowledge promotion 的目录迁移、敏感风险扫描和依赖检查都还停留在临时脚本或局部规则层面。

当前主流程方向是正确的：先配置只读数据源，再刷新 schema，再基于 schema 和已有知识查数、写 SQL、验证结果、沉淀知识。但要减少下一次类似任务中的手工 glue code，需要把这轮临时能力固化为 skill 包内的通用脚本和共享模块。

## 目标

- 支持按 table list 定向刷新 schema，不再只能按 engine/profile/limit 扫描。
- 支持从 schema index 批量抽取每表最新样例，并在落盘前完成统一脱敏。
- 将脱敏规则产品化为共享模块，覆盖字段名、值形态、响应体和 residual scan。
- 修复 knowledge promotion 只改 frontmatter、不移动文件的问题。
- 收敛 knowledge 目录结构，避免默认铺大量空目录。
- 改善依赖检查和跨平台兼容，确保 Windows、Linux、macOS 都能运行核心脚本。
- 增强 schema 敏感字段风险报告、批量修正 approve 流程、discovery report 和 ClickHouse 旧版本 SQL 规则。

## 非目标

- 不把真实业务 schema、历史 SQL、查询导出、团队知识或凭证写入 skill 包。
- 不引入 MCP 或后台服务形态，本轮仍保持 Python CLI 脚本模式。
- 不做复杂平台化 UI。
- 不改变只读查询安全边界。
- 不默认把 `data-query-work/` 整体加入业务仓库 `.gitignore`。

## 总体设计

本轮按四条主线改造：

1. Schema discovery：增强 `scripts/refresh_schema.py`，支持 scoped refresh 和 discovery report。
2. Sampling and masking：新增 `scripts/sample_tables.py` 和 `scripts/lib_masking.py`，样例抽取必须经过统一脱敏。
3. Knowledge lifecycle：调整 `scripts/lib_workspace.py`、`scripts/promote_query_knowledge.py`、search/validate/report 脚本，形成稳定目录迁移合同。
4. Install and validation：增强 `post_install_check.py`、`discover_data_sources.py`、`scan_sensitive_info.py`、`query_static_check.py`，提升依赖、风险和 SQL 方言检查质量。

所有新增或修改脚本都必须保持 Windows/Linux/macOS 兼容：

- 使用 `pathlib.Path` 处理路径，不手写 `/` 或 `\`。
- CLI 参数支持带空格路径。
- 不依赖 shell-specific 命令、管道或 `bash` 特性。
- 输出文件使用 UTF-8，CSV 使用 `utf-8-sig` 时需明确。
- 临时文件通过 `tempfile`，不得写死 `/tmp`。
- 换行读取使用 Python 通用文本模式，输出尽量避免平台相关换行差异。
- 测试命令在三类系统上都应可执行；无法实测 Windows 时，至少增加路径解析和文本解析单元用例覆盖。

## P0 必改

### 1. Scoped schema refresh

当前问题：

- `refresh_schema.py` 只能按 engine/profile/limit 拉取。
- 无法按 xlsx 或 table list 定向刷新。
- 本轮只能临时写脚本处理指定表。

目标行为：

```bash
python scripts/refresh_schema.py \
  --engine clickhouse \
  --profile default \
  --table-list ck.xlsx \
  --root <target-repo>

python scripts/refresh_schema.py \
  --engine clickhouse \
  --profile default \
  --table-list tables.txt \
  --default-database dm \
  --root <target-repo>
```

输入支持：

- `.txt`：每行一个表名，允许空行和 `#` 注释。
- `.csv`：默认读取第一列；可选 `--table-column` 指定列名。
- `.xlsx`：默认读取第一个 sheet 的第一列；可选 `--sheet`、`--table-column`。
- 表名格式支持 `table`、`db.table`、`` `db`.`table` ``。
- 不带 database 时使用 `--default-database`；未传则使用 profile config 中的 database/project/schema。

输出要求：

- 更新 `data-query-work/schema/unified_schema_index.json`。
- 写入 DDL 到原有 `data-query-work/schema/ddl/<engine>/<profile>/<database>/<table>.sql`。
- 生成 discovery report：
  - `data-query-work/discovery-reports/YYYY-MM-DD__schema-refresh__<engine>__report.md`
  - 可选 JSON：`data-query-work/discovery-reports/YYYY-MM-DD__schema-refresh__<engine>__report.json`

report 必须包含：

- requested：用户请求的原始表名和解析后的 canonical 表名。
- found：成功刷新的表。
- missing：未找到的表。
- duplicate_aliases：多个输入指向同一 canonical 表的重复项。
- skipped：profile 缺字段、占位配置、引擎不支持等。
- failed：实际连接或 DDL 拉取失败。
- output：schema index 和 DDL 输出路径。

实现要点：

- 新增 table list parser，建议放在 `refresh_schema.py` 内部或 `lib_table_list.py`。
- ClickHouse/MySQL/ODPS 的 metadata 查询应支持 `IN` 条件或逐表查询，避免先拉全库再过滤。
- Metabase 可先支持按 table name 过滤 metadata；如果 API 无法高效定向，report 中标注 `filtered_after_metadata_fetch`。
- `--limit-tables` 在有 `--table-list` 时不作为主限制，只用于保护 Metabase 这类无法完全定向的来源。
- `--replace` 语义保持不变；默认 merge 指定表到现有 index。

验收：

- txt/csv/xlsx 三类 table list 都能解析。
- `db.table` 和默认 database 都能解析。
- missing 和 duplicate aliases 可在 dry fixture 中稳定复现。
- 旧的无 `--table-list` 全量刷新路径不回归。

### 2. Sample extraction script

当前问题：

- 缺少内置样例抽取脚本。
- “每表两条最新数据 + 脱敏”依赖临时脚本。

目标命令：

```bash
python scripts/sample_tables.py \
  --engine clickhouse \
  --profile default \
  --from-schema-index data-query-work/schema/unified_schema_index.json \
  --rows 2 \
  --root <target-repo>
```

核心行为：

- 从 schema index 读取目标表。
- 支持 `--table-list` 再次缩小抽样范围。
- 每表最多抽取 `--rows` 条。
- 原始行只允许驻留内存，禁止落盘。
- 输出 masked JSONL、status CSV、summary report。

输出文件：

```text
data-query-work/exports/YYYY-MM-DD__sample-tables__<engine>__masked.jsonl
data-query-work/exports/YYYY-MM-DD__sample-tables__<engine>__status.csv
data-query-work/discovery-reports/YYYY-MM-DD__sample-tables__<engine>__report.md
```

ClickHouse 规则：

- `drh_` 前缀表自动使用 `FINAL`。
- 如果存在 `_sign` 字段，自动增加 `_sign > 0`。
- `FINAL` 后避免直接 alias，兼容旧版本 ClickHouse。
- 默认不采样 `local` 表，除非显式传 `--include-local-tables`。

latest 字段推断：

优先级建议：

1. 精确字段：`updated_at`、`update_time`、`modified_at`、`modify_time`。
2. 业务时间：`created_at`、`create_time`、`event_time`、`finish_time`、`pay_time`。
3. 分区字段：`dt`、`date`、`biz_date`、`pt`。
4. 主键或递增字段：`id`、`version`，仅作为低置信 fallback。

status CSV 字段：

- engine
- profile
- database
- table
- status：`sampled`、`missing_latest_column`、`limit_only`、`query_failed`、`masked_residual_failed`、`skipped`
- rows_requested
- rows_returned
- latest_column
- latest_reason
- where_clause
- order_by
- clickhouse_rules_applied
- output_file
- error

验收：

- schema index fixture 可离线生成 SQL 和 status。
- 有 latest 字段时按 latest 排序。
- 无 latest 字段时仍可 `LIMIT 2`，但 status 必须标注。
- `drh_` 表 SQL 包含 `FINAL`，有 `_sign` 时包含 `_sign > 0`。
- 所有输出均为脱敏后内容。

### 3. Masking as productized module

当前问题：

- 字段名脱敏、值形态脱敏、`callback_response` 二次脱敏都是临时逻辑。
- `scan_sensitive_info.py` 和 `capture_query_knowledge.py` 各有局部正则，缺少统一规则。

新增模块：

```text
scripts/lib_masking.py
```

字段名规则：

- phone、mobile、tel
- email
- token、access_token、refresh_token、api_key、session、cookie
- password、passwd、pwd
- secret、app_secret、access_key、access_key_secret
- openid、unionid、user_id、id_card、identity
- address、receiver_address、shipping_address
- callback_response、response_body、raw_response、payload

值形态规则：

- 中国手机号。
- 邮箱。
- JWT。
- 长 hex/base64/token-like 字符串。
- URL basic auth。
- 私钥块。
- access key / secret assignment。
- 过长文本响应体，尤其是疑似 JSON/XML/HTML 的 response body。

API 设计：

```python
mask_value(field_name: str, value: Any) -> Any
mask_row(row: dict[str, Any]) -> dict[str, Any]
mask_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]
residual_scan_text(text: str) -> list[Finding]
residual_scan_file(path: Path) -> list[Finding]
```

落盘规则：

- sample extraction、knowledge capture、result summary 写文件前必须调用 residual scan。
- 原始查询结果不得落盘。
- residual scan 命中高风险时，默认阻断写入。
- 可通过 `--allow-risk-report-only` 将敏感字段名风险降为 report warning，但 credential-like 值不得降级。

验收：

- `callback_response` 中嵌套 JSON 字符串能二次解析并脱敏。
- 字段名命中但值为空时仍在 report 中记录字段风险。
- 值形态命中时不依赖字段名也能脱敏。
- residual scan 能复用同一套规则。

### 4. Knowledge promotion should move files

当前问题：

- `promote_query_knowledge.py` 只改 frontmatter 和 promotion log。
- approved 文件仍留在 candidates 目录，目录语义失真。

修正后的目录合同：

```text
data-query-work/knowledge/
├── candidates/
├── reviewed/
├── approved/
├── deprecated/        # 首次 deprecated 时再创建
├── OWNERS.yaml
└── promotion-log.md
```

注意：candidate 只进入 `candidates/`，不再使用 `candidates/observed`、`candidates/query-verified`、`candidates/user-assertions` 等默认子目录。maturity 保留在 frontmatter 中表达，不再通过目录表达。

promotion 行为：

- `candidate -> reviewed`：移动到 `reviewed/`。
- `candidate/reviewed -> approved`：移动到 `approved/`。
- 任意状态 -> `deprecated`：移动到 `deprecated/`，如目录不存在则创建。
- 文件名中的状态后缀同步替换：
  - `__candidate-<id>.md` 或 `__candidate.md` -> `__reviewed-<id>.md` / `__approved-<id>.md`
  - 无状态后缀时追加 `__<status>-<id>.md`
- `id` 保持不变，search/validate/report 都以 `id` 为稳定标识。

兼容策略：

- search/validate/report 继续递归扫描整个 knowledge root，兼容旧目录。
- promote 新写入时使用新目录。
- 可提供一次性迁移命令：

```bash
python scripts/migrate_query_knowledge_layout.py --root <target-repo> --dry-run
python scripts/migrate_query_knowledge_layout.py --root <target-repo>
```

验收：

- promote 后旧路径不存在，新路径存在。
- promotion-log 正确记录 from/to。
- search by id、search by keyword 仍能命中。
- validate 不因路径迁移误判 duplicate id。
- dry-run 输出 planned move，不改文件。

## P1 应改

### 5. Dependency checks

当前问题：

- 使用 bundled Python 时可能缺 `PyYAML`，导致 `discover_data_sources.py` 在读取 config 前失败。
- post-install 报告不够明确。

改造：

- 新增 `scripts/lib_dependencies.py` 或在 `post_install_check.py` 中集中实现 dependency probing。
- 输出当前 Python 路径、版本、平台、缺失模块和推荐安装命令。
- `discover_data_sources.py` 在缺 PyYAML 时仍能输出：
  - installed driver 状态。
  - config path 是否存在。
  - schema index / historical SQL / knowledge 是否存在。
  - 缺 PyYAML 导致 profile parsing skipped。

示例输出：

```text
python: /path/to/python
version: 3.11.x
platform: macOS
missing_modules:
- yaml: install with python -m pip install -r requirements.txt
recommended_python: use the same Python that runs Codex skill scripts
```

验收：

- 无 PyYAML 时 `post_install_check.py --offline-ok` 不崩溃，能给出明确 next action。
- 有 PyYAML 时行为保持不变。
- Windows/Linux/macOS 路径展示正常。

### 6. Schema sensitive field risk report

当前问题：

- `scan_sensitive_info.py` 主要扫描高置信凭证值。
- schema/DDL 中出现 `token/password/app_secret` 字段名时，应作为敏感字段名风险报告，而不是当成凭证泄露。

改造：

- 扩展 `scan_sensitive_info.py` 输出两个分组：
  - `secret_leak_findings`：高置信凭证值，默认 return 1。
  - `sensitive_field_name_risks`：字段名风险，默认 warning。
- 增加 CLI：

```bash
python scripts/scan_sensitive_info.py . --include-field-name-risks
python scripts/scan_sensitive_info.py . --fail-on-sensitive-field-name
```

验收：

- DDL 中 `app_secret String` 会出现在 field risk。
- `password = <real long secret value>` 这类真实值仍作为 secret leak；计划文档和 fixture 不放真实形态字面量。
- field risk 默认不阻断 packaging，除非显式 fail flag。

### 7. Knowledge directory structure convergence

当前问题：

- `lib_workspace.py` 默认创建大量空目录，容易误导使用者。

新默认结构：

```text
data-query-work/knowledge/
├── candidates/
├── reviewed/
├── approved/
├── OWNERS.yaml
└── promotion-log.md
```

规则：

- 空目录不主动创建，除 `candidates/reviewed/approved` 三个主目录外。
- `deprecated/` 只有首次 deprecated 时创建。
- 旧模板中建议路径改为新目录。
- maturity、source type、knowledge type 都放 frontmatter，不再通过多层目录表达。

验收：

- `capture_query_knowledge.py` 默认写入 `knowledge/candidates/`。
- 新业务仓库初始化不再出现 `metrics/sources/joins/golden-queries/...` 空目录。
- 旧目录存在时 search/validate 仍兼容。

### 8. Batch patch and approve flow

当前问题：

- 用户修正“某表弃用、某口径改掉、其他 approve”时，需要手工 patch 多个知识文件、再逐个 promote、再搜索验证。

新增脚本建议：

```text
scripts/patch_query_knowledge.py
```

支持：

```bash
python scripts/patch_query_knowledge.py \
  --root <target-repo> \
  --patch-file corrections.yaml \
  --dry-run

python scripts/patch_query_knowledge.py \
  --root <target-repo> \
  --patch-file corrections.yaml
```

patch file 示例：

```yaml
deprecated:
  - id: kcap-old-table
    reason: table no longer used
    superseded_by: kcap-new-table
updates:
  - id: kcap-metric-a
    set:
      confidence: high
      sync_notes:
        - corrected by user review
promote:
  - id: kcap-metric-a
    to: approved
    reviewer: zheng
    approver: zheng
    evidence:
      - data-query-work/reviews/2026-06-02__metric-a__review.md
verify_absent_keywords:
  - old_table_name
```

验收：

- dry-run 能输出将修改哪些文件、移动到哪里、哪些关键词会验证。
- 执行后自动调用 validate。
- 对 `verify_absent_keywords`，默认搜索 active statuses，不包含 deprecated。
- deprecated 仍可通过 `--include-deprecated` 搜到。

## P2 可增强

### 9. Automatic discovery reports

schema refresh 和 sample extraction 都应自动生成 report。report 内容：

- 本次范围。
- 输入 table list 解析结果。
- 使用的 profile 和 engine。
- 输出文件。
- missing/failed/skipped 表。
- 敏感字段名风险。
- 脱敏 residual scan 结果。
- 验证命令。

### 10. Explain latest column inference

sample status 中要解释：

- 使用哪个排序字段。
- 为什么选择它。
- 是否只是 `LIMIT N`。
- 字段置信度：`high`、`medium`、`low`、`none`。

### 11. ClickHouse old-version SQL rules

落点建议是 `query_static_check.py`：

- `FINAL` 后避免直接 alias。
- 日期为 String 时提醒 `toDate/parseDateTimeBestEffort` 风险。
- 复杂 CTE alias 风险。
- 默认不使用 local 表。
- 旧版本 ClickHouse 对部分函数、别名、WITH 语义不稳定时给 warning。

验收：

- 规则以 warning 为主，不阻断只读 SQL。
- 每条 warning 有明确 hint。
- sample_tables 生成 SQL 时遵守这些规则，减少 warning。

## 跨平台兼容要求

所有新增脚本和修改后的旧脚本必须满足：

- Python 3.10+。
- Windows、Linux、macOS 均可运行。
- 使用 `pathlib.Path` 和 `argparse`。
- 不依赖 shell glob 展开；需要多文件输入时支持重复参数或显式列表。
- 不依赖系统 `date`、`sed`、`awk`、`grep`、`mktemp`。
- 不假设当前工作目录为脚本目录；所有脚本都支持 `--root`。
- 对 Excel 依赖 `openpyxl`，缺失时给出明确错误，并允许 txt/csv 路径继续工作。
- 文件写入使用原子写入或先写临时文件再替换，避免半写入。
- Windows 下文件移动需处理目标已存在、大小写不同名、路径长度和非法字符。
- 文件名 slug 只使用 ASCII 安全集合：`A-Za-z0-9_.-`。

建议增加一个跨平台 smoke fixture：

```text
tests/fixtures/
├── table-list/
│   ├── tables.txt
│   ├── tables.csv
│   └── tables.xlsx
├── schema-index/
│   └── unified_schema_index.json
└── knowledge/
    └── candidates/
```

## 推荐实施顺序

1. 新增 `lib_masking.py`，统一字段名、值形态、response body 和 residual scan。
2. 改造 `refresh_schema.py`，补 `--table-list`、默认 database 解析和 discovery report。
3. 新增 `sample_tables.py`，复用 `lib_masking.py`，输出 masked JSONL/status CSV/report。
4. 收敛 `lib_workspace.py` 默认 knowledge 目录，并更新 capture/search/validate/report 兼容逻辑。
5. 改造 `promote_query_knowledge.py`，实现 status 目录迁移和文件名状态同步。
6. 新增或扩展 batch patch/promotion flow。
7. 增强 post-install/discover 依赖检查。
8. 扩展 sensitive scan 的字段名风险报告。
9. 扩展 ClickHouse old-version warning。
10. 更新 `SKILL.md`、README、templates 和 references。
11. 补测试和 packaging 验证。

## 验证矩阵

最低验证命令：

```bash
python -m py_compile scripts/*.py
python scripts/scan_sensitive_info.py .
python scripts/package_skill.py --json
python scripts/post_install_check.py --offline-ok
```

新增专项验证：

```bash
python scripts/refresh_schema.py --engine clickhouse --profile default --table-list tests/fixtures/table-list/tables.txt --root tests/fixtures/workspace --dry-run
python scripts/refresh_schema.py --engine clickhouse --profile default --table-list tests/fixtures/table-list/tables.xlsx --root tests/fixtures/workspace --dry-run
python scripts/sample_tables.py --engine clickhouse --from-schema-index tests/fixtures/schema-index/unified_schema_index.json --rows 2 --root tests/fixtures/workspace --dry-run
python scripts/promote_query_knowledge.py <id> --to approved --reviewer test --approver test --evidence tests/fixtures/review.md --root tests/fixtures/workspace --dry-run
python scripts/validate_query_knowledge.py --root tests/fixtures/workspace
```

跨平台验证：

- macOS：本机执行完整 smoke。
- Linux：CI 执行 py_compile、sensitive scan、package、offline post-install、fixture tests。
- Windows：CI 至少执行 py_compile、table list parser、masking、knowledge path migration dry-run。

## 交付清单

- `scripts/lib_masking.py`
- `scripts/sample_tables.py`
- `scripts/refresh_schema.py` scoped refresh 改造
- `scripts/promote_query_knowledge.py` 文件迁移改造
- `scripts/lib_workspace.py` knowledge skeleton 收敛
- `scripts/patch_query_knowledge.py` 或等价批量 patch/promote 能力
- `scripts/post_install_check.py` dependency report 增强
- `scripts/discover_data_sources.py` 无 PyYAML 降级
- `scripts/scan_sensitive_info.py` sensitive field risk report
- `scripts/query_static_check.py` ClickHouse 旧版本 warning
- `SKILL.md`、README、templates、references 同步更新
- 跨平台 fixture 和测试

## 风险与处理

- 旧 knowledge 目录已存在：search/validate 递归兼容；新增 migrate dry-run。
- `candidate -> candidates/` 目录变更影响旧模板：模板和 SKILL.md 同步改，旧目录不主动删除。
- xlsx 依赖缺失：txt/csv 不应受影响；xlsx 路径给明确依赖提示。
- latest 字段误判：status 中必须输出 reason 和 confidence，低置信 fallback 不标为 latest verified。
- 脱敏漏扫：写文件前 residual scan 阻断，高风险值不得通过 allow flag 降级。
- ClickHouse 旧版本差异：生成 SQL 优先保守；static check 先 warning，不默认阻断。

## 完成标准

当以下条件满足时，本轮优化可认为完成：

- 指定 table list 可以完成 schema refresh，并输出 requested/found/missing/duplicate aliases。
- 可以从 schema index 对指定表抽取样例，输出 masked jsonl/status csv/report。
- 原始样例数据不会落盘。
- 字段名和值形态脱敏统一复用，`callback_response` 等响应体能二次脱敏。
- knowledge promote 会移动文件到 `candidates/`、`reviewed/`、`approved/`、`deprecated/` 中的目标目录，并保持 id 稳定。
- 默认 knowledge skeleton 不再创建大量空目录。
- 缺 PyYAML 或其他依赖时，post-install/discover 能明确报告当前 Python、缺失模块和推荐安装方式。
- schema/DDL 中敏感字段名作为风险报告，而不是混同为凭证泄露。
- 批量用户修正、promote、deprecated 清理和旧关键词验证有命令化流程。
- Windows/Linux/macOS 兼容要求写入测试或 CI 验证。
