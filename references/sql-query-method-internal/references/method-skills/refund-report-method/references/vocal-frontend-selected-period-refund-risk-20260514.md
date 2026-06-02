# 声乐前端：选期/未选期与 D4-D14 退费风险验证（2026-05-14）

## 适用场景
当用户怀疑“交接强要求 / 选期流程走不通”导致 D4-D14 退费偏高时，不要只按交接状态解释；应进一步拆成 `已选期` vs `未选期`，并同时展示 GMV、退费额、退费率。

## 推荐口径
- 范围：声乐 + 前端 + 课程 + 全款/尾款。
- 支付 cohort：按 `dwd_order_flow_df.pay_time`。
- M0 退费：同支付月内的 `tock_dwd_order_refund_df.refund_time`。
- D4-D14：`dateDiff('day', pay_time, refund_time) BETWEEN 4 AND 14`。报告中应统一写 D4-D14，不写 D4-D15，除非分桶实际包含 D15。
- 已选期：`dwd_order_handover_df` 中同一 `flow_no` 存在 `class_camp_id > 0 AND class_camp_name != ''`。
- 未选期：不满足上述条件。

## 已验证示例：2026-04 声乐前端 M0
| 状态 | GMV | M0退费额 | M0退费率 | D4-D14退费额 | D4-D14退费率 |
|---|---:|---:|---:|---:|---:|
| 已选期 | 288.50万 | 3.90万 | 1.35% | 2.91万 | 1.01% |
| 未选期 | 64.70万 | 5.29万 | 8.18% | 4.32万 | 6.67% |

解释：未选期 M0 退费率约为已选期的 6.1 倍，未选期 D4-D14 退费率约为已选期的 6.6 倍。该结果支持“未选期/未完成选期链路是 4月 D4-D14 高退费的主要风险池”。

## 分析表达边界
可以写：
> D4-D14 退费与未选期状态高度相关，未选期订单池是主要风险池。

不要直接写：
> 交接强要求导致退费。

原因：当前数据能证明状态相关性和风险集中，但未必有退费发起人、交接失败原因、销售主动/被动退费字段。若要验证强因果，需要补充：
1. 退费发起人 / 审批人 / 提交人字段。
2. 未选期原因 / 交接失败原因。
3. 退费前是否已经有明确选期推进、拒绝、改期、无法联系等过程记录。

## 图表建议
- 至少画两组柱：M0 退费率、D4-D14 退费率。
- 图中文字必须带 GMV 和退费额，不只展示百分比。
- 如果用于 Feishu Docx，图片可命名为 `06_selected_vs_unselected_refund_rate.png`，正文放在交接/选期假设验证段落后。

## SQL 形态提示（ClickHouse）
用 `dwd_order_flow_df` 作支付分母，用 `tock_dwd_order_refund_df` 作退费分子，用 `dwd_order_handover_df` 聚合同一 `flow_no` 的选期状态：

```sql
WITH handover AS (
    SELECT
        flow_no,
        max(if(class_camp_id > 0 AND class_camp_name != '', 1, 0)) AS has_selected_period
    FROM dwd_order_handover_df
    WHERE flow_no != ''
    GROUP BY flow_no
), orders AS (...), refunds AS (...)
SELECT
    if(h.has_selected_period = 1, '已选期', '未选期') AS period_status,
    sum(pay_amount) AS gmv,
    sum(refund_amount) AS refund_amount,
    refund_amount / nullIf(gmv, 0) AS refund_rate,
    sumIf(refund_amount, pay_to_refund_days BETWEEN 4 AND 14) AS d4_14_refund_amount,
    d4_14_refund_amount / nullIf(gmv, 0) AS d4_14_refund_rate
FROM ...
GROUP BY period_status;
```

## 常见坑
- 不要把 `join_group_time` 等同于“已选期”。本次验证使用 `class_camp_id + class_camp_name` 表示选期状态。
- 不要只按金额排序判断风险；选期/未选期、渠道来源都必须同时展示 GMV、退费额、退费率。
- 对未选期高退费只能说“支持风险池判断”，不能说已经证明销售主动/被动退费。
