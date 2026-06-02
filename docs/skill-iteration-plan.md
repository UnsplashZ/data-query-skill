# internal-data-query skill 一次性迭代计划

## 目标

把当前 `internal-data-query` 从“可安装的数据查询 skill 包”升级为“安装后能被自然触发、能主动引导配置、能接入既有数据知识库、能连接多类数据源、能完成可靠 SQL 查数闭环、能沉淀可复用查询知识”的内部数据查询能力。

本轮不是 MVP，也不是分阶段试点。`一次到位` 和 `安装即会用` 是硬性验收标准：用户把 zip 或链接交给 Codex / 其他 AI web coding 工具后，AI 必须能识别、安装、校验、引导配置、跑 smoke check，并告诉用户后续如何用自然语言触发查数。不能只交付“计划上未来能做”的版本。

这次迭代不追求把流程拆成很多小阶段，而是一次性把用户实际安装和使用时最关键的断点补齐：

- 安装后，AI 应知道这个 skill 什么时候要被隐性调用。
- 安装后，AI 应主动提示用户配置 Metabase、ClickHouse、ODPS、MySQL 等只读账号或调用方式。
- 用户通过链接或 zip 交给 Codex / 其他 AI web coding 工具安装时，AI 应能完成解压、识别、校验、配置引导和首个 smoke check。
- skill 在真实查数时应具备完备 SQL 查询能力：能发现口径、找表找字段、复用历史 SQL、连接数据源、执行查询、读取 Metabase 看板、导出结果、复核结果并说明风险。
- 共享知识沉淀必须区分个人临时产物、AI candidate memory、团队 approved truth。

## 关键判断

隐性调用不是单靠 `SKILL.md` 正文决定的。对 Codex 类工具，触发主要来自 skill frontmatter 的 `name` / `description` 以及运行时是否认为当前请求匹配；对其他 AI web coding 工具，触发更多依赖安装后的 README、目录结构、使用说明和安装代理是否主动读取这些文件。

因此本次迭代要同时改三层：

1. **触发层**：让 skill metadata 明确覆盖“查数、SQL、schema、Metabase、ClickHouse、ODPS、MySQL、报表、指标口径、数据验证、数据依赖映射、安装配置”等场景。
2. **安装层**：让 AI 安装者在解压后必须继续提示配置账号，不能停在“文件已安装”。
3. **执行层**：让真实查询过程有 source selection、SQL static check、sample/full execution、validation、confidence 和 final answer contract。

## 硬性验收口径

本轮实现必须同时满足：

- **安装即会用**：安装完成后，AI 必须主动进入配置引导；如果没有真实账号，也必须生成本地占位配置、说明缺口，并完成离线 smoke check。
- **安装体验不可降级**：完备 SQL 能力不能以牺牲安装体验为代价；zip / 链接安装、配置引导、凭证本地化、首次 smoke check、后续自然语言触发说明必须同批完成。
- **隐性可触发**：用户不需要记住脚本名；说“查数据 / 写 SQL / 看 Metabase / 找字段 / 验证口径 / 配置数据源”时，应命中本 skill。
- **真实查询闭环**：有账号时能完成 schema / 历史 SQL / Metabase 检索、只读 SQL、采样、验证、导出和结果说明。
- **无账号也可落地**：没有账号时，仍能完成安装校验、配置模板生成、schema KB / 历史 SQL 检索、SQL 草案和 unverified 风险标注。
- **协作知识可同步成长**：多人在同一仓库内持续补充、复核、晋升、废弃知识时，知识库必须能通过仓库文件同步保持兼容，不能只适配单机单人。
- **渐进式知识沉淀**：查数过程中允许隐性记录高价值候选知识，但不频繁打扰用户；只有结果和口径趋于稳定时，才阶段性建议写入共享知识库。
- **质量护栏齐全**：SQL 静态检查、敏感信息扫描、manifest 校验、最小 eval、共享知识模板、仓库同步兼容检查和检索规则必须同批落地。
- **不能把高级能力留空**：promotion、query knowledge 检索、模板校验、eval 不能只写在计划里；至少要有可运行脚本和 fixtures 覆盖主路径。
- **保持轻量**：不把本 skill 做成完整数据平台，不引入 DB-GPT / WrenAI / Cube / MindsDB 这类重型 runtime 作为默认依赖；只借鉴其设计，落成本仓库内轻量脚本、模板和工作流。
- **MCP 暂不进入本轮**：本轮先做好 zip / link 安装、直接只读连接、多源 SQL 查询、Metabase 取数和 repo-native 知识库；MCP 只记录为未来方向，不作为交付项或验收项。

