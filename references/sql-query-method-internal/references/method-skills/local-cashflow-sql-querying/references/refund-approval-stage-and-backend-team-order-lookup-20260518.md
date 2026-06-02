# 退款审批表阶段补充与后端团队订单查找经验（2026-05-18）

## 场景
用户要查声乐后端某团队/业务分类在 5 月是否有二阶、四阶订单，并确认 `tock_ods_feishu_refund_approval_detail_all_d` 是否能区分阶段。

用户给出的分类名：
- `4月尾单-0203正价-成都罗一豪`
- `4月尾单-0127小课包-成都罗一豪`
- `0210小课包上半程-成都罗一豪`

这些名称在当前库里不一定是标准轨次/营期名。不要只按 `camp_name` / `camp_group_name` 精确搜不到就结束，应继续查团队、人、订单、交接表字段。

## 已验证字段与表

### `dwd_order_flow_df`
相关字段：
- `flow_no`
- `collect_order_no`
- `union_id`
- `camp_id`
- `camp_name`
- `camp_sku`
- `main_goods_sku`
- `main_first_level`
- `main_goods_name`
- `pay_type_name`
- `total_original_price`
- `pay_amount`
- `refund_amount`
- `pay_time`
- `pay_status_name`
- `order_emp_name`
- `emp_team_name`
- `emp_group_name`
- `new_front_end_name`

注意：本次验证中“罗一豪”出现在 `order_emp_name`，不是 `emp_team_name` / `emp_group_name`。

### `dim_camp_df`
用于补轨次和阶段：
- `camp_id`
- `camp_name`
- `camp_group_id`
- `camp_group_name`
- `class_stage`
- `class_stage_name`
- `camp_sku`
- `start_class_time`

### `dwd_order_handover_df`
用于交接/轨次归属口径：
- `flow_no`
- `union_id`
- `class_camp_id`
- `class_camp_name`
- `camp_group_id`
- `camp_group_name`
- `class_stage_name`
- `pay_time`

### `tock_ods_feishu_refund_approval_detail_all_d`
审批表自身字段不含阶段/营期：
- 没有 `class_stage` / `class_stage_name`
- 没有 `camp_id` / `camp_name` / `camp_group_name`
- 有 `order_no`、`sku`、`refund_amount`、退款原因、申请人/责任人等审批字段

## 退款审批表补阶段的方法

审批表本身不能直接区分阶段，但可通过订单表和营期维表补：

```sql
SELECT
    r.order_no,
    r.sku,
    r.refund_amount,
    f.flow_no,
    f.collect_order_no,
    f.camp_name,
    d.camp_group_name,
    d.class_stage_name,
    f.new_front_end_name,
    f.pay_time,
    f.refund_time
FROM tock_ods_feishu_refund_approval_detail_all_d r
INNER JOIN dwd_order_flow_df f
    ON r.order_no = f.flow_no
LEFT JOIN dim_camp_df d
    ON f.camp_id = d.camp_id
WHERE r.order_no != ''
```

本次验证：`r.order_no = f.flow_no` 可用；`r.order_no = f.collect_order_no` 在 2026-05 支付订单范围内未命中。以后不要默认把审批 `order_no` 当总订单号。

可按阶段汇总：

```sql
SELECT
    d.class_stage_name,
    count() AS rows,
    countDistinct(r.order_no) AS orders,
    round(sum(r.refund_amount), 2) AS refund_amt
FROM tock_ods_feishu_refund_approval_detail_all_d r
INNER JOIN dwd_order_flow_df f
    ON r.order_no = f.flow_no
LEFT JOIN dim_camp_df d
    ON f.camp_id = d.camp_id
WHERE r.order_no != ''
GROUP BY d.class_stage_name
ORDER BY rows DESC
```

本次全量关联阶段分布示例：
- 销转营期：22,020 单，退费额 24,673,375.55
- 二阶营期：8,029 单，退费额 13,893,187.29
- 三阶营期：3,192 单，退费额 8,130,304.22
- 四阶营期：874 单，退费额 2,749,914.44
- 特殊营期：820 单，退费额 4,213,306.87
- 五阶营期：35 单，退费额 74,432.00

这些数值是当时环境的验证样例，不要作为永久业务结果复用。

## 后端团队/人员订单查找流程

当用户说“某人是后端团队”但系统字段不一定有团队名时，按这个顺序查：

1. 先查字段存在性：`dwd_order_flow_df`、`dim_camp_df`、`dwd_order_handover_df`。
2. 同时搜索：
   - `dwd_order_flow_df.order_emp_name`
   - `dwd_order_flow_df.emp_team_name`
   - `dwd_order_flow_df.emp_group_name`
   - `dwd_order_flow_df.camp_name`
   - `dim_camp_df.camp_name`
   - `dim_camp_df.camp_group_name`
   - `dwd_order_handover_df.class_camp_name`
   - `dwd_order_handover_df.camp_group_name`
3. 如果用户给的是业务侧分类名（如“4月尾单-0203正价-成都罗一豪”），不要假设它等于标准轨次/营期名；需要进一步找分类来源表或映射关系。
4. 要取阶段，优先 `dwd_order_flow_df.camp_id -> dim_camp_df.camp_id -> class_stage_name`。
5. 若是“交接/归属”口径，则走 `dwd_order_handover_df`；若是“订单所属营期”口径，则走 `dwd_order_flow_df` + `dim_camp_df`。

## ClickHouse 21.8 注意事项

- 不要在 `JOIN ON` 中写不等式/范围过滤，例如 `ON f.camp_id=d.camp_id AND f.pay_time >= ...`，会报 `JOIN ON inequalities are not supported`。把时间过滤放入子查询或 `WHERE`。
- 查询里如果 `SELECT formatDateTime(pay_time, ...) AS pay_time`，后续 `WHERE pay_time >= toDateTime(...)` 可能被别名污染，触发 String/DateTime 类型冲突。避免用同名别名，改成 `pay_time_str`。

## 输出建议

给用户结论时区分：
- “没有命中这些文本/字段”
- “可能相关的标准轨次/营期候选”
- “当前按某字段口径是否有订单”
- “审批表自身是否带阶段”与“能否通过 join 补阶段”

不要把没有直接命中业务分类名，误报成“没有相关订单”。