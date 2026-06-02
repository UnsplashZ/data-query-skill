# SKU × 前后端月度退费金额预测 Excel 模板

适用场景：用户要一个可填写 GMV 的预测 Excel，按 SKU × 前后端预测未来自然月累计退费金额，优先用公式而不是只给静态结果。

## 推荐数据源

- 订单 GMV：ClickHouse `dwd_order_flow_df`
- 退费明细：ClickHouse `tock_dwd_order_refund_df`
- 粒度：支付月 × `main_goods_sku` × 前后端
- 前后端归并：
  - `new_front_end_name LIKE '%前端%'` -> `前端`
  - `new_front_end_name LIKE '%后端%'` -> `后端`

## 已验证字段注意

`tock_dwd_order_refund_df` 的订单关联字段是：

```sql
flow_no
```

不是 `order_no`。如果写成 `order_no` 会报缺字段。

退款金额字段：

```sql
refund_amount
refund_time
```

## 口径建议

默认订单范围：

```sql
pay_status_name = '支付成功'
AND main_first_level = '课程'
AND pay_time >= toDateTime('2025-01-01 00:00:00')
AND pay_time < toStartOfMonth(today())
```

退费范围建议与订单起点一致，并截止到本月月初前：

```sql
refund_time >= toDateTime('2025-01-01 00:00:00')
AND refund_time < toStartOfMonth(today())
```

这个口径是“截至当前已释放的累计退费金额按订单支付月归因”，不是严格同龄 D0/DN cohort。面向预测模板可用，但必须在说明 sheet 写明。

## 预测模型默认值

对每个 `SKU × 前后端`：

1. 优先用近 3 个成熟月加权退费率。
2. 如果近 3 个成熟月不足，用所有成熟月加权退费率。
3. 5 月如果尚未成熟，默认不纳入训练，只作为用户填写/校准参考。

公式：

```text
6月累计退费金额预测 = 6月预测完整GMV × 预测退费率
```

可选校准列：

```text
5月按预测率应退金额 = 5月真实完整GMV × 预测退费率
5月实际-预测差额 = 5月当前累计退费金额 - 5月按预测率应退金额
5月校准后预测退费率 = AVERAGE(预测退费率, 5月当前累计退费金额 / 5月真实完整GMV)
6月校准后累计退费金额预测 = 6月预测完整GMV × 5月校准后预测退费率
```

## ClickHouse 21.8 写法坑

避免同层复用聚合别名或聚合里再嵌聚合。先子查询聚合，再外层计算退费率。

Decimal 相除时显式转 Float64，避免 Decimal/Float64 类型冲突：

```sql
round(if(toFloat64(gmv) = 0, 0, toFloat64(refund_amount) / toFloat64(gmv)), 6) AS refund_rate
```

## Excel 输出结构

建议 sheet：

- `说明`：数据源、订单范围、GMV/退费口径、默认预测率、公式、限制
- `预测输入`：用户填写和公式列
- `历史月度明细`：支付月 × SKU × 前后端历史明细
- `字段校验`：实际字段探查结果
- `SQL`：完整 SQL

`预测输入` 建议高亮：

- 黄色：用户可填写/覆盖字段
  - `5月真实完整GMV_用户填写`
  - `6月预测完整GMV_用户填写`
  - `预测退费率_可覆盖`
- 绿色：公式字段
  - `6月累计退费金额预测`
  - 5月校准相关字段

导出后必须用 openpyxl 重新打开验证：

- sheet 是否存在
- 行数是否合理
- 公式列是否以 `=` 开头
- 金额/退费率单元格格式是否正确