## 完备 SQL 查询能力定义

本 skill 的核心不是“能写几条 SQL”，而是一个面向 AI 助手的完整内部数据查询层。一次到位版本必须具备以下能力。

### 1. 数据知识库接入

必须能接入并优先利用已有知识资产：

- 当前仓库中的 SQL、报表、notebook、数据目录、接口字段说明和业务文档。
- 包内 schema KB：`references/sql-query-method-internal/references/schema-kb/`。
- 包内历史 SQL：`references/historical-sql-index.md` 与 `references/old-sql/sql/`。
- 包内 method references：`references/sql-query-method-internal/references/method-skills/`。
- 仓库级共享知识：`data-query-knowledge/`。
- 未来用户新增的本地知识库路径，通过配置声明后纳入检索。

检索规则必须是证据优先：

- 先找已有看板 / 已有 SQL / schema / 口径说明，再新写 SQL。
- 每条引用的知识都要标注状态：`approved`、`reviewed`、`candidate`、`historical`、`deprecated`、`unknown`。
- 历史 SQL 和 candidate memory 只能作为字段、join、口径线索；不能直接当当前真源。
- 当多个知识源冲突时，必须列出冲突并降级 confidence，不能自行选择一个当结论。

### 2. 多数据源连接能力

必须支持包括但不限于以下数据源：

- ClickHouse：用于快速明细探索、近实时或大宽表查询、看板底表核对。
- ODPS / MaxCompute：用于离线数仓、DWD/DWS、财务/订单/退款/GMV 等标准口径。
- MySQL：用于应用真实状态、业务系统读模型、配置表、审批/工单/后台状态核对。
- Metabase：用于搜索、读取和执行已有 card / dashboard，优先复用已有看板 SQL 和结果。

连接能力必须包括：

- 本地只读连接配置：默认 `~/.internal-data-query/data-sources.yaml`。
- 多 profile 支持：例如 `default`、`prod-readonly`、`staging-readonly`。
- 每个 source 都能独立配置、独立 smoke check、独立报错。
- 连接失败时给出可执行修复提示，不吞错、不伪造结果。
- 所有执行路径默认只读，拒绝 DDL / DML / 权限变更 / 生产写操作。
- 后续扩展新引擎时，通过统一 runner 接口接入，不改主工作流。

### 3. Metabase 看板直接取数能力

Metabase 不是辅助项，而是正式数据源。必须支持：

- 搜索 card / dashboard。
- 获取 card 元数据、native SQL、参数、数据库 ID、更新时间。
- 判断 card 是否能回答用户问题。
- 运行 card 并导出 CSV / XLSX。
- 对带参数 card 支持参数填充或明确提示缺失参数。
- 将 Metabase 结果标注为 dashboard evidence；若需要作为最终口径，仍需说明 owner、更新时间和是否有权威确认。

默认策略：

- 用户问“有没有现成看板 / 看板数据 / Metabase 指标”时，先走 Metabase search。
- 用户问常见经营指标时，也要先查 Metabase，再决定是否新写 SQL。
- 如果已有 card 足够匹配，优先运行 card；只有缺口明确时才新写 SQL。

### 4. SQL 生成、执行与复核闭环

完整查询流程必须覆盖：

```text
理解问题
-> 形成 Query Brief
-> 检索知识库 / 看板 / schema / 历史 SQL
-> 选择数据源和执行引擎
-> 生成只读 SQL 或选择 Metabase card
-> 静态检查
-> schema / metadata check
-> 小样本或小时间窗执行
-> 枚举、join cardinality、金额单位、去重口径复核
-> 全量执行或明确标记 unverified
-> 导出结果
-> 生成 result summary / SQL review / residual risk
```

每次最终交付必须说明：

- 使用的数据源和为什么选择它。
- 使用或拒绝的知识资产。
- 表、字段、join key、时间字段、粒度、状态过滤、金额单位。
- SQL 或 Metabase card ID。
- 是否执行、执行范围、行数、导出路径。
- 验证动作和剩余风险。
- 结果可信度：`verified`、`partially_verified`、`unverified`、`historical_only`。

