# 声乐指定多轨次 GMV / 课程类GMV / 平均续费间隔（2026-05-11）

## 适用场景

用户给出一批 `camp_group_name` 轨次名，要求同时输出：
- GMV
- 课程类GMV
- 平均续费间隔

本次示例轨次：
- 声乐二阶-20251209-院长班
- 声乐二阶-20251223-院长特惠班
- 声乐二阶-20251224-赵曼院长班-BLT
- 声乐二阶-20260106-院长班
- 声乐二阶-20260113-院长班BLT
- 声乐二阶-20260127-院长特惠班
- 声乐二阶-20260203-院长班
- 声乐三阶-20251118-进阶班
- 声乐三阶-20260106-进阶班
- 声乐四阶-20251111-名师班

## 核心口径

### 1. GMV / 课程类GMV：订单所属营期口径

来源：
- `dwd_order_flow_df f`
- `dim_camp_df c ON f.camp_id = c.camp_id`

轨次识别：
- `c.camp_group_name`
- 如果末尾有 `(二)` / `（二）`，用 `replaceRegexpAll(camp_group_name, '[(（]二[)）]$', '')` 合并到无后缀轨次。

指标：
- `GMV = sum(f.pay_amount)`，条件 `f.pay_status_name='支付成功'`
- `课程类GMV = sumIf(f.pay_amount, f.main_first_level='课程')`
- `支付订单数 = uniqExact(f.flow_no)`
- `课程类支付订单数 = uniqExactIf(f.flow_no, f.main_first_level='课程')`

注意：
- 这里的 GMV 是全部支付成功订单，不限制 `main_first_level`。
- 课程类GMV 才限制 `main_first_level='课程'`。

### 2. 平均续费间隔：严格 handover 锚点口径

来源：
- `dwd_order_handover_df h` 提供该轨次学员与 `track_pay_time` 锚点
- `dwd_order_flow_df f2 + dim_camp_df c2` 提供同轨次同阶段课程订单

规则：
1. `handover_base` 按 `class_stage_name + normalized camp_group_name + union_id` 聚合。
2. `track_pay_time = min(h.pay_time)`。
3. 在同 `union_id + class_stage_name + normalized camp_group_name` 的订单里，只保留：
   - `pay_status_name='支付成功'`
   - `main_first_level='课程'`
   - `renewal_pay_time >= track_pay_time`
4. 用 `minIf(renewal_pay_time, renewal_pay_time >= track_pay_time)` 取首笔课程续费时间。
5. `平均续费间隔(天) = avgIf(dateDiff('day', track_pay_time, first_course_renewal_pay_time), first_course_renewal_pay_time > toDateTime('1970-01-02 00:00:00'))`

ClickHouse 21.8 注意：
- 不要把 `renewal_pay_time >= track_pay_time` 写进 `JOIN ON`。
- 先按用户/轨次/阶段等值 join，再用 `sumIf` / `minIf` 写时间条件。

## 输出字段建议

- 营期阶段
- 轨次
- 合并包含轨次
- 最新结课时间
- 支付用户数
- 支付订单数
- GMV
- 课程类支付用户数
- 课程类支付订单数
- 课程类GMV
- 交接用户数
- 可计算续费间隔用户数
- 间隔覆盖课程GMV
- 间隔用户覆盖率
- 间隔GMV覆盖率
- 平均续费间隔(天)

## 已保存 SQL

本次生成并验证通过的 SQL：

`/Users/zheng/.hermes/sql/clickhouse/track-gmv-course-gmv-interval-selected-vocal-20260511.sql`

上一个只含 GMV / 课程类GMV 的版本：

`/Users/zheng/.hermes/sql/clickhouse/track-gmv-course-gmv-selected-vocal-20260511.sql`

## 验证结果

执行环境：`/opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python` + `clickhouse_driver`。

导出文件：

`/Users/zheng/.hermes/output/query_results/track_gmv_course_gmv/指定声乐轨次_GMV课程类GMV_含平均续费间隔_20260511_105619.xlsx`

验证项：
- ClickHouse SQL 执行成功。
- Excel 回读行列数与 DataFrame 一致。
- `GMV`、`课程类GMV`、`平均续费间隔(天)` 为数值单元格。

关键结果：

| 营期阶段 | 轨次 | 支付订单数 | GMV | 课程类订单数 | 课程类GMV | 可计算续费间隔用户数 | 平均续费间隔(天) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 三阶营期 | 声乐三阶-20251118-进阶班 | 1708 | 5219121.90 | 1229 | 4065206.00 | 980 | 254.8918 |
| 三阶营期 | 声乐三阶-20260106-进阶班 | 2049 | 6358630.00 | 1363 | 5047211.00 | 1138 | 222.8005 |
| 二阶营期 | 声乐二阶-20251209-院长班 | 1292 | 1705120.66 | 710 | 1378444.00 | 472 | 133.4449 |
| 二阶营期 | 声乐二阶-20251223-院长特惠班 | 752 | 744736.00 | 404 | 603147.00 | 267 | 127.2959 |
| 二阶营期 | 声乐二阶-20251224-赵曼院长班-BLT | 122 | 303443.00 | 122 | 303443.00 | 67 | 129.4179 |
| 二阶营期 | 声乐二阶-20260106-院长班 | 1484 | 1918141.90 | 774 | 1564051.90 | 548 | 113.9434 |
| 二阶营期 | 声乐二阶-20260113-院长班BLT | 653 | 1132461.75 | 356 | 847276.85 | 262 | 88.0458 |
| 二阶营期 | 声乐二阶-20260127-院长特惠班 | 695 | 809620.66 | 396 | 652417.66 | 287 | 123.3415 |
| 二阶营期 | 声乐二阶-20260203-院长班 | 832 | 1195936.00 | 439 | 984043.00 | 360 | 108.7694 |
| 四阶营期 | 声乐四阶-20251111-名师班 | 722 | 3303383.00 | 505 | 2534652.00 | 413 | 290.1404 |

## Pitfalls

- 不要把“平均续费间隔”的分母直接设为订单所属营期 GMV 的所有用户；它只能在有 handover 锚点并能找到首笔课程续费订单的用户上计算。
- 不要把“GMV”和“课程类GMV”都限制成 `main_first_level='课程'`；用户同时要两列时，GMV 是总支付成功订单，课程类GMV 才是课程限制。
- ClickHouse driver 可能把 `t.stage_name` 这类选择列命名成 `t_stage_name`，Python rename 时要兼容带表别名前缀的列名。
- 用户面向结果文件时，导出 Excel 要用中文表头和数值单元格，并回读验证。
