# SKU × 前后端 6月累计退费金额预测 Excel 模板经验

场景：用户要做 6月分 SKU、前后端的退费金额预测，并希望业务侧只填写 5月真实完整 GMV 和 6月预测完整 GMV，即可得到 6月累计退费金额。

## 用户纠正后的口径

- SKU 字段：使用 `dwd_order_flow_df.cci3_name`，不要默认用 `main_goods_sku`。
- 前后端：从 `dwd_order_flow_df.new_front_end_name` 归并：
  - 包含 `前端` -> `前端`
  - 包含 `后端` -> `后端`
- GMV：`dwd_order_flow_df.pay_amount`，支付成功课程订单。
- 退费来源：`tock_dwd_order_refund_df.refund_amount`，用 `flow_no` 关联订单。
- 用户 2026-05-28 纠正后的口径：“X月GMV在6月预计退费率”指该支付月 GMV 在 6月当月产生的退费率，不是截至 6月底累计退费率。
  - 1月 -> 历史 M5 当月退费率
  - 2月 -> 历史 M4 当月退费率
  - 3月 -> 历史 M3 当月退费率
  - 4月 -> 历史 M2 当月退费率
  - 5月 -> 历史 M1 当月退费率，必须写上
  - 6月 -> 历史 M0 当月退费率
- 6月当月预计退费GMV公式：
  - `SUM(1月GMV×1月GMV在6月预计退费率, ..., 6月GMV×6月GMV在6月预计退费率)`
  - 这里的汇总金额是 6月当月预计发生退费，不是 1-6月累计到 6月底的退费。

## 用户偏好的简版 sheet

除详细明细/说明外，需要额外放一个简洁 sheet，最好排在第一个：

```text
SKU
前后端
1月GMV、2月GMV、3月GMV、4月GMV、5月GMV、6月GMV
1月GMV在6月预计退费率、2月GMV在6月预计退费率、...、6月GMV在6月预计退费率
6月累计退费GMV
```

注意：不要只给一个“预测退费率”列；每个月的 GMV 到 6月底的成熟度不同，所以 1-6月应分列。

## 建模建议

按 `SKU × 前后端 × 支付月` 聚合 GMV，再将退款按订单关联回支付月，计算退款月份相对支付月的 offset：

```text
offset = refund_month - pay_month
M0/M1/M2/... = 截至该 offset 的累计退款金额 / 支付月 GMV
```

预测某目标月在 6月底的退费率时，用同 SKU×前后端历史同月龄的加权累计退费率：

```text
目标月 2026-05：使用历史 M1 加权累计退费率
目标月 2026-06：使用历史 M0 加权累计退费率
```

如果样本稀疏，可以保留可人工覆盖的黄色输入单元格。

## ClickHouse 21.8 注意

ClickHouse 21.8 不支持在 `JOIN ON` 里写不等式，例如：

```sql
ON o.flow_no = r.flow_no
AND r.refund_time >= o.pay_month
```

稳妥做法：
- SQL 只拉订单明细和退款月度明细；
- 在 pandas 中按 `flow_no` merge，计算 `Period(refund_month) - Period(pay_month)` 得到 offset；
- 再聚合 cohort 累计退费率。

这样比强行把复杂 cohort offset 全写在 ClickHouse 里更稳定，也更方便写 Excel 公式。

## Excel 验证

生成后重新打开 workbook，验证：
- 简版 sheet 存在且排在前面；
- 表头顺序符合用户要求；
- `6月累计退费GMV` 是公式列；
- 5月 GMV、6月 GMV、各月预测退费率保留可覆盖格式；
- 说明里写清 SKU 字段是 `cci3_name`。