### 5. 查询能力边界

必须明确拒绝或降级这些情况：

- 用户要求写入、删除、改库、授权、修生产数据：默认拒绝，除非任务明确变成数据库运维且用户另行授权。
- 无法确认表字段或口径：输出 discovery report / requirement gap，不编造 SQL。
- 没有账号或执行失败：可以给 SQL 草案，但必须标 `unverified`。
- 结果与已有看板或历史 SQL 冲突：必须报告冲突，不直接给单一结论。

## 安装体验与首次可用性

安装体验是核心能力，不是附属文档。一次到位版本必须让拿到 zip / 链接的用户和 AI 助手沿着同一条路径完成首次可用。

必须覆盖：

- AI 能识别 skill 包：存在 `SKILL.md`、`manifest.json`、`scripts/setup_connections.py`、README 和必要 references。
- AI 能解释这个 skill 的自然语言用法，而不是要求用户记命令。
- AI 能主动询问要配置哪些 source：Metabase、ClickHouse、ODPS / MaxCompute、MySQL，以及未来扩展数据源。
- AI 能在 TTY 环境运行交互式配置，也能在无 TTY 环境生成本地占位 YAML。
- AI 能区分“已安装”“已配置”“可离线检索”“可真实执行查询”四种状态。
- AI 能在安装后输出下一步建议：缺账号时如何补账号，有账号时如何跑 smoke check，后续如何发起查数请求。
- 安装流程必须默认不写仓库、不提交 git、不泄露凭证、不把真实配置打进 zip。

安装后的状态报告建议固定为：

```text
installed: yes/no
local_config: present/missing/placeholder
available_sources:
  metabase: ready/missing/failed
  clickhouse: ready/missing/failed
  odps: ready/missing/failed
  mysql: ready/missing/failed
offline_knowledge:
  schema_kb: ready/missing
  historical_sql: ready/missing
  repository_knowledge: ready/missing
next_actions:
  - ...
```

## 仓库协作与知识库自我成长

`data-query-knowledge/` 必须设计成 repo-native、可 review、可 diff、可同步的知识库。多人协作时，它通过仓库文件同步，而不是依赖某台机器的本地缓存或个人配置。

### 1. 同步原则

- 知识库文件使用 Markdown / YAML / JSON，避免二进制和本地数据库，保证 git diff / review 友好。
- 每个知识文件必须有稳定 ID、`schema_version`、`status`、owner、时间戳、适用范围和验证证据。
- 本地凭证、导出结果、临时 SQL、个人配置永远留在 `data-query-work/` 或本机目录，不进入共享知识库。
- 共享知识只记录可复核的口径、表字段、join、SQL 模板、看板引用、验证证据和风险。
- 不同 AI 或不同成员生成的 candidate 必须能共存；通过 status、owner、supersedes、conflicts_with 解决冲突。

### 2. 知识生命周期

标准流转：

```text
draft
-> candidate
-> reviewed
-> approved
-> deprecated
```

规则：

- `draft`：个人或 AI 初稿，不参与默认检索。
- `candidate`：可以被搜索到作为线索，但默认不能当最终口径。
- `reviewed`：经过 owner 或同事复核，可作为较高置信参考。
- `approved`：可作为默认优先口径，但仍要检查 `expires_at` 和适用范围。
- `deprecated`：默认排除，除非用户要求查历史。

知识成长不是覆盖旧文件，而是保留关系：

- 新版本用 `supersedes` 指向旧版本。
- 冲突知识用 `conflicts_with` 显式标注。
- 废弃原因写入 `deprecation_reason`。
- 复核证据写入 `validation_evidence`。
- 晋升、废弃、冲突解决写入 `promotion-log.md` 或结构化 log。

### 3. 多人协作兼容

必须支持这些场景：

- A 在仓库中新增某指标口径，B 拉到同一仓库后能检索、验证、继续晋升。
- A 和 B 对同一指标产生不同 candidate，系统能同时保留并标冲突，而不是互相覆盖。
- 某个 approved 口径过期后，新查询默认降级并提示需要复核。
- 不同 AI 助手安装同一 skill 后，都能读取同一套 `data-query-knowledge/` 文件并遵守相同状态语义。
- 仓库同步产生冲突时，脚本能报告冲突文件、冲突 ID、冲突字段和建议处理方式。

