# 历史首款 / 休学冻课 / 未分配明细最新口径（2026-05-08）

## 适用场景

维护 Feishu 表：
`<REDACTED_FEISHU_URL>`

主脚本：
`/Users/zheng/.hermes/python/projects/first-payment-only/refresh_feishu_with_class_attendance.py`

最新导出：
- 本地完整四表：`/Users/zheng/.hermes/output/query_results/20260508_历史首款_冻课学员_补上课情况.xlsx`
- 明细拆分附件：`/Users/zheng/.hermes/output/query_results/冻课明细_未分配明细_补手机号商品名称_20260508.xlsx`
- 当前 SQL：`/Users/zheng/.hermes/output/query_results/休学冻课_未分配_当前口径_补手机号商品名称_20260508.sql`

## 最新业务口径

### 休学冻课池

来源：`tock_handover_plus t` LEFT JOIN `drh_handover_plus FINAL WHERE _sign > 0` 聚合后的 `drh_valid d`。

条件：
```sql
WHERE t.order_no != ''
  AND (
      multiMatchAny(t.service_camp_name, ['冻课', '休学', '延期'])
      OR d.stop_study_status = 1
  )
```

注意：不要加 `AND t.service_camp_name != ''`。用户确认服务营期为空但 `drh_handover_plus.stop_study_status=1` 的订单也应进入休学。

### 未分配池

只来自 `tock_handover_plus`：
```sql
WHERE order_no != ''
  AND service_camp_name = ''
  AND service_emp_name = ''
  AND order_no NOT IN (SELECT flow_no FROM stop_study_flag)
```

关键纠正：不要再 `UNION ALL` 这段：
```sql
SELECT order_no AS flow_no
FROM tock_order
WHERE order_no NOT IN (SELECT order_no FROM tock_handover_plus)
  AND pay_type IN ('全款','尾款')
  AND first_level = '课程'
```
原因：这会把大量“只是没进交接表/表关联缺失”的正常订单误算进未分配，导致未分配异常偏大。

### 最终统计限制

休学和未分配最终汇总/明细都只统计课程支付成功订单：
```sql
matched_paid_course_order = 1
```
其来源是 `dwd_order_flow_df`：
```sql
main_first_level = '课程'
AND pay_status_name = '支付成功'
```

## 最新校验结果

当前口径跑数后：

- 休学原始命中：11,931；匹配课程支付成功：11,603；未匹配：328
- 未分配原始命中：38,654；匹配课程支付成功：38,035；未匹配：619

最终汇总（课程支付成功）：

休学：
- 订单数：11,603
- 学员数：11,190
- 支付金额：29,139,064.58
- 退款金额：2,221,306.19
- 退费率：7.62%

未分配：
- 订单数：38,035
- 学员数：34,171
- 支付金额：87,935,528.95
- 退款金额：23,593,104.92
- 退费率：26.83%

声乐：
- 休学 × 声乐：8,774 单、8,559 学员、支付金额 22,644,768.88、退款金额 1,538,536.36、退费率 6.79%
- 未分配 × 声乐：21,420 单、19,929 学员、支付金额 50,081,180.94、退款金额 16,800,168.96、退费率 33.55%

## 明细字段

休学/未分配明细常用字段应包括：
- 成交人：优先 `dwd_order_flow_df.order_emp_name`，兜底 `tock_order.emp_name`
- 交接学管：`dwd_order_handover_df.ast_emp_name`
- 手机号：`tock_applet_user.phone`，按 `union_id` 匹配，取 `argMaxIf(phone, create_time, phone != '')`
- 商品名称：优先 `dwd_order_flow_df.main_goods_name`，兜底 `tock_order.goods_name`
- 课包价格：优先 `dwd_order_flow_df.total_original_price`，兜底 `tock_order.goods_price`
- 成交营期阶段：优先 `dwd_order_handover_df.class_stage_name`，兜底 `tock_order.class_stage`

## Feishu 写入坑和修复

飞书单 sheet 单元格上限约 5,000,000。旧 `冻课明细` sheet 曾保留 173,625 行，追加列时报：
```text
cells excess:5000000
```

处理路径：
1. 先算待写入单元格：`(len(df)+1) * len(df.columns)`。
2. 如果旧 sheet 已膨胀，即使待写数据较小，追加列也可能因旧行数×新列数超过限制失败。
3. 可删除多余列；若仍不稳，重建明细 sheet：新增临时 sheet、删除旧 sheet、重命名临时 sheet 为原标题。
4. 重新 `list_sheets()` 获取新 sheet_id，不要继续使用旧 id。
5. 写入后读取 `A1:D3` 验证。

本次重建后 `冻课明细` sheet_id 从 `35dI3g` 变为 `2BG2di`。

Feishu 最新成功写入：
- `首款订单汇总`：64 行 × 8 列
- `首款订单明细`：137,041 行 × 20 列
- `冻课汇总`：79 行 × 6 列
- `冻课明细`：合并休学+未分配时 49,635 行 × 35 列，单元格约 1,737,260，未超限

## 用户沟通偏好

当用户只要现状/结果时，不要解释口径来源和 SQL 细节；直接给当前规模、关键风险和表链接。技术口径细节保存在 SQL/技能文档中即可。
