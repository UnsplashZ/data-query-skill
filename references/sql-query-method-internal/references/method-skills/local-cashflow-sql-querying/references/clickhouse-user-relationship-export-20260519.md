# 大批量 ClickHouse 用户关系导出：分块、断点与 Excel 写入教训

适用场景：用户要求导出数万用户的好友关系 / 企微关系 / 学习行为 / 订单标签，涉及 `dwd_order_flow_df`、`tock_emp_external_user`、`tock_qw_message_res`、`tock_ast_process_data` 等 ClickHouse 表。

## 本次验证出的稳定做法

1. 先用小查询确认各基础来源单独可跑：订单用户、学习记录、投诉关键词、服务信息、昵称手机号、消息互动。
2. 不要把所有关系和消息都塞进一个大 SQL；ClickHouse 21.8 容易出现：
   - `Max query size exceeded`，特别是 `union_id IN (...)` 太长；
   - `JOIN ON` 不支持非等值条件；
   - 大 JOIN 长时间无输出，无法判断进度。
3. 好友关系大表应分块查；在本次任务中：
   - `CHUNK_SIZE=500`：稳定推进，82 批时每 10 批约 3 分钟；完整约 25 分钟；
   - `CHUNK_SIZE=1000`：批数少但单批变慢/不稳定；
   - `CHUNK_SIZE=2000`：容易卡在第一批好友关系查询。
4. 对长任务必须打印进度并 `flush=True`，例如：
   - `base rows=...`
   - `friend chunks i/n, rows=...`
   - `friend rows=...`
5. 更稳的后续改造方向：每个好友关系 chunk 写临时 CSV/Parquet，完成后再合并，避免 20+ 分钟任务在最后 Excel 写入失败后全部重跑。

## ClickHouse 语法/兼容性坑

- 不要在 `JOIN ON` 中放 `msgtime >= ...` 这类非等值条件；先在消息子查询 `WHERE` 中过滤。
- `maxIf(x, pay_time)` 是错的，`If` 后缀最后一个参数必须是布尔条件；按时间取最新值用 `argMax(x, pay_time)`。
- 避免 `WITH now_dt AS toDateTime(...)` 这类表达式别名，当前环境曾报语法错误；直接内联 `toDateTime('...')` 更稳。
- 大量 `union_id IN (...)` 要控制批大小，避免 `Max query size exceeded`。

## 数据源口径

- 订单/退费/付款标签：`dwd_order_flow_df`
- 首款未付尾款：`pay_type_code=1` 首款，反查是否存在 `pay_type_code=2` 且 `relate_flow_no = 首款 flow_no` 的尾款。
- 好友关系：`tock_emp_external_user`
- 当前好友判断：`del_time IS NULL OR del_time <= toDateTime('1971-01-01 00:00:00')`
- 企微消息：`tock_qw_message_res`
- 学习记录：`tock_ast_process_data`
- 服务/交接：`tock_handover_plus`
- 昵称/手机号：不要从 `dwd_order_flow_df` 取；该表不含 `nick_name` / `phone`。可从 `drh_live_user FINAL` 补。

## Excel 写入前的 DataFrame 防错

长查询完成后，最容易在最后一步因列不齐失败。原因通常是有好友关系用户和无好友关系用户拼接后，不同 DataFrame 列集合不一致。

写 Excel 前必须对每个目标 sheet 的 DataFrame 补齐列：

```python
for df in [refund, first, high]:
    for c in expected_cols:
        if c not in df.columns:
            df[c] = pd.NA
```

注意：补列要补到最终 `refund / first / high`，不是只补 `merged`，否则 `refund[cols_common]` 仍可能 `KeyError`。

## 推荐输出结构

Excel 至少包含：

- `00_口径说明`
- `01_汇总`
- `02_退费用户好友关系`
- `03_首款小于1000未退费`
- `04_付款大于880高意向`

对用户汇报时只说：文件路径、sheet 行数、核心口径和未验证/风险点。不要把中间失败堆给用户，除非解释当前状态需要。
