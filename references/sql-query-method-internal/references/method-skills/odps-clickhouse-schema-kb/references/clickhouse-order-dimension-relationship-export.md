# ClickHouse 订单维度好友关系导出补充

适用场景：用户要求基于订单筛选人群，并回填企微好友、交接服务、学习记录等用户级摘要。

## 核心口径

1. 粒度优先按用户要求确认：如果用户说“从订单维度看”，每行应是一笔订单，不要先按 `union_id` 聚合。
2. “只看前端订单”在 `dwd_order_flow_df` 中使用：
   ```sql
   new_front_end_name = '大前端'
   ```
   同时通常保留：
   ```sql
   pay_status_name = '支付成功'
   AND main_first_level = '课程'
   AND union_id != ''
   ```
3. 首款 `<1000` 且无尾款订单口径：
   ```sql
   pay_type_code = 1
   AND pay_amount < 1000
   AND refund_amount <= 0
   ```
   并且该首款 `flow_no` 不能出现在任何支付成功尾款订单的 `relate_flow_no` 中：
   ```sql
   LEFT JOIN (
     SELECT relate_flow_no
     FROM dwd_order_flow_df
     WHERE pay_status_name = '支付成功'
       AND pay_type_code = 2
       AND relate_flow_no != ''
     GROUP BY relate_flow_no
   ) tail_pay ON first_order.flow_no = tail_pay.relate_flow_no
   WHERE ifNull(tail_pay.relate_flow_no, '') = ''
   ```
   注意：尾款检查不要只在前端订单子集里做，除非用户明确尾款也限定前端；默认应在全订单表中检查关联尾款，避免漏掉跨来源尾款。
4. “购买了哪些商品”应从订单行直接输出，至少包括：
   - `flow_no`, `pay_time`, `pay_type_code`, `pay_type_name`
   - `main_goods_name`, `main_goods_sku`
   - `camp_name`, `camp_sku`
   - `total_original_price`, `pay_amount`, `refund_amount`
   - `order_source_name`, `front_end_name`, `new_front_end_name`

## 正价班判断

不要只用用户级 `max(is_official)` 作为“是否在正价班”。订单维度导出应拆开：

1. 订单是否正价课：
   ```sql
   dwd_order_flow_df.is_official = 1
   ```
2. 是否进入正价班/服务班：优先使用 `tock_handover_plus` 的交接/服务字段，例如：
   - `service_camp_name`
   - `service_camp_stage`
   - `service_camp_sku`
   - `service_emp_name`
   - `service_emp_group_name`
   - `service_is_friend`

建议输出多个字段，而不是一个黑箱字段：
- `订单是否正价课`
- `是否在正价班_综合判断`
- `正价班判断依据`
- `是否在正价班_交接判断`
- `是否在正价班_微信辅助`
- `交接表是否有服务班`
- `交接表是否二阶及以上`
- `是否当前企微好友`

交接表是主判断；微信好友关系只能作为服务/承接辅助证据，不应单独等同于正价班。

## 推荐处理形态

1. 先从 `dwd_order_flow_df` 拉目标订单行。
2. 收集目标订单的 `union_id`。
3. 按 `union_id` 分批查询并回填用户级摘要：
   - `tock_ast_process_data`：近 30 天学习、首次开课。
   - `tock_handover_plus`：服务班、服务阶段、学管。
   - `tock_emp_external_user`：好友关系数、当前好友数、企微主体/归属/员工样例。
   - `tock_qw_message_res`：当前好友近 30 天互动、投诉关键词摘要。
   - `drh_live_user FINAL`：昵称、手机号。
4. 高意向订单筛选可在订单基础上叠加用户级条件：未退款、无投诉关键词，且近 30 天学习或当前好友互动。

## 验证清单

- Excel 可读取，sheet 行列数符合预期。
- 首款无尾款组：`countIf(tail_pay.relate_flow_no != '') = 0`。
- 首款无尾款组：`sum(refund_amount) = 0`。
- 前端订单：目标订单均为 `new_front_end_name = '大前端'`。
- 正价班字段：同时检查订单 `is_official` 和交接字段覆盖情况，不要只汇报综合字段。
