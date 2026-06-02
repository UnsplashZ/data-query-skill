# data-query-work 单一工作空间改造方案

## 背景

当前 skill 在目标业务仓库内使用时，会形成两个顶层目录：

- `data-query-work/`：过程文件目录，保存 query brief、SQL 草稿、review、探索报告、缺口记录和导出结果。
- `data-query-knowledge/`：团队复用知识库，保存 candidate、metric、source、join、golden query、review、promotion log 等。

这个设计会让用户误以为“过程产物”和“知识沉淀”是两套独立系统。实际使用时，二者都属于该 skill 在目标业务仓库里的工作空间，只是生命周期和共享等级不同。因此应收敛成一个顶层目录。

## 目标

在任意业务仓库使用该 skill 时，只额外创建一个顶层目录：

```text
data-query-work/
```

所有过程文件和知识库都在这个目录内沉淀。`data-query-work/` 成为该 skill 在目标业务仓库内的唯一 workspace。

## 目标目录结构

```text
data-query-work/
├── briefs/
├── reviews/
├── sql-drafts/
├── discovery-reports/
├── requirement-gaps/
├── exports/
└── knowledge/
    ├── manifest.yaml
    ├── OWNERS.yaml
    ├── promotion-log.md
    ├── candidates/
    │   ├── observations/
    │   ├── query-verified/
    │   ├── reusable-patterns/
    │   └── user-assertions/
    ├── metrics/
    ├── sources/
    ├── joins/
    ├── golden-queries/
    ├── semantic-memory/
    ├── review-records/
    └── deprecated/
```

### 连接配置边界

`config/` 不属于本轮默认工作空间结构。连接配置包含 host、账号、token、password、access key 等敏感信息，不应作为团队共享目录展示。

本轮要求：

- 默认连接配置仍是 `~/.internal-data-query/data-sources.yaml`。
- 继续支持 `INTERNAL_DATA_QUERY_CONFIG` 和显式 `--config <path>`。
- 配置读取顺序应把 `~/.internal-data-query/data-sources.yaml` 放在普通本机默认位，`data-query-work/config/data-sources.yaml` 只能排在 local-only 兼容位。
- 不在 README、SKILL 或默认目录树中展示 `data-query-work/config/`。
- 如当前脚本保留 `data-query-work/config/data-sources.yaml` 兼容读取，只能作为 local-only fallback，不得由新流程自动创建，不得进入团队共享知识沉淀。

## 目录语义

### 过程文件

- `briefs/`：需求梳理、业务问题、范围、候选数据源、假设。
- `sql-drafts/`：查询草稿，默认未验证或部分验证。
- `reviews/`：SQL review、结果复核、风险结论。它只表示一次查询任务的过程复核。
- `discovery-reports/`：schema、Metabase、历史 SQL、当前仓库证据探索报告。
- `requirement-gaps/`：口径不清、字段缺失、权限缺口、数据源缺失。
- `exports/`：一次性结果导出，默认本地保留，不作为团队知识真源。

### 知识库

- `knowledge/candidates/`：所有自动或半自动捕获的候选知识，不能直接当 approved truth。
- `knowledge/metrics/`：稳定指标定义。
- `knowledge/sources/`：表、Metabase card、数据源 profile。
- `knowledge/joins/`：join key、grain、cardinality、膨胀风险。
- `knowledge/golden-queries/`：已复核的可复用 SQL。
- `knowledge/semantic-memory/`：业务概念和语义层说明。
- `knowledge/review-records/`：知识条目的 review 记录，避免与过程目录 `reviews/` 混淆。
- `knowledge/deprecated/`：废弃或过期知识。
- `knowledge/promotion-log.md`：candidate -> reviewed -> approved -> deprecated 的变更日志。

## 文件命名和标题规范

为了方便多人共享和检索，过程文件生成时应使用稳定、可读、可排序的文件名和标题。

### 文件名格式

建议统一为：

```text
YYYY-MM-DD__domain__topic__artifact-type.ext
```

示例：

```text
data-query-work/briefs/2026-06-02__refund__monthly-rate__brief.md
data-query-work/sql-drafts/2026-06-02__refund__monthly-rate__draft.sql
data-query-work/reviews/2026-06-02__refund__monthly-rate__sql-review.md
data-query-work/discovery-reports/2026-06-02__refund__metabase-source-scan__discovery.md
data-query-work/exports/2026-06-02__refund__monthly-rate__sample.csv
data-query-work/knowledge/candidates/query-verified/2026-06-02__refund__monthly-rate__candidate.md
data-query-work/knowledge/review-records/2026-06-02__refund__monthly-rate__knowledge-review.md
```

规则：

- 日期使用业务操作日期，格式 `YYYY-MM-DD`。
- `domain` 使用稳定英文短词，例如 `refund`、`gmv`、`cashflow`、`handover`、`renewal`。
- `topic` 使用短横线英文，避免空格和中文标点。
- `artifact-type` 明确文件类型，例如 `brief`、`draft`、`sql-review`、`discovery`、`candidate`。

### Markdown 标题格式

Markdown 文件首个标题建议统一为：

```text
# YYYY-MM-DD / domain / topic / artifact type
```

示例：

```text
# 2026-06-02 / refund / monthly-rate / query brief
```

正文顶部应保留统一元信息：

```text
- Status:
- Owner:
- Source:
- Related files:
- Validation:
- Risk:
```

