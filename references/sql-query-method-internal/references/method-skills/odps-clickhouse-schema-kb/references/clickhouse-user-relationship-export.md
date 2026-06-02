# ClickHouse 大批量用户关系导出注意事项

适用场景：从 ClickHouse 按用户集合导出好友关系、企微互动、学习记录、订单标签等宽表，尤其是 `union_id IN (...)` 分批查询。

## 稳定做法

1. 先生成基础用户标签表/DataFrame，再按 `union_id` 分批查询关系明细，避免单个大 SQL 长时间无输出。
2. `IN (...)` 批量值不要过大。实测 5000 个较长 `union_id` 可能触发 `Max query size exceeded`；优先从 1000/批开始，必要时继续降到 500 或改用临时表/外部表。注意：分批只能解决 query size，不一定解决执行计划慢；如果组合 CTE / 多 JOIN 仍长时间无输出，应拆成多个独立小查询并在 pandas 中 merge。
3. ClickHouse 旧版本不支持在 `JOIN ON` 放非等值条件，例如：
   ```sql
   ON f.union_id = m.union_id
  AND m.msgtime >= toDateTime('2026-05-19 00:00:00') - INTERVAL 30 DAY
   ```
   应改成子查询先过滤：
   ```sql
   LEFT JOIN (
       SELECT union_id, emp_id, count() AS recent_qw_msg_cnt, max(msgtime) AS latest_qw_msg_time
       FROM tock_qw_message_res
       WHERE msgtime >= toDateTime('{AS_OF}') - INTERVAL 30 DAY
       GROUP BY union_id, emp_id
   ) m ON f.union_id = m.union_id AND f.emp_id = m.emp_id
   ```
4. `maxIf(x, pay_time)` 是错误写法，因为 `If` 后缀最后一个参数必须是布尔条件。按时间取最新字段用：
   ```sql
   argMax(x, pay_time)
   ```
5. 避免 `WITH now_dt AS toDateTime(...)` 这类表达式别名；在兼容性不确定时直接内联 `toDateTime(...)`。
6. pandas 读取 ClickHouse 结果时，关键列要显式 alias，例如：
   ```sql
   SELECT ou.union_id AS union_id
   ```
7. 当订单表缺少昵称/手机号时，不要臆造字段；可从 `drh_live_user FINAL` 取 `nick_name`, `phone`，并用 `_sign > 0 AND union_id != ''` 过滤。

## 导出验证清单

- 记录每类人群人数、订单数、金额合计。
- 记录好友关系行数与覆盖用户数。
- 抽样检查：退费/未退费、首款/尾款、近30天学习、近30天企微互动、当前好友状态、投诉过滤。
- Excel 写出后检查每个 sheet 行数，确认没有超过 Excel 单 sheet 上限。
- 未重新运行脚本或未抽样时，最终汇报必须写明“没验证”。
