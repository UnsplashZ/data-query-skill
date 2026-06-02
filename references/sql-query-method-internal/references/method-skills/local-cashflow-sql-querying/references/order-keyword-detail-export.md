# 订单商品名称关键词明细导出

适用场景：用户要求“导一份某月所有商品名称包含 A 或 B 的订单明细”。

## 推荐数据源

优先使用 ClickHouse `dwd_order_flow_df`，适合快速导出订单流水明细。

关键字段：
- 时间：`pay_time`
- 商品名称：`main_goods_name`
- 支付状态：`pay_status_name`
- 金额：`pay_amount`、`refund_amount`、`net_received_amount`
- 订单唯一键：`flow_no`
- 用户唯一键：`union_id`

## 默认口径

如果用户只说“5月”等自然月，按当前年份自然月处理，并在交付时明示，例如：

```sql
pay_time >= toDateTime('2026-05-01 00:00:00')
AND pay_time < toDateTime('2026-06-01 00:00:00')
```

若用户说“订单明细”且未说明是否包含未支付，默认导出：

```sql
pay_status_name = '支付成功'
```

关键词匹配建议使用 ClickHouse 的 `positionUTF8`，避免中文字符串匹配问题：

```sql
AND (
  positionUTF8(main_goods_name, '维也纳') > 0
  OR positionUTF8(main_goods_name, '金色大厅') > 0
)
```

## 导出形态

用户要“导一份”时优先给 `.xlsx`，至少包含：
- `口径说明`
- `汇总`
- `状态校验`
- `订单明细`
- `字段校验`
- `SQL`

推荐验证：
1. 先查 `system.columns` 确认字段存在。
2. 跑状态分布，确认匹配关键词后有哪些 `pay_status_name`。
3. 正式明细按 `pay_status_name='支付成功'` 导出。
4. 汇总验证：`count()`、`uniqExact(flow_no)`、`uniqExact(union_id)`、`sum(pay_amount)`、`sum(refund_amount)`、`sum(net_received_amount)`。
5. 重新打开 Excel 验证 sheet、行数、金额列是数值类型。

## 已验证样例

2026 年 5 月商品名称包含“维也纳”或“金色大厅”的支付成功订单：
- 明细行数：75
- 流水去重数：75
- 用户去重数：53
- 实付金额合计：1,648,883
- 退款金额合计：91,800
- 实收金额合计：1,557,083

当用户随后说“文件发我”，不要只返回本地路径；在 Feishu 对话中使用 final response 的 `MEDIA:/absolute/path.xlsx` 触发附件发送。