### 4. 版本与迁移

知识库需要有版本兼容机制：

- 根目录保留 `data-query-knowledge/manifest.yaml`，记录 `schema_version`、domains、owners、last_validated_at。
- 每类模板记录自身 `schema_version`。
- 新版 skill 读取旧版知识库时，必须能给出兼容性报告。
- 必要时提供 migration script，把旧字段补齐到新 schema，但不得静默删除旧证据。
- `validate_query_knowledge.py` 必须检查 schema version、必填字段、过期、冲突、owner 和 promotion log 一致性。

### 5. 仓库同步边界

本 skill 可以生成 repo-native 文件、报告冲突和给出同步建议，但不能绕过用户的 git 权限边界。

- 不自动 commit / push / pull / merge。
- 当用户要求同步到仓库时，先说明要变更哪些知识文件。
- 如果环境规则要求 git 操作确认，必须先获得用户明确授权。
- 共享知识可以通过普通代码 review 流程进入仓库；skill 负责让文件格式、状态和证据可审。

### 6. 渐进式知识沉淀

查数过程本身应持续完善数据库认知，但沉淀动作必须低打扰、可复核、可共享。

原则：

- 查询早期主要是需求和口径对齐，不频繁询问是否记录。
- 查询过程中可以隐性生成候选知识，但默认只进入候选区，不直接成为 approved truth。
- 候选知识应是 repo-native 文本资产，可被团队同步、review 和继续迭代。
- 只有当结果趋于稳定、用户确认口径、某条知识多次复用，或出现明显高价值结构化认知时，才阶段性提示用户是否写入共享知识库。
- 用户明确说“记一下”“以后按这个口径”“这个表你记住”时，可以直接生成 candidate，但仍不自动 approved。

候选知识成熟度：

```text
observed
-> user_asserted
-> query_verified
-> reused
-> ready_for_candidate
-> ready_for_review
```

建议新增共享候选区：

```text
data-query-knowledge/
├── candidates/
│   ├── observations/
│   ├── user-assertions/
│   ├── query-verified/
│   └── reusable-patterns/
```

沉淀触发条件：

- 用户确认结果或口径：“这个结果对了”“以后就按这个口径”。
- 同一字段、状态枚举、join key、Metabase card、指标口径被多次复用。
- 查询中发现了明确的表用途、字段含义、枚举定义、join 风险或指标公式。
- 查询结果已经进入 final / review 状态，而不是还在需求对齐阶段。

阶段性提示示例：

```text
这轮查询已经形成 3 条比较稳定的可复用知识：
1. audit_status=3 表示审批通过
2. refund_order 与 pay_order 可用 order_no 关联，但可能一对多
3. Metabase card 123 可作为 GMV 日报参考看板

是否写入 data-query-knowledge/candidates/ 作为 candidate？不会标记为 approved。
```

不触发沉淀的情况：

- 用户还在改需求、改时间范围、改口径。
- SQL 尚未执行或结果标记为 `unverified`。
- 只是一次性的临时过滤条件。
- 和已有知识冲突但未确认来源。
- 涉及敏感字段、权限信息或本地凭证。

自动记录与用户确认的边界：

- 可隐性记录：表/字段被使用、候选 join、候选枚举、失败原因、验证动作、可复用 SQL 片段。
- 需要阶段性询问：写入共享候选区、把 query case 抽象为 golden query、把用户口头认知写成 semantic memory。
- 必须 review 才能晋升：candidate -> reviewed -> approved。

## 开源项目轻量借鉴记录

这些项目只作为设计参考，不作为本轮默认依赖。本 skill 的实现原则是：吸收有效模式，避免引入重平台；能用 Markdown / YAML / JSON / Python 脚本解决的，不引入服务端系统。

### WrenAI：借鉴 context layer，不引入平台

可借鉴：

- 不让 LLM 直接猜裸表，而是先构建业务语义上下文。
- MDL 思路：model、relationship、calculation、metric、view、permission、memory 都可审、可版本化。
- dry-plan / context build：生成 SQL 前先确认上下文和执行计划。

本 skill 的轻量落法：

- `data-query-knowledge/` 做 MDL-lite，而不是部署 WrenAI。
- 用 `metric-definition.md`、`source-profile.md`、`join-contract.md`、`golden-query.md` 表达语义和口径。
- 只保留必要字段：owner、status、grain、time field、filters、join、metric formula、validation evidence。

