---
name: high-handover-feishu-sync
description: 全量生成高阶交接明细，并覆盖写入飞书《交接情况统计-高阶》的明细 sheet。
version: 1.0.0
---

# 高阶交接明细 → 飞书明细 sheet

适用场景：
- 用户要把“高阶交接明细预览”变成正式的飞书全量覆盖同步
- 目标表是：`交接情况统计-高阶`
- 目标 sheet 是：`明细`

## 当前已验证目标

- Wiki URL：`<REDACTED_FEISHU_URL>`
- spreadsheet_token：`<REDACTED_FEISHU_SPREADSHEET_TOKEN>`
- sheet_id：`99caa0`
- sheet title：`明细`

## 当前业务口径

### 1. 明细基础范围
- 数据源：`~/.hermes/sql/projects/handover-realtime-sync/交接数据-实时.sql`
- 时间：`支付日期 >= 2025-01-01`
- 商品限制：**只限制 `商品sku='声乐'`**
- 不限制：`营期sku`
- 不限制：`营期阶段`。历史版本曾只保留 `二阶营期`、`三阶营期`、`四阶营期`、`五阶营期`，但 2026-05-11 已按用户要求移除该限制，`销转营期`、`特殊营期` 等也应进入明细。

### 2. A:AC 列
- 直接沿用实时交接 SQL 结果字段
- 当前顺序：
  - `flow_no`
  - `union_id`
  - `nick_name`
  - `营期名称`
  - `营期轨次`
  - `营期开课日期`
  - `营期封板日期`
  - `营期sku`
  - `商品sku`
  - `商品名称`
  - `支付类型`
  - `商品原价`
  - `支付时间`
  - `支付日期`
  - `团队`
  - `组别`
  - `成交人`
  - `退款时间`
  - `营期阶段`
  - `二阶学管`
  - `二阶轨次`
  - `二阶营期`
  - `加微时间`
  - `开课日期`
  - `加入轨次日期`
  - `加入营期日期`
  - `选期状态`
  - `加微状态`
  - `开课状态`

### 3. AD:AH 补充字段
- `报名学员数 = 1`
- `交接学员数 = 有二阶学管，且二阶轨次不含 冻结/延期/分配`
- `退费学员数 = 退款时间不为空`
- `加微学员数 = 满足交接学员条件，且加微时间不为空`
- `衔接课开课人数 = 满足交接学员条件，且衔接课开课日期不为空`
  - 注意：`衔接课开课日期` 来自 SQL 内部字段，不写入飞书 A:AH 明细列。
  - 这不是正式课首课白名单口径；正式课 `开课日期` 仍保留在明细列中，但不再作为高阶 `衔接课开课人数` 的计数依据。

## 已验证脚本

主脚本：
- `~/.hermes/python/projects/high-handover-feishu-sync/run_sync.py`

运行命令：
```bash
/opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python \
  /Users/zheng/.hermes/python/projects/high-handover-feishu-sync/run_sync.py \
  --write-feishu
```

## 实现细节

### 数据生成
- 动态加载：`~/.hermes/python/projects/handover-realtime-sync/run_sync.py`
- 复用其中的 `query_clickhouse(sql)`
- SQL 模板来自：
  - `~/.hermes/sql/projects/high-handover-feishu-sync/高阶交接数据.sql`
- 注意：高阶 SQL 是从实时交接 SQL 拆出的独立模板，**已去掉**商品名排除条件：
  - `AND NOT multiMatchAny(T3.goods_name, ['.*进阶班.*', '.*名师班.*', '.*祝老师.*'])`
- 前端-二讲/实时交接仍使用：
  - `~/.hermes/sql/projects/handover-realtime-sync/交接数据-实时.sql`
  - 该 SQL 继续保留上述商品名排除条件
- 模板渲染参数：
  - `main_goods_sku = name in ('声乐')`
  - `goods_price = 1880`
  - `start_date = toDate('2025-01-01')`
  - `end_date = toDate('2030-12-31')`

