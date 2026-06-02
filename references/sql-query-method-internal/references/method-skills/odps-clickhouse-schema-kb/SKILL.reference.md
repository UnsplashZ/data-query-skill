---
name: odps-clickhouse-schema-kb
description: 维护并使用本地 ODPS / ClickHouse 表结构知识库，先查 KB 再做实时探表验证，再写正式 SQL。
---

# ODPS / ClickHouse Schema KB

适用场景：
- 用户要写新的 CK / ODPS SQL
- 需要先定位候选表、字段、ODPS↔CK 映射
- 需要刷新本地 schema 知识库

## 目标

避免直接按业务口径猜物理字段。标准流程是：
1. 先查本地知识库
2. 再做实时探表 SQL 验证
3. 最后写正式 SQL

补充参考：
- `references/clickhouse-user-relationship-export.md` 记录了 ClickHouse 大批量用户关系/企微好友关系导出的分批查询、旧版本 SQL 兼容性与验证清单。
- `references/clickhouse-user-relationship-export-session-20260519.md` 记录了一次用户关系导出任务中从大 SQL 改为分块/多小查询/pandas merge 的经验，包含 `exit code 143`、组合 CTE 长耗时、阶段日志、字段补齐与中间结果缓存注意事项。
- `references/clickhouse-order-dimension-relationship-export.md` 记录了订单维度好友关系导出口径：前端订单、首款无关联尾款、商品字段、正价班按订单/交接/企微辅助拆分判断。

## 本地知识库位置

- `~/.hermes/cleaned/projects/sql-metadata-index/index/unified_schema_index.json`
- `~/.hermes/cleaned/projects/sql-metadata-index/index/field_to_tables.json`
- `~/.hermes/cleaned/projects/sql-metadata-index/index/table_mapping.json`
- `~/.hermes/cleaned/projects/sql-metadata-index/index/refresh_summary.json`
- `~/.hermes/cleaned/projects/sql-metadata-index/index/schema_kb.md`

原始/运行产物：
- `~/.hermes/cleaned/projects/sql-metadata-index/raw/`
- `~/.hermes/cleaned/projects/sql-metadata-index/snapshots/`
- `~/.hermes/cleaned/projects/sql-metadata-index/runs/`

脚本：
- `~/.hermes/python/projects/sql-metadata-index/refresh_schema_kb.py`
- 兼容旧入口：`~/.hermes/python/projects/sql-metadata-index/build_odps_clickhouse_index.py`

## 刷新命令

始终在 `hermes-sql` 环境里跑：

```bash
eval "$(conda shell.bash hook)"
conda activate hermes-sql
python ~/.hermes/python/projects/sql-metadata-index/refresh_schema_kb.py
```

只刷单侧：

```bash
python ~/.hermes/python/projects/sql-metadata-index/refresh_schema_kb.py --source odps
python ~/.hermes/python/projects/sql-metadata-index/refresh_schema_kb.py --source clickhouse
```

## 增量逻辑

### ODPS
- 先拉全量 inventory
- inventory signature 依赖：
  - `table_name`
  - `owner`
  - `comment`
  - `is_virtual_view`
  - `column_count`
  - `partition_count`
  - `last_modified_time`
- 再只重抓新增/变更表的详细 schema
- 构建统一索引时保留未变更表旧快照

### ClickHouse
- 先查 `system.tables`
- inventory signature 依赖：
  - `engine`
  - `partition_key`
  - `sorting_key`
  - `primary_key`
  - `metadata_modification_time`
  - `comment`
  - `create_table_query_hash`
- 再只重抓新增/变更表的列信息

## 推荐工作流（写 SQL 前必须遵守）

### 第零步：先判断数据源
不要一上来就写 SQL。先判断这次任务应该走 ODPS 还是 ClickHouse：

- 用户要求飞书群快速查数、看板加速、已有 CK 表覆盖、需要秒级/分钟级反馈：优先 ClickHouse。
- 用户要求数仓标准口径、离线宽表、dwd/dws 指标、财务/现金流主链路：优先 ODPS。
- 如果用户明确指定 ODPS / ClickHouse，以用户指定为准。
- 如果两边都可能满足，先说明取数口径差异，再选一个主路径；必要时两边交叉验证。

### 第一步：查对应 schema / 常用表清单
按已判定的数据源查对应知识：