### Dataherald：借鉴 context store + golden SQL + tool loop

可借鉴：

- SQL agent 不靠单 prompt，而是检索 schema、列说明、业务上下文、few-shot / golden SQL。
- 用工具循环完成生成、检查、执行、修正。

本 skill 的轻量落法：

- `search_schema.py`、`search_old_sql.py`、`search_query_knowledge.py` 共同组成本地 context store。
- golden SQL 只作为 `candidate/reviewed/approved` 知识资产，不直接当最终结果。
- 查询流程固定为：检索上下文 -> 写 SQL -> 静态检查 -> sample -> 修正 -> full/export。

### Vanna：借鉴 SQL / DDL / documentation 训练资产分类

可借鉴：

- 把可学习资产分成 SQL、DDL、documentation 三类。
- 通过历史问题和相关训练数据增强 text-to-SQL。
- 生成结果后可被人工 flag / review。

本 skill 的轻量落法：

- 将历史 SQL、schema KB、业务文档分别映射成 `sql`、`schema`、`documentation` knowledge type。
- 自动沉淀只能进入 `draft` 或 `candidate`，不能自动 approved。
- 不依赖 Vanna runtime；如未来需要，只做 import/export。

### DB-GPT：借鉴 workflow 和 sandbox，不引入一站式平台

可借鉴：

- 数据助理工作流：连接数据源、查知识库、执行 SQL / Python、生成图表和报告。
- 沙箱执行和步骤化 agent workflow。

本 skill 的轻量落法：

- 本轮只做 SQL 查询和结果摘要，不做完整报表平台。
- 导出结果后的 Python / notebook 分析可以留作后续能力。
- 不引入 AWEL、server、admin console 或多模型平台。

### XiYan MCP / MindsDB / Cube MCP：记录为未来方向，本轮不做 MCP

可借鉴：

- 把查数能力封装成 agent 可调用工具。
- 统一 schema resources、query tool、semantic layer access。
- Cube 的“AI 只查语义层，不直连裸表”对权限和口径治理有价值。

本轮处理：

- 不实现 MCP server。
- 不把 `transport: mcp` 加入验收。
- 只在架构上保留未来可把 `run_query.py`、`search_query_knowledge.py`、Metabase card runner 封装成 MCP tools 的可能性。

### PandasAI：借鉴轻量探索，不进入核心链路

可借鉴：

- CSV / DataFrame / Parquet 的自然语言探索。
- 代码执行沙箱和图表生成。

本 skill 的轻量落法：

- 本轮不做 DataFrame agent。
- 仅保留导出 CSV / XLSX 后可被后续 notebook 或外部工具分析的接口。
- 若未来要做结果分析，再增加 sandbox，不影响 SQL 查询主链路。

### LangChain SQL Agent：借鉴最小工具循环

可借鉴：

- list tables -> get schema -> generate query -> check query -> execute -> fix error -> final answer。
- 官方强调收窄数据库权限。

本 skill 的轻量落法：

- 不引入 LangChain 作为默认依赖。
- 把这个工具循环写进 `SKILL.md` 和 `query-execution-contract.md`。
- 用本仓库已有脚本实现工具，而不是引入 agent framework。

## 本轮不做的开源集成

- 不直接集成 WrenAI、DB-GPT、Vanna、Dataherald、MindsDB、Cube、PandasAI、LangChain。
- 不做 MCP server。
- 不做模型微调或专用 Text-to-SQL 模型接入。
- 不做长期运行的 Web 服务、admin console、权限平台或可视化 BI 平台。
- 不把这些项目的复杂架构搬进来；只保留对本 skill 有直接帮助的轻量模式。

## 最终交付形态

### 1. 触发与安装引导

重写 `SKILL.md` frontmatter description，使它更适合隐性触发，覆盖这些用户说法：

- “帮我查一下数据”
- “写个 SQL”
- “看一下 Metabase 里有没有这个指标”
- “这个页面字段应该接哪张表”
- “导出某个时间段的订单/退款/GMV”
- “验证这个报表口径”
- “安装这个数据查询 skill”
- “配置内部数据源账号”

在 `SKILL.md` 的开头增加硬性安装契约：