### 飞书写入
- 凭证文件：`~/.config/hermes/feishu_credentials.json`
- 使用 cashflow-core 内已有客户端：
  - `automatic.clients.feishu.get_tenant_access_token`
  - `automatic.clients.feishu_sheets.ensure_sheet_grid_size`
  - `automatic.clients.feishu_sheets.batch_update_values`
- 写入策略：
  1. 先根据结果行数自动扩容 sheet
  2. 再分块覆盖写入 `A:AH`
  3. 若旧数据比新数据更多，补空白行清掉旧尾部残留
- 当前列数为 34 列，对应最后一列 `AH`

## 本地输出

脚本每次同时输出两份目录：

正式导出：
- `~/.hermes/output/exports/high-handover-feishu-sync/`

预览副本：
- `~/.hermes/output/query_results/`

文件名形如：
- `高阶交接明细_YYYYmmdd_HHMMSS.xlsx`
- `高阶交接明细_YYYYmmdd_HHMMSS.csv`
- `高阶交接明细预览_YYYYmmdd_HHMMSS.xlsx`
- `高阶交接明细预览_YYYYmmdd_HHMMSS.csv`

## 定时任务

已验证 cron：
- 名称：`交接情况统计-高阶明细全量写入飞书`
- job_id：`81b2a1861039`
- 调度：`0 13,17 * * *`

## 排查某个二阶轨次为什么没进高阶表

适用场景：用户问某个 `二阶轨次` / 承接轨次为什么在《交接情况统计-高阶》明细里没有数据，怀疑被过滤。

优先按“漏斗式排查”回答，不要只看最终飞书表：

1. 先查最近本地导出的高阶 CSV，确认最终结果中该轨次是否存在：
   - 路径：`~/.hermes/output/exports/high-handover-feishu-sync/高阶交接明细_*.csv`
   - 检查 `二阶轨次`，必要时全列搜索。
2. 再查 ClickHouse 源数据中该轨次是否存在：
   - `dim_camp_df.camp_group_name = '<轨次名>'` 可验证轨次/camp_id/营期阶段。
   - `drh_handover_plus FINAL` 通过 `class_camp_id` 或 `stop_camp` 关联 `dim_camp_df`，可验证承接记录数。
3. 对照高阶同步过滤条件逐项计数。注意该清单必须随业务口径更新，2026-05-11 后**不再限制营期阶段**：
   - `T3.goods_sku_name = '声乐'`
   - 不再使用：`T0.class_stage_name IN ('二阶营期','三阶营期','四阶营期','五阶营期')`
   - `round(ifNull(T1.total_price,0)/100,4) >= 1880`
   - `toDate(T1.pay_time) >= toDate('2025-01-01')`
   - `T1.pay_type IN (2,3)`
   - `T3.first_level_name = '课程'`
   - 高阶 SQL 当前不使用前端-二讲/实时交接中的商品名排除：`NOT multiMatchAny(T3.goods_name, ['.*进阶班.*', '.*名师班.*', '.*祝老师.*'])`
4. 注意 ClickHouse `FINAL` 不能直接跟别名，排查 SQL 里用子查询包住：
   - 正确：`FROM (SELECT * FROM drh_handover_plus FINAL WHERE _sign > 0) AS h`
   - 避免：`FROM drh_handover_plus FINAL h`

已验证案例：`声乐三阶-20260428-进阶班小课包`
- `dim_camp_df` 中存在 2 个 camp：`15865` / `15866`，营期阶段为 `三阶营期`。
- `drh_handover_plus` 关联该二阶轨次有 `704` 单。
- 最终高阶结果为 `0`，主要原因是商品名大量包含 `进阶班`，命中 SQL 源头排除：

```sql
AND NOT multiMatchAny(T3.goods_name, ['.*进阶班.*', '.*名师班.*', '.*祝老师.*'])
```