- ClickHouse：查 `unified_schema_index.json` / `field_to_tables.json` 中 CK 表和字段；同时查是否有已验证的 CK 表规则。
- ODPS：优先 dwd_ / dws_，再查用户常用表，再查 cron / 项目 SQL 引用表。
- 跨源场景：查 `table_mapping.json` 判断 ODPS↔CK 映射，不要凭表名猜。

判断是否满足：

- 是否有目标事实表。
- 是否有时间字段。
- 是否有指标分子/分母字段。
- 是否有业务筛选字段。
- 是否有 join key。
- 是否能支持用户要的粒度。

如果当前源不满足，切换到另一源或明确说明缺口。

### 第二步：基于现有知识先写候选 SQL
候选 SQL 要先在本地推敲：

- 业务口径是否对应到正确字段。
- 商品 SKU / 营期 SKU / cci3 等是否混用。
- 时间字段类型是否正确。
- join 粒度是否会放大行数。
- 分母和分子是否同一粒度。

### 第三步：检查方言与表规则
正式运行前必须做语言/方言检查。

ClickHouse 特别检查：

- `drh_*` 表是否需要 `FINAL` 和 `_sign > 0`。
- `FINAL` 后不能直接别名；需要包子查询。
- ClickHouse 21.8 不要使用不确定的新语法。
- JOIN ON 不写该版本不支持的不等式条件；改用 `sumIf` / `minIf` 等。
- `dt` 等 String 日期字段不要和 Date 直接比较。
- SQL alias 尽量 ASCII，避免 driver 中文 alias 编码问题。尤其是 `clickhouse_driver.query_dataframe()`：中文 alias 可能在服务端 SQL 报错时触发异常信息 UTF-8 解码失败，掩盖真实错误；做法是 SQL 层用 ASCII alias，pandas/导出层再 rename 成中文列名。
- 默认不用表名带 `local` 的表。

ODPS 特别检查：

- 分区字段和日期条件是否可裁剪。
- `${param}` / 模板参数是否替换正确。
- 函数、类型转换、窗口函数是否符合 MaxCompute 方言。

### 第四步：本地运行测试
输出给用户前必须先本地跑测试，除非用户只要求草稿 SQL 且明确接受未运行。

测试顺序：

1. 小日期范围 / `LIMIT` 先跑通。
2. 检查是否报语法、字段、类型、权限错误。
3. 检查返回行数是否合理。
4. 对关键枚举值 / join 命中率 / 金额单位做 sanity check。
5. 再跑正式范围。

### 第五步：测试通过后再输出
最终输出：

- 可直接执行 SQL。
- 实际结果或结果文件路径。
- 数据源选择理由。
- 使用表和关键字段。
- 口径说明。
- 如果仍有未确认假设，明确列出。

如果测试失败：先修 SQL 或切换数据源，不要把失败 SQL 当成最终答案。

## 常见业务查询口径

### 好友关系/订单维度导出修正

当用户从用户级好友关系导出切换到“订单维度、只看前端订单”时，不要沿用用户级聚合。应先按订单行筛选，再按 `union_id` 回填学习、交接、企微好友摘要。

已验证的前端订单基础过滤：

```sql
pay_status_name = '支付成功'
AND new_front_end_name = '大前端'
AND main_first_level = '课程'
AND union_id != ''
```

首款 `<1000` 且无尾款的订单口径：

```sql
pay_type_code = 1
AND pay_amount < 1000
AND refund_amount <= 0
AND flow_no NOT IN (
  SELECT relate_flow_no
  FROM dwd_order_flow_df
  WHERE pay_status_name = '支付成功'
    AND pay_type_code = 2
    AND relate_flow_no != ''
)
```

注意：尾款排除不要只在前端订单子集里查；应在订单表中查所有支付成功尾款的 `relate_flow_no`，否则可能漏掉非前端口径记录的关联尾款。

“是否在正价班”不要只用用户任意订单 `max(is_official)`。订单维度导出建议同时输出：
- `订单是否正价课`：当前订单 `dwd_order_flow_df.is_official`
- `是否在正价班_交接判断`：优先用 `tock_handover_plus.service_camp_name/service_camp_stage`
- `是否在正价班_微信辅助`：交接未命中时，可用“订单正价 + 当前企微好友”作为辅助，不要把企微好友关系单独当成进班证据。

### 前端 880 以上课程 GMV 占比

用户问“前端 880 以上课程 GMV 占总 GMV 占比，看全部 SKU 和声乐 SKU”时，已验证可用 ClickHouse 表 `dwd_order_flow_df` 快速出数。默认口径：