- 如果当前任务是安装本 skill，安装完成后必须询问用户是否现在配置数据源。
- 如果用户同意，优先运行 `python scripts/setup_connections.py`。
- 如果没有 TTY，使用 `--non-interactive` 生成本地占位配置，然后引导用户填本机 YAML。
- 配置文件默认写入 `~/.internal-data-query/data-sources.yaml`，权限设为 `0600`。
- 任何凭证不得写入 skill 包、仓库文档、manifest、聊天记录或生成 SQL。
- 配置后至少运行一个无敏感 smoke check，例如脚本 help、schema 搜索、`select 1` 或 Metabase search。

同步更新 `README.md`，让通过 zip / 链接安装的 AI 助手看到后能执行同样流程。README 不做长篇教程，只保留“安装后下一步必须做什么”。

### 2. 安装包使用路径

定义一套 AI 安装者应该执行的标准路径，写入 `SKILL.md` 和 README：

```text
收到链接/zip
-> 解压到 AI 工具可读取的 skills 目录或用户指定目录
-> 确认存在 SKILL.md、manifest.json、scripts/setup_connections.py
-> 运行 manifest 校验和敏感信息扫描
-> 提示用户配置哪些数据源
-> 生成本地 data-sources.yaml
-> 运行 smoke check
-> 告诉用户后续可直接用自然语言触发查数
```

安装后的用户提示要明确，例如：

```text
internal-data-query 已安装。要执行真实查询，还需要配置只读数据源。
我可以现在帮你配置 Metabase、ClickHouse、ODPS/MaxCompute 或 MySQL。
请确认要配置哪些数据源；凭证只会写入你的本机 ~/.internal-data-query/data-sources.yaml。
```

### 3. SQL 查询能力闭环

补齐上一轮 review 指出的 P1：skill 本体不能只讲架构，必须能指导 AI 完成可靠 SQL 查询。

新增或强化这些规则：

- 先搜当前仓库、Metabase、schema KB、历史 SQL、method references、`data-query-knowledge/`，再写新 SQL。
- 先选数据源，再写 SQL；不能静默切换数据源。
- 历史 SQL 只能当证据，不能当当前真源。
- Metabase card / dashboard 是正式 source；能匹配时优先复用并运行看板取数。
- SQL 必须只读；默认禁止 DDL、DML、grant、drop、truncate、insert、update、delete、alter、create。
- 所有查询必须声明时间字段、时间范围、粒度、状态过滤、金额单位。
- 执行可用时必须走 sample -> validation -> full scope。
- 执行不可用时必须标记 `unverified`。
- 输出结果必须包含 source、metric definition、SQL/result、validation、risk。

新增 `references/query-execution-contract.md`，把执行闭环集中写清楚：

- dialect 策略：ClickHouse / ODPS / MySQL / Metabase 的日期、limit、函数、导出差异。
- 失败修正循环：字段不存在、权限不足、方言错误、timeout、join 膨胀、空结果分别怎么处理。
- 采样策略：`LIMIT`、小日期范围、枚举分布、join cardinality、聚合 sanity check。
- 可信度标签：`verified`、`partially_verified`、`unverified`、`historical_only`。

### 4. 脚本能力补齐

保留当前已有脚本，并一次性补关键缺口：

- `scripts/query_static_check.py`
  - 检查 SQL 是否只读。
  - 检查是否缺少时间范围、limit、scope、危险关键字。
  - 根据 engine 给出方言风险提示。

- `scripts/search_query_knowledge.py`
  - 检索仓库级 `data-query-knowledge/`。
  - 支持按 `status`、`domain`、`metric`、`grain`、`source`、`confidence` 过滤。
  - 默认排除 `candidate`、`deprecated`、`expired`。

- `scripts/validate_query_knowledge.py`
  - 校验共享知识模板字段是否齐全。
  - 校验 status、owner、reviewer、expires_at、supersedes、conflicts_with。

- `scripts/eval_skill_pack.py`
  - 一次跑 manifest、敏感信息扫描、SQL static check、knowledge validation、基础检索 eval。

- `scripts/promote_query_knowledge.py`
  - 将 candidate 晋升为 reviewed / approved。
  - 写 promotion log。
  - 阻止缺少 review evidence 的晋升。

- `scripts/check_connections.py`
  - 对 ClickHouse、ODPS、MySQL、Metabase 分别执行只读 smoke check。
  - 输出每个 source 的可用状态、profile、错误原因和下一步配置建议。