该案例中的结论来自旧口径：当时虽有 1 单商品名不含 `进阶班`（`声乐院长特别班`），但前端营期阶段为 `销转营期`，又被 Python 的阶段过滤排除。2026-05-11 移除阶段过滤后，类似 `销转营期` 记录应重新进入高阶明细；遇到历史案例需按当前口径重查，不要沿用旧结论。

结论表达模板：
- “不是飞书写入问题，源表有数据；当前同步口径在 SQL 阶段/后处理阶段把它过滤了。”
- 如果用户要纳入，不建议直接删除 `进阶班` 排除条件；优先建议对指定二阶轨次或业务确认后的商品范围做例外，避免误放大量原本排除的进阶班商品。

## 常见口径差异

### 开课状态=未开课，但衔接课开课人数=1

这是当前口径允许出现的结果，不一定是同步错误。

- 飞书列里的 `开课状态` 使用正式课首课白名单口径：
  - 依赖 `开课日期`，该字段来自 `tock_ast_process_data` 中匹配白名单课程名的正式课记录：`月夜/小白杨/鸿雁/我和你/红河谷第1课/手指技术专项强化课第一节`。
  - SQL 还要求 `承接状态=已承接`、`二阶学管` 不为空、`加微时间` 不为空、`开课日期` 不为空，并且 `today() >= 开课日期`，才显示 `已开课`。
- `衔接课开课人数` 使用高阶统计口径：
  - Python 中按 `handover_ok & 衔接课开课日期.notna()` 计算。
  - `衔接课开课日期` 来自 `tock_ast_process_data` 任意 `study_time > 0` 的最早学习记录，不要求命中正式课首课白名单，也不要求 `加微时间` 不为空。
  - 该内部字段不写入飞书 A:AH 明细列，所以在表里看不到直接依据。

因此常见原因是：用户有衔接课/任意课程学习记录，所以 `衔接课开课人数=1`；但没有正式课首课白名单记录，或缺少加微信时间，所以 `开课状态` 仍是 `未开课`。

排查时读取原始 SQL 结果中的内部字段 `衔接课开课日期` / `衔接课开课状态`，不要只看飞书明细列。

## 维护注意事项

1. 若目标 sheet 列结构变化，优先同步修改：
   - `BASE_COLS`
   - `EXTRA_COLS`
   - `LAST_COL`
2. 若业务改成限制 `营期sku`，必须显式修改过滤逻辑；当前是**只限制商品sku**。
3. 若飞书已有公式或其他附加列，不要直接扩大覆盖范围；当前仅覆盖 `A:AH`。
4. 若业务要求“高阶开课口径调整为衔接课开课”，只改 Python 里 `衔接课开课人数` 的判断，不改飞书列结构：
   - SQL 已输出内部字段 `衔接课开课日期`，但 `BASE_COLS` / `ALL_COLS` 仍不包含它，目标覆盖范围仍是 `A:AH`。
   - 在 `run_sync.py` 中用 `handover_ok & df['衔接课开课日期'].notna()` 计算 `衔接课开课人数`。
   - 保持正式课 `开课日期` 列继续展示，避免破坏下游表头；它只是退出高阶 `衔接课开课人数` 计数。
   - 改完后必须重跑并验证：JSON `metric_sums.衔接课开课人数`、本地 Excel 仍为 34 列、飞书读回 `A1:AH4` 表头正确。
5. 若需要抽样核对，先读飞书 `99caa0!A1:AHN` 再和本地导出比对。
5. cron 命令已使用 hermes-sql 的绝对 Python 路径，不要改回 `conda activate && python` 模式。

## 最低验证项

每次改完后至少验证：
1. 本地脚本能成功运行
2. 返回 JSON 中包含：
   - `rows`
   - `stage_counts`
   - `metric_sums`
   - `feishu.rows_written_including_header`
3. 飞书读取 `A1:AH4` 可见正确表头
4. sheet 元数据 `row_count` 不小于新写入行数