- 前端：`new_front_end_name = '大前端'`
- 支付成功：`pay_status_name = '支付成功'`
- GMV：`pay_amount`
- 880 以上课程 GMV：`main_first_level = '课程' AND total_original_price >= 880` 的 `pay_amount`
- 声乐 SKU：`main_goods_sku = '声乐'`
- 时间范围未说明时不要假装确定；可按上下文默认今年至今，但回复中必须明示假设。若用户要正式结果，优先问或标明时间范围。

ClickHouse 21.8 注意：不要在同一层里写 `round(sum(x) / sum(y))` 时又复用 `sum(x) AS x_alias` 这类聚合别名，可能触发 `Aggregate function ... is found inside another aggregate function`。做法是先在子查询聚合出 `total_gmv`、`gmv_880_plus`，外层再算占比。

推荐 SQL 形态：

```sql
SELECT
    scope,
    round(total_gmv, 2) AS total_gmv,
    round(gmv_880_plus, 2) AS gmv_880_plus,
    round(gmv_880_plus / nullIf(total_gmv, 0), 6) AS ratio
FROM
(
    SELECT
        scope,
        sum(pay_amt) AS total_gmv,
        sum(gmv_880_amt) AS gmv_880_plus
    FROM
    (
        SELECT
            '全部SKU' AS scope,
            pay_amount AS pay_amt,
            if(main_first_level = '课程' AND total_original_price >= 880, pay_amount, 0) AS gmv_880_amt
        FROM dwd_order_flow_df
        WHERE pay_status_name = '支付成功'
          AND new_front_end_name = '大前端'
          AND pay_time >= toDateTime('${start_date} 00:00:00')
          AND pay_time < toDateTime('${end_date_exclusive} 00:00:00')
        UNION ALL
        SELECT
            '声乐SKU' AS scope,
            pay_amount AS pay_amt,
            if(main_first_level = '课程' AND total_original_price >= 880, pay_amount, 0) AS gmv_880_amt
        FROM dwd_order_flow_df
        WHERE pay_status_name = '支付成功'
          AND new_front_end_name = '大前端'
          AND pay_time >= toDateTime('${start_date} 00:00:00')
          AND pay_time < toDateTime('${end_date_exclusive} 00:00:00')
          AND main_goods_sku = '声乐'
    ) x
    GROUP BY scope
) y
ORDER BY scope;
```

## 常用实时验证 SQL

ClickHouse 常用探表 SQL：

```sql
SELECT table, name, type, position
FROM system.columns
WHERE database = currentDatabase()
  AND table IN ('tock_applet_user', 'dwd_order_flow_df', 'drh_emp_external_user', 'drh_emp_external_user_del')
ORDER BY table, position;
```

枚举值验证示例：

```sql
SELECT sku, count()
FROM tock_applet_user
GROUP BY sku
ORDER BY count() DESC
LIMIT 50;
```

```sql
SELECT pay_type_name, pay_status_name, count()
FROM dwd_order_flow_df
GROUP BY pay_type_name, pay_status_name
ORDER BY count() DESC
LIMIT 50;
```

## 已验证的本地规律

### ClickHouse 21.8 + drh 表
- 用户环境是 ClickHouse `21.8.2.1`
- `drh_*` 表常需要：
  - `FINAL`
  - `WHERE _sign > 0`
- `FINAL` 后不能直接别名，应该包子查询：

```sql
FROM (
    SELECT *
    FROM drh_emp_external_user FINAL
    WHERE _sign > 0
) AS e
```

### 这套 KB 要解决的真实坑
曾发生过：
- 直接按业务口径把 `tock_applet_user` 的商品字段写成 `main_goods_sku`
- 实际表里字段是 `sku`

所以：
- 业务口径 ≠ 物理字段名
- 必须先查 KB，再实时探表

## 验证刷新是否正常
看：
- `refresh_summary.json`
- 最新 `runs/refresh_*.json`

判断方法：
- ClickHouse 连续两次 `changed_count = 0` 或很小：通常正常
- ODPS 连续两次仍有少量 `changed`：通常是表元数据本身在变，不代表脚本坏了
- 如果 ODPS 突然 600+ 全量 changed，优先检查 inventory signature 逻辑是否被改坏

## 维护要求

如果本 skill 在实际使用中发现：
- 路径变化
- 刷新命令变化
- 产物格式变化
- 新的 CK/ODPS 语法坑

要立即 patch 本 skill，不要留旧信息。
