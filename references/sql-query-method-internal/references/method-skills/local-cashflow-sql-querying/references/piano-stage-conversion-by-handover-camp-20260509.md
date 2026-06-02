# 钢琴二/三/四阶交接营期转化统计（2026-05-09）

## 适用场景

用户要改造“钢琴二阶/三阶/四阶订单数据”的统计逻辑：

- 先从交接表获取 2024 年至今已经开课的钢琴二/三/四阶营期和交接学员数；
- 再统计这些学员在对应交接营期内是否产生目标订单；
- 按 `营期阶段 × 来源课包价格 × 目标课包价格` 输出交接学员数、转化人头数、目标订单数、转化率；
- 剔除还没充分转化的新营期。

## 最终口径

### 分母：交接学员

来源：`dwd_order_handover_df h LEFT JOIN dim_camp_df d ON h.class_camp_id = d.camp_id`

过滤：

```sql
h.sku = '钢琴'
h.class_stage_name IN ('二阶营期','三阶营期','四阶营期')
d.start_class_time >= toDateTime('2024-01-01 00:00:00')
d.start_class_time <= today()
d.start_class_time > toDateTime('2000-01-01 00:00:00')
h.union_id != ''
```

粒度：`class_camp_id × union_id`，同一学员同一交接营期只算一次。

### 来源课包价格

不要再用“上一阶段按 union_id 反查”的泛化逻辑。

在这类交接营期转化统计里，来源课包价格取交接表上的原始订单：

```text
dwd_order_handover_df.flow_no -> dwd_order_flow_df.flow_no -> total_original_price
```

实现时先在交接 CTE 取：

```sql
argMin(h.flow_no, h.pay_time) AS source_flow_no
```

再用 `source_flow_no` 回查原订单价格。

### 转化 / 目标订单

转化定义：同一 `union_id` 在对应交接营期 `class_camp_id` 下有支付成功课程订单。

订单池：`dwd_order_flow_df f LEFT JOIN dim_camp_df d ON f.camp_id = d.camp_id`

过滤：

```sql
f.pay_status_name = '支付成功'
f.main_first_level = '课程'
f.main_goods_sku = '钢琴'
f.pay_type_name IN ('全款','尾款')
f.union_id != ''
f.pay_time >= toDateTime('2023-01-01 00:00:00')
```

关联：

```text
f.union_id = h.union_id
f.camp_id = h.class_camp_id
```

注意：不要要求目标订单支付时间晚于开课时间。钢琴二/三/四阶目标订单常常在营期开课前支付。若加上 `pay_time >= start_class_time` 会严重低估转化。

同一学员同一营期多笔目标订单：取最早一笔作为目标课包价格。

### 成熟营期剔除

用户要求“按照时间分布，用分阶段成熟窗口；大的时间窗口可以放松到 24 年至今”。

根据本次历史支付时间分布，最终使用：

```text
二阶营期：开课满 130 天
三阶营期：开课满 180 天
四阶营期：开课满 300 天
```

本次验证的相对开课支付时间分布：

```text
二阶：P05=63，P25=80，P50=98，P75=112，P95=128
三阶：P05=113，P25=121，P50=140，P75=155，P95=171
四阶：P05=271，P25=271，P50=272，P75=274，P95=285
```

所以成熟判断：

```python
MATURE_DAYS_BY_STAGE = {
    '二阶营期': 130,
    '三阶营期': 180,
    '四阶营期': 300,
}

age_days = today - target_start_time
mature_flag = age_days >= MATURE_DAYS_BY_STAGE[target_stage_name]
```

### 转化率

输出表里同一 `营期阶段 × 来源课包价格` 的交接学员数作为分母。

```text
转化率 = 转化人头数 / 交接学员数
```

`目标课包价格` 为空的行表示未转化人群。

## 本次产物

脚本：

- `/Users/zheng/.hermes/python/projects/ad_hoc/piano_stage_conversion_by_handover_camp.py`

结果：

- `/Users/zheng/.hermes/output/query_results/piano_stage_conversion_by_handover_camp_20260509_145143.xlsx`
- `/Users/zheng/.hermes/output/query_results/piano_stage_conversion_by_handover_camp_20260509_145143.sql`

规模校验：

```text
交接明细：41,586 行
成熟窗口后：30,285 行
全部营期：166 个
纳入成熟窗口营期：126 个
汇总行数：238 行
```

成熟条件校验：

```text
二阶营期：纳入 96 个营期，交接学员 22,805，转化人头 9,611，转化率 42.14%
三阶营期：纳入 28 个营期，交接学员 6,213，转化人头 3,451，转化率 55.54%
四阶营期：纳入 2 个营期，交接学员 591，转化人头 183，转化率 30.96%
```

## 易错点

- 不要用当前订单的 `tock_order.goods_price` 当来源课包价格。
- 不要把“上一阶段来源价格”泛化到这个场景；本场景用户明确要从交接表先定人群和营期，来源价格应绑定交接表原始 `flow_no`。
- 不要用 `pay_time >= start_class_time` 判断目标订单是否在营期内；高阶续费订单通常发生在开课前。
- 不要用统一 90 天成熟窗口；对三阶/四阶会纳入仍未充分转化的营期。
- ClickHouse 21.8 不支持 JOIN ON inequality；复杂窗口逻辑更稳的方式是 Python 后处理或在 SQL 中用条件聚合。