- `scripts/discover_data_sources.py`
  - 汇总当前可用连接、schema KB、历史 SQL、Metabase 状态、仓库级知识库状态。
  - 安装后和每次复杂查询前都可运行，用来告诉 AI 当前能查什么、缺什么。

- `scripts/report_query_knowledge_sync.py`
  - 检查 `data-query-knowledge/` 的新增、过期、冲突、重复 ID、schema version 和 promotion log 状态。
  - 输出适合代码 review 的同步报告，不执行 git 操作。

- `scripts/migrate_query_knowledge.py`
  - 将旧版共享知识模板迁移到当前 `schema_version`。
  - 只补字段和生成迁移报告，不静默删除旧证据。

- `scripts/capture_query_knowledge.py`
  - 从 query brief、SQL review、result summary、Metabase card、用户断言中抽取候选知识。
  - 默认写入 candidate / observed 状态。
  - 支持 `--dry-run` 输出建议，不直接改共享知识库。

- `scripts/suggest_knowledge_capture.py`
  - 根据查询轮次、复用次数、验证状态和用户确认信号，判断是否应该阶段性提示用户沉淀知识。
  - 输出低打扰提示文案和候选知识列表。

### 5. 个人工作区与共享知识区

继续保留当前 `data-query-work/` 作为默认个人工作区：

```text
data-query-work/
├── briefs/
├── reviews/
├── sql-drafts/
├── discovery-reports/
├── requirement-gaps/
└── exports/
```

新增标准仓库共享知识区。个人临时查数不强制创建该目录，但 skill 实现必须支持它；一旦仓库存在该目录或用户要求团队复用，就必须按共享知识规则执行。

```text
data-query-knowledge/
├── manifest.yaml
├── OWNERS.yaml
├── candidates/
├── metrics/
├── sources/
├── joins/
├── golden-queries/
├── semantic-memory/
├── reviews/
├── promotion-log.md
└── deprecated/
```

硬规则：

- `data-query-work/` 默认是个人过程产物，不可直接当团队真源。
- `data-query-knowledge/` 才是共享知识区。
- AI 自动生成的知识默认只能是 `draft` 或 `candidate`。
- 查数过程中的隐性记录默认进入 `data-query-knowledge/candidates/` 或 `data-query-work/knowledge-candidates/`，不得直接进入 approved 区。
- `approved` 必须有 reviewer、validation evidence 和明确适用范围。
- `deprecated`、`expired`、`conflicts_with` 默认不参与普通检索。
- 共享知识必须是可 diff、可 review、可仓库同步的文本资产，不能依赖个人本地数据库。

### 6. 模板补齐

新增模板目录：

```text
templates/query-knowledge/
├── metric-definition.md
├── source-profile.md
├── join-contract.md
├── golden-query.md
├── semantic-memory.md
├── knowledge-candidate.md
├── review-record.md
├── promotion-request.md
└── OWNERS.yaml.example
```

共享知识模板必须包含这些字段：

- `id`
- `schema_version`
- `status`
- `created_by`
- `reviewed_by`
- `approved_by`
- `source_status`
- `confidence`
- `risk_level`
- `expires_at`
- `supersedes`
- `conflicts_with`
- `validation_evidence`
- `last_verified_at`
- `sync_notes`
- `maturity`
- `capture_trigger`
- `source_interaction`

### 7. README 与包边界

README 改成面向“拿到 zip/link 的用户和 AI 助手”：

- 这个 skill 是什么。
- 安装后 AI 必须做什么。
- 如何配置账号。
- 凭证放哪里。
- 如何确认配置成功。
- 用户后续怎么用自然语言触发。
- 什么不会自动发生：不会自动提交 git、不会写入生产库、不会把凭证打包。
- 多人协作时，哪些文件可以进入仓库同步，哪些文件必须留在本机。

避免新增过多教程型文档。详细规则放 references，主入口保持短而硬。

### 8. Eval 与验收

新增最小 eval：

```text
evals/
├── cases/
├── fixtures/
└── expected/
```

必须覆盖：

