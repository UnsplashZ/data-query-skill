# 退款预测：目标自然月当月退费率 vs 截至目标月累计退费率

场景：用户纠正退款预测口径——预测表里的退费率应表示“任意支付月 GMV 在 6月当月产生的退费率”，不是“截至 6月底的累计退费率”。

## 正确口径

对目标月 `target_month`（例如 2026-06）：

```text
X月GMV在6月当月退费率 = X月支付GMV在 2026-06 自然月产生的退费金额 / X月支付GMV
```

这只取支付月到目标月之间的单个 lag：

```text
lag = month_diff(target_month, pay_month)
当月退费率 = lag 对应的 refund_amount / pay_month_gmv
```

不要把 `lag <= current_lag` 的退款累计起来。

## 易错点

旧版预测逻辑同时输出最终/累计预测字段，容易把这些字段误填进“6月当月退费率”：

- `predicted_final_refund_rate`：最终或累计预测口径，不是目标自然月当月退费率。
- `cum_refund_rate` / `cumN_rate`：截至某月龄累计口径，不是自然月现金流口径。

面向业务输入/预测表时，应清楚区分：

- `predicted_current_month_refund_rate`：目标自然月当月退费率。
- `predicted_final_refund_rate`：最终/累计退费率，只能用于最终退费率预测或 cohort 成熟度判断。

## 推荐测试夹具

构造一个支付月 GMV=1000 的 cohort：

```text
M0 = 100 / 1000 = 10%
M1 = 80 / 1000 = 8%
M2 = 40 / 1000 = 4%
M3 = 30 / 1000 = 3%
```

当目标月是 M2 时：

```text
目标月当月退费率 = 4%
截至目标月累计退费率 = 22%
最终预测退费率 = 25%（若还预测 M3）
```

验证重点：当目标月是 M2，预测表的“当月退费率”必须是 4%，不是 22% 或 25%。

## 实现建议

在自然月现金流预测函数中同时保留两个字段，避免业务表误用：

```text
predicted_current_month_refund
predicted_current_month_refund_rate
predicted_final_refund
predicted_final_refund_rate
```

导出 Excel 或 Feishu 表时，凡是列名写“X月GMV在6月当月退费率”或“6月预计退费率”的，应使用 `predicted_current_month_refund_rate` 这一类当月字段；只有明确写“截至6月底累计退费率”时，才可使用累计字段。
