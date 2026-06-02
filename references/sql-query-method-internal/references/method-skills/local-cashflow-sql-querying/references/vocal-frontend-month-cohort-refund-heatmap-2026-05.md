# 声乐前端支付月 × 后续退款月 cohort 退费热力图（2026-05）

## 适用场景

用户要看“类似甘特图”的 cohort 退费率：按支付自然月 cohort，观察这些订单在后续每个自然月里发生的退款率。

推荐形式不是传统条形甘特，而是 **支付月 × 退款月偏移 M0/M1/... 的热力图矩阵**。

## 默认口径

- 数据源：ClickHouse
- 支付分母：`dwd_order_flow_df`
- 退款分子：`tock_dwd_order_refund_df`
- 时间范围：可按用户要求；本次为 `2025-01-01` 至运行当天
- 支付状态：`pay_status_name = '支付成功'`
- 声乐：`cci3_name = '声乐'`
- 前端：`new_front_end_name LIKE '%前端%'`
- 退款发生日：必须用 `tock_dwd_order_refund_df.refund_time`

两个常用 scope：

1. 全部声乐前端订单
2. 核心课：额外加
   - `main_first_level = '课程'`
   - `total_original_price >= 1880`
   - `pay_type_name IN ('全款', '尾款')`

## 指标定义

### 月发生 cohort 退费率（热力图主指标）

```text
单元格 = 该支付月 cohort 在对应后续退款自然月发生的退款 GMV / 该支付月 cohort GMV
```

- 行：支付自然月 cohort，例如 `2025-01`
- 列：退款月相对支付月偏移
  - `M0` = 支付当月
  - `M1` = 支付后次月
  - `M2` = 支付后第 2 个月
- 分母固定为该支付月 cohort 的 `sum(pay_amount)`
- 分子为对应退款发生自然月的 `sum(refund_amount)`

### 累计 cohort 退费率（Excel 辅助指标）

```text
累计单元格 = 截至该后续退款月累计退款 GMV / 该支付月 cohort GMV
```

用于补充观察释放节奏，不建议和月发生率混在一张热力图上。

## 未来未观察月份处理

不要把尚未完整进入的后续月份铺成 0。

例如当前是 2026-05：
- 2026-04 cohort 的 M2、M3... 是未来未观察，不是 0
- 图上应显示为灰色或空值
- 脚注写明“灰色单元格为该支付月尚未完整进入的后续月份，不按 0 处理”

实现上：

```python
end_month_start = pd.Timestamp(END_DATE).to_period('M').to_timestamp()
available_max_offset = (end_month_start.year - pay_month_start.year) * 12 + (end_month_start.month - pay_month_start.month)
```

只为每个 cohort 铺到 `available_max_offset`。

## 输出建议

图片：

```text
~/.hermes/output/query_results/cohort_refund_rate/声乐前端cohort退费率_支付月x退款月_甘特热力图_2025年至今_<timestamp>.png
```

Excel：

```text
~/.hermes/output/query_results/cohort_refund_rate/声乐前端cohort退费率_支付月x退款月_甘特热力图_2025年至今_<timestamp>.xlsx
```

Excel sheets：

- `月发生退费率矩阵_全部订单`
- `月发生退费率矩阵_核心课`
- `累计退费率矩阵_全部订单`
- `累计退费率矩阵_核心课`
- `月度汇总`
- `长表明细`
- `SQL`

## 图表版式要点

- 上下两张子图：全部订单、核心课
- 色条放在图表右侧外部，不能压住热力图主体
- 灰色表示未来未观察月份
- 只标注有意义的单元格，例如：
  - `>= 0.3%`
  - 或 M0 中非零值
- 脚注必须写清楚：
  - 声乐字段
  - 前端字段
  - 单元格公式
  - 退款发生日字段
  - 灰色格含义

## 本次脚本

已生成的可复用脚本：

```text
/Users/zheng/.hermes/scripts/cohort-refund-rate/vocal_frontend_cci3_month_cohort_heatmap.py
```

运行：

```bash
/opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python /Users/zheng/.hermes/scripts/cohort-refund-rate/vocal_frontend_cci3_month_cohort_heatmap.py
```

## 业务解读模式

读图时区分：

- `M0` 高：支付当月退费异常，偏成交承诺/即时反悔/交接初期问题
- `M1` 高：支付后次月释放，通常是首个完整承接周期后的退款
- `M2+` 高：后续履约或长期预期落差问题

本次观察：

- 退费主要集中在 `M0-M2`，其中多数历史月份 `M1` 最明显
- 2026-03/04 的异常主要体现在 `M0` 支付当月退费率明显抬升：
  - 全部订单：2026-03 M0 约 3.3%，2026-04 M0 约 2.9%
  - 核心课：2026-03 M0 约 3.1%，2026-04 M0 约 2.4%
- 因此可表述为：3 月开始不只是后续退款释放变多，而是支付当月已经明显异常。

## 常见坑

1. 不要使用 `dwd_order_flow_df.refund_amount` 做退款发生月回放；它会把当前累计退款归因回支付订单，污染历史时间。
2. 不要把尚未观测的未来月份当 0，否则会误导较新 cohort 后续退费已经低。
3. 不要只输出图片；同时输出 Excel 长表和 SQL，便于审计。
4. 如果用户后续要求写入飞书报告，不要追加到末尾；应插入趋势/退费释放节奏相关章节。