- readonly SQL 通过。
- DML / DDL 被拒绝。
- 缺时间范围被标记风险。
- 历史 SQL 不能标记为 verified。
- candidate memory 默认不被检索。
- 缺 review 字段的共享知识不能晋升。
- 安装配置脚本在 non-interactive 模式能生成本地占位配置。
- ClickHouse / ODPS / MySQL / Metabase 四类 profile 的配置解析和连接 smoke check。
- Metabase card search / get / run 的 mock eval。
- schema KB、历史 SQL、data-query-knowledge 多知识源冲突时必须降级 confidence。
- `data-query-knowledge/` 多人协作同步检查：重复 ID、过期 approved、冲突 candidate、旧 schema version。
- migration eval：旧版知识文件迁移后保留原证据和 supersedes / conflicts_with 关系。
- 渐进式知识沉淀 eval：早期查询不打扰，稳定结果后给出候选沉淀建议，未 review 不得晋升 approved。
- 轻量化边界 eval：确认本轮不依赖 MCP server、不启动常驻服务、不要求安装重型平台。

最终验收命令：

```bash
python scripts/validate_manifest.py
python scripts/scan_sensitive_info.py
python scripts/setup_connections.py --non-interactive --output data-query-work/config/internal-data-query-check.yaml --overwrite
python scripts/check_connections.py --config data-query-work/config/internal-data-query-check.yaml --offline-ok
python scripts/discover_data_sources.py --config data-query-work/config/internal-data-query-check.yaml
python scripts/search_schema.py refund --limit 3
python scripts/search_old_sql.py 退款 --limit 3
python scripts/query_static_check.py --sql-file evals/fixtures/readonly.sql --engine clickhouse
python scripts/query_static_check.py --sql-file evals/fixtures/reject-dml.sql --engine mysql
python scripts/validate_query_knowledge.py --root evals/fixtures/data-query-knowledge
python scripts/search_query_knowledge.py refund --root evals/fixtures/data-query-knowledge --status approved
python scripts/report_query_knowledge_sync.py --root evals/fixtures/data-query-knowledge
python scripts/migrate_query_knowledge.py --root evals/fixtures/data-query-knowledge-old --dry-run
python scripts/capture_query_knowledge.py --input evals/fixtures/query-case.md --root evals/fixtures/data-query-knowledge --dry-run
python scripts/suggest_knowledge_capture.py --input evals/fixtures/query-session.json
python scripts/eval_skill_pack.py
```

## 不做的事

- 不把 TianGong `.gstack` / data-access gate 搬进这个通用 skill。
- 不把真实凭证、真实内部 URL、个人配置打进 zip。
- 不默认创建 git commit、push、PR 或切分支。
- 不把 AI candidate memory 当作 confirmed source。
- 不强制所有用户使用仓库级 `data-query-knowledge/`；个人查数默认仍只用 `data-query-work/`。
- 不把 WrenAI、DB-GPT、Vanna、Dataherald、MindsDB、Cube、PandasAI、LangChain 作为默认依赖。
- 本轮不做 MCP；后续如需要再单独设计。

## 一次性实现顺序

虽然实现时可以分文件落地，但逻辑上按四个包一次完成；任一包缺失都不能算本轮完成：

1. **Activation & Onboarding Pack**
   - 改 `SKILL.md` metadata 和安装契约。
   - 改 README 的 zip/link 安装后引导。
   - 强化 `setup_connections.py` 的安装后提示和 smoke check 文案。

2. **Query Reliability Pack**
   - 新增 query execution contract。
   - 新增 `query_static_check.py`。
   - 把 SQL 验证、失败修正、confidence 输出写成硬规则。

3. **Knowledge Collaboration Pack**
   - 新增 `data-query-knowledge/` 规范。
   - 新增 query-knowledge 模板。
   - 新增 search / validate / promotion 脚本。

4. **Eval & Packaging Pack**
   - 新增 eval fixtures。
   - 新增 `eval_skill_pack.py`。
   - 更新 manifest。
   - 跑完整验收命令和敏感信息扫描。

## 成功标准

本轮完成后，一个用户把 zip 或链接交给 AI 助手时，理想行为应该是：

1. AI 能识别这是 `internal-data-query` skill。
2. AI 能安装并校验包。
3. AI 不会停在“安装完成”，而是主动要求配置只读数据源。
4. AI 能把凭证写到用户本机安全路径。
5. AI 能告诉用户以后直接说“帮我查 GMV / 退款 / 订单 / Metabase 卡片 / 字段映射”即可触发。
6. AI 在真实查数时不会乱编表字段，不会跳过验证，不会把历史 SQL 或 candidate memory 当真源。
