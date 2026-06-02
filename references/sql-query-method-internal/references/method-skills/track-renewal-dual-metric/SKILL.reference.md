---
name: track-renewal-dual-metric
description: 轨次续费双口径汇总：用宽口径算总GMV，用严格handover锚点口径算平均续费间隔与覆盖率。
---

# 轨次续费双口径 SQL

适用场景：
- 用户要看某个轨次的全部课程订单 GMV
- 同时又要保留严格定义的“续费间隔”
- 避免把没有 handover 锚点的用户强行纳入间隔计算

## 核心口径

### 1. 宽口径：总GMV / 全部用户 / 全部订单
来源：
- `dwd_order_flow_df`
- `dim_camp_df`

条件：
- `camp_group_name = <目标轨次>`
- `pay_status_name = '支付成功'`
- `main_first_level = '课程'`

输出：
- `全部下单用户数`
- `全部订单数`
- `总GMV`

### 2. 严口径：续费间隔
来源：
- `dwd_order_handover_df`
- `dwd_order_flow_df`
- `dim_camp_df`

规则：
- 先在 `dwd_order_handover_df` 里按 `union_id` 取该轨次最早 `pay_time` 作为 `track_pay_time`
- 再在目标轨次订单池里，找 `pay_time >= track_pay_time` 的首笔续费订单
- `平均续费间隔 = 首笔续费支付时间 - 轨次付费时间`

输出：
- `可计算续费间隔用户数`
- `间隔覆盖GMV`
- `间隔用户覆盖率`
- `间隔GMV覆盖率`
- `平均续费间隔(天)`

## 承接学员数 + 课程GMV续费率口径

当用户给一批轨次并要：`承接学员数 / GMV(含电商) / GMV(仅课程) / 续费率(课程GMV) / 平均续费间隔` 时，优先使用 handover-based 轨次续费汇总口径，而不是订单所属营期宽口径。

默认解释：
- `承接学员数` = `dwd_order_handover_df` 中 `class_stage_name + normalized camp_group_name + union_id` 去重人数。
- `GMV(含电商)` = 上述承接学员在同阶段同轨次订单池中、`pay_status_name='支付成功'` 且 `pay_time >= track_pay_time` 的全部 `pay_amount`。
- `GMV(仅课程)` = 同上，但限制 `main_first_level='课程'`。
- `续费率(课程GMV)` = `GMV(仅课程) / 承接学员数`，这是按承接学员数摊分的课程续费 GMV，不是人数转化率；如用户要人数口径，应输出 `课程续费人数 / 承接学员数`。
- `平均续费间隔` = 每个承接学员首笔课程续费订单 `pay_time - track_pay_time` 的天数均值。

已验证脚本/SQL 示例：
- SQL: `/Users/zheng/.hermes/sql/clickhouse/track-renewal-user-gmv-course-rate-selected-vocal-20260518.sql`
- Runner: `/Users/zheng/.hermes/python/clickhouse/run_selected_vocal_track_renewal_metrics_20260518.py`
- 输出目录: `/Users/zheng/.hermes/output/query_results/track_renewal_selected_vocal/`

## 为什么要双口径
如果不使用 handover 严口径：
- 总GMV 会更完整
- 但一部分用户没有 `track_pay_time` 锚点
- 这部分用户不能严格计算续费间隔

所以：
- **GMV 看宽口径**
- **间隔看严口径**

## SQL 文件
已保存到：
- `~/.hermes/sql/clickhouse/track-renewal-dual-metric.sql`

## 使用方法
1. 打开 SQL 文件
2. 把其中的轨次名替换为目标值（出现 4 处）
3. 在 ClickHouse 中执行

## 当前字段
- `营期阶段`
- `轨次`
- `全部下单用户数`
- `全部订单数`
- `总GMV`
- `可计算续费间隔用户数`
- `间隔覆盖GMV`
- `间隔用户覆盖率`
- `间隔GMV覆盖率`
- `平均续费间隔(天)`

## 已验证样例
轨次：`声乐二阶-20251224-赵曼院长班-BLT`

结果：
- 全部下单用户数：`113`
- 全部订单数：`120`
- 总GMV：`297483`
- 可计算续费间隔用户数：`67`
- 间隔覆盖GMV：`180962`
- 间隔用户覆盖率：`0.5929`
- 间隔GMV覆盖率：`0.6083`
- 平均续费间隔(天)：`129.4179`

## 注意事项
- 这套 SQL 适合单个轨次查询；如果要批量跑所有轨次，需要再做参数化或改成多轨次版本
- 如果同名轨次可能跨不同 `class_stage_name` 重复，保留 `class_stage_name` 联结是必要的
- `main_first_level = '课程'` 是当前已验证的课程口径
- 当用户同时要“GMV / 课程类GMV / 平均续费间隔”时，区分两个口径：GMV 用订单所属营期的全部支付成功订单；课程类GMV 才限制 `main_first_level='课程'`；平均续费间隔用 handover 锚点严口径。多轨次声乐示例与完整 SQL 见 `references/vocal-selected-tracks-gmv-course-gmv-interval-20260511.md`。

## 交接营期 cohort 转化率与本技能的边界

如果用户问的是“先从交接表获取已开课营期和交接学员，再统计这些学员在对应营期内的订单数 / 转化率”，不要套用本技能的单轨次 GMV / 平均续费间隔口径。

那类任务应走 `local-cashflow-sql-querying` 中的交接营期 cohort 口径，参考：
- `references/piano-stage-conversion-by-handover-camp-20260509.md`

关键差异：
- 分母是 `dwd_order_handover_df.class_camp_id × union_id` 的交接学员；
- 目标订单用 `dwd_order_flow_df.camp_id = class_camp_id` 识别对应营期订单；
- 目标订单可能在开课前支付，不能加 `pay_time >= start_class_time`；
- 需要显式剔除未充分转化的新开课营期。