## 需要改动的范围

### 文档

- `README.md`
  - 将工作目录说明改为单一 `data-query-work/`。
  - 删除顶层 `data-query-knowledge/` 作为目标业务仓库独立目录的描述。
  - 说明知识沉淀路径为 `data-query-work/knowledge/`。

- `SKILL.md`
  - Default Output Directory 改为单一 workspace。
  - 所有知识沉淀指向 `data-query-work/knowledge/`。
  - 增加过程文件命名和标题规范。

- `references/bundled-assets.md`
  - 更新默认目录示例。

- `references/sql-query-method-overlay.md`
  - 更新保存路径和知识库路径。

### 脚本

需要把默认知识根从 `data-query-knowledge` 改为 `data-query-work/knowledge`：

- `scripts/capture_query_knowledge.py`
- `scripts/validate_query_knowledge.py`
- `scripts/search_query_knowledge.py`
- `scripts/report_query_knowledge_sync.py`
- `scripts/promote_query_knowledge.py`
- `scripts/migrate_query_knowledge.py`
- `scripts/discover_data_sources.py`
- `scripts/suggest_knowledge_capture.py` 中的提示文案

建议新增共享常量，避免各脚本各自硬编码：

```text
WORKSPACE_DIR = "data-query-work"
KNOWLEDGE_DIR = "knowledge"
DEFAULT_KNOWLEDGE_ROOT = "data-query-work/knowledge"
```

共享路径解析必须把读取和写入分开：

- read：优先 `data-query-work/knowledge/`；旧 `data-query-knowledge/` 只作为 read-only compatibility source。
- write：只允许 `data-query-work/knowledge/`；如果旧目录存在，只输出迁移提示，不写回旧目录。
- root 本身是 knowledge root 时可读取；如果 root 是旧 `data-query-knowledge/`，非 dry-run 写操作必须失败。
- 双路径同时存在时读新路径，并提示旧路径需要迁移。

`capture`、`promote`、`migrate` 等写入口不得复用会回落到旧目录的 read resolver。

### manifest / package

- `manifest.json` 不再声明包内顶层 `data-query-knowledge/*` 为默认资产。
- 包内默认知识骨架迁到模板资产，安装后或首次写入时初始化到目标仓库的 `data-query-work/knowledge/`。
- release zip 不得包含 `.github/`、`.DS_Store`、`AGENTS.md`、`dist/` 或顶层旧知识目录。
- manifest metadata 中的知识路径必须指向 `data-query-work/knowledge/`。

### 模板

需要更新模板中的默认路径和标题规范：

- `templates/query-brief.md`
- `templates/sql-review.md`
- `templates/result-summary.md`
- `templates/feature-data-dependency.md`
- `templates/query-knowledge/*.md`
  - 知识 review 模板路径改为 `data-query-work/knowledge/review-records/` 语义。

### fixtures / eval

当前 eval fixture 使用 `evals/fixtures/data-query-knowledge`。需要迁移为：

```text
evals/fixtures/data-query-work/knowledge/
```

并更新：

- `scripts/eval_skill_pack.py`
- expected 输出中的路径断言
- `evals/expected/eval-skill-pack.expected.json`

## 兼容策略

为了不破坏旧项目，建议保留一版兼容读取：

1. 默认新路径：`data-query-work/knowledge/`
2. 兼容旧路径：`data-query-knowledge/`
3. 如果两个路径同时存在：
   - 默认优先新路径。
   - 输出 warning，提示迁移旧路径。
   - 不自动合并，避免覆盖用户知识。
4. 旧路径只允许读取、搜索、校验和迁移；任何新 capture/promote/migrate 写入默认都必须进入 `data-query-work/knowledge/`。
5. 旧路径不允许原地 promote 或非 dry-run in-place migrate。迁移流程应先复制到 `data-query-work/knowledge/`，再在新路径完成校验和提升。

迁移可以提供脚本或文档命令：

```text
data-query-knowledge/ -> data-query-work/knowledge/
```

迁移后运行知识库校验和同步报告。

## 验收标准

- 新业务仓库只需要一个顶层目录：`data-query-work/`。
- 所有过程文件和知识库都在 `data-query-work/` 下。
- 默认知识写入路径为 `data-query-work/knowledge/`。
- 旧路径 `data-query-knowledge/` 仍可读，但只作为兼容/迁移来源，并提示迁移。
- 新版本不得自动创建顶层 `data-query-knowledge/`。
- `run_query.py` 和 `metabase_run_card.py` 仍默认导出到 `data-query-work/exports/`。
- query knowledge 的 capture/search/validate/report/promote 全部通过新路径工作。
- README、SKILL、references、templates 不再把 `data-query-knowledge/` 描述为目标业务仓库顶层目录。
- README、SKILL 和默认目录树不展示 `data-query-work/config/`。
- 不默认修改目标业务仓库 `.gitignore`，尤其不得默认加入整目录 `data-query-work/`；如需保护敏感导出，只能按团队约定忽略具体本地文件或 local-only 子路径。
- eval 全部通过。

## 非目标

- 不把真实连接配置作为团队共享内容。
- 不把 `exports/` 中的原始导出结果提升为知识真源。
- 不自动提交、push 或迁移用户业务仓库文件。
- 不改变 `~/.internal-data-query/data-sources.yaml` 作为默认全局配置路径。
