# 历史首款订单 / 休学冻课 Feishu 四表工作流（2026-05-08）

## 适用场景

用户要重建或维护飞书表：

`<REDACTED_FEISHU_URL>`

四个用户可读 sheet：

- `首款订单汇总`
- `首款订单明细`
- `冻课汇总`
- `冻课明细`

脚本：

- `/Users/zheng/.hermes/python/projects/first-payment-only/refresh_feishu_with_class_attendance.py`

本地备份输出：

- `/Users/zheng/.hermes/output/query_results/20260508_历史首款_冻课学员_补上课情况.xlsx`

## 首款订单口径

基础订单池来自 `dwd_order_flow_df`：

- `pay_status_name = '支付成功'`
- `pay_type_code = 1`
- `pay_type_name = '首款'`
- `main_first_level = '课程'`
- 反关联尾款：尾款行 `pay_type_code = 2`, `pay_type_name = '尾款'`, `relate_flow_no != ''`；首款 `flow_no` 不在尾款 `relate_flow_no` 中
- 历史范围用 `pay_time < toDateTime('2026-05-09 00:00:00')`

最新校验结果（2026-05-08 刷新后）：

- 首款订单：`137,041`
- 有上课记录订单：`26,899`
- 上课订单率：`0.1962843237`
- 有学习行为订单：`26,340`
- 学习行为订单率：`0.1922052524`

## 首款订单上课情况

用户补充口径：首款订单需要看是否有上课情况。

表：`tock_ast_process_data`

字段验证：

- `camp_id`：上课营期 ID
- `union_id`：用户 union_id
- `class_time`：上课时间
- `study_time` / `zb_study_time` / `submit_cnt` / `e_time_cnt` / `message_cnt`：学习行为辅助字段

匹配规则：

- `dwd_order_flow_df.union_id = tock_ast_process_data.union_id`
- `dwd_order_flow_df.camp_id = tock_ast_process_data.camp_id`
- 只统计 `class_time > '1970-01-02'`
- 只统计 `class_time >= pay_time`
- 历史输出中限制 `class_time < toDateTime('2026-05-09 00:00:00')`

用户最终确认：汇总和用户可读指标只保留“学习行为”相关指标，不展示 `有上课订单数` / `有上课学员数` / `上课订单率`。明细中也不要展示 `是否有上课记录` / `上课记录数`。

保留字段：

- `是否有学习行为`：`active_class_record_cnt > 0`
- `学习行为记录数`
- `首次上课时间`
- `最近上课时间`
- `学习时长`
- `直播学习时长`

学习行为定义：

```sql
study_time > 0 OR zb_study_time > 0 OR submit_cnt > 0 OR e_time_cnt > 0 OR message_cnt > 0
```

## 当前休学冻课合并口径

用户明确纠正：`休学冻课` 是一个合并概念，用户侧不要拆成休学 / 冻课，也不要拆关键词命中 / 其他规则命中。汇总里只看总计。

2026-05-08 追加修正：用户提供了新的休学/未分配学员 SQL，后续以该 SQL 为基础，而不是旧的 `hp_class_camp_name`/`class_camp_group_name` 空值判定口径。后续又纠正了两个关键限制：

- 休学不能用 `OR d.order_no != ''` / `OR d.order_no IS NOT NULL`，否则会把所有有有效交接班级的正常订单错误归进休学；应改为 `multiMatchAny(service_camp_name, ['冻课','休学','延期']) OR d.stop_study_status = 1`。
- 最终休学/未分配统计和 `冻课明细` 都必须限制为课程支付成功订单：匹配 `dwd_order_flow_df.main_first_level='课程' AND pay_status_name='支付成功'`，即 `matched_paid_course_order=1`。

当前收窄口径（2026-05-08 最后确认）：休学来自 `tock_handover_plus` 中命中 `冻课/休学/延期`，或 `drh_handover_plus FINAL WHERE _sign>0` 中 `stop_study_status=1`；不要要求 `t.service_camp_name != ''`，因为服务营期为空但 `stop_study_status=1` 的订单也应进入休学。未分配只来自 `tock_handover_plus` 中 `service_camp_name='' AND service_emp_name=''`，并且必须排除已经进入 `stop_study_flag` 的订单；不要再 UNION `tock_order.order_no NOT IN (SELECT order_no FROM tock_handover_plus)` 这段补充来源，因为会把“只是没进交接表/表关联缺失”的正常订单误算进未分配。`冻课明细` 只展示 `flag='休学' AND matched_paid_course_order=1`，`flag='未分配' AND matched_paid_course_order=1` 只进入 `冻课汇总` 的单独统计。

当前口径已改为：

1. 主来源使用 `tock_handover_plus t`
2. 连接 `drh_handover_plus` 只为补 `stop_study_status` 等字段
3. `drh_handover_plus` 必须先在子查询中做 `FINAL WHERE _sign > 0`，再参与 join
4. 不再使用 `dev_stop_stu_record.stop_flag = 1` 作为补充来源
5. 不再用 `drh_handover_plus.stop_flag` 或 `drh_handover_plus.class_camp_name` 作为主判定条件

正确 SQL 结构：

```sql
WITH
drh_valid AS (
    SELECT
        order_no,
        anyIf(union_id, union_id != '') AS union_id,
        max(stop_study_status) AS stop_study_status,
        anyIf(stop_hand_emp, stop_hand_emp != '') AS stop_hand_emp,
        anyIf(class_camp_name, class_camp_name != '') AS class_camp_name
    FROM (
        SELECT *
        FROM drh_handover_plus FINAL
        WHERE _sign > 0
    )
    WHERE order_no != ''
    GROUP BY order_no
),
hp AS (
    SELECT
        t.order_no AS flow_no,
        anyIf(d.union_id, d.union_id != '') AS union_id_hp,
        max(if(
            d.stop_study_status = 1
            OR t.service_camp_name LIKE '%休学%'
            OR t.service_camp_name LIKE '%冻课%'
            OR t.service_camp_name LIKE '%延期%',
            1,
            0
        )) AS stop_freeze_flag_hp,
        minIf(
            t.stop_study_time,
            d.stop_study_status = 1
            AND t.stop_study_time > toDateTime('1970-01-02 00:00:00')
        ) AS first_rest_time,
        maxIf(
            t.stop_study_time,
            d.stop_study_status = 1
            AND t.stop_study_time > toDateTime('1970-01-02 00:00:00')
        ) AS latest_rest_time,
        anyIf(d.stop_hand_emp, d.stop_study_status = 1 AND d.stop_hand_emp != '') AS rest_operator,
        anyIf(
            coalesce(nullIf(t.service_camp_name, ''), d.class_camp_name),
            coalesce(nullIf(t.service_camp_name, ''), d.class_camp_name) != ''
        ) AS hp_class_camp_name,
        anyIf(
            t.service_camp_name,
            t.service_camp_name LIKE '%休学%'
            OR t.service_camp_name LIKE '%冻课%'
            OR t.service_camp_name LIKE '%延期%'
        ) AS keyword_class_camp_name
    FROM tock_handover_plus t
    LEFT JOIN drh_valid d
        ON t.order_no = d.order_no
    WHERE t.order_no != ''
      AND (
          d.stop_study_status = 1
          OR t.service_camp_name LIKE '%休学%'
          OR t.service_camp_name LIKE '%冻课%'
          OR t.service_camp_name LIKE '%延期%'
      )
    GROUP BY t.order_no
)
```

最新校验结果：

- 冻课明细：`11,929` 条
- `dev_stop_stu_record.stop_flag = 1` 曾经作为补充来源时独有补充 `1,438` 条；用户已明确要求去掉这部分补充

## 休学冻课补字段

Join / 补字段：

- 休学/未分配记录按 `flow_no + flag` 聚合成一行；旧的一单一行断言不再适用，校验应使用 `len(rest) == rest[['flow_no','flag']].drop_duplicates().shape[0]`
- 再 LEFT JOIN `dwd_order_flow_df.flow_no` 补支付金额、退款、SKU、前后端等；最终汇总和明细只统计能匹配到课程支付成功订单的记录（`matched_paid_course_order=1`），否则会出现记录数包含非课程/非支付成功但金额为 0 的混合口径
- 明细补字段：
  - `成交人`：优先 `dwd_order_flow_df.order_emp_name`，兜底 `tock_order.emp_name`
  - `交接学管`：`dwd_order_handover_df.ast_emp_name`
  - `手机号`：`tock_applet_user.phone`，按最终 `union_id` 匹配；建议在 `applet_user` CTE 中用 `argMaxIf(phone, create_time, phone != '') AS phone`，避免取到空手机号
  - `课包价格`：优先 `dwd_order_flow_df.total_original_price`，兜底 `tock_order.goods_price`
  - `成交营期阶段`：优先 `dwd_order_handover_df.class_stage_name`，兜底 `tock_order.class_stage`
- `交接班级轨次` 来自 `dwd_order_handover_df.camp_group_name`，按 `flow_no` 左连补字段
- 2026-05-08 最后确认的未分配收窄口径不再使用 `tock_order order_no NOT IN (SELECT order_no FROM tock_handover_plus)` 补充来源；该分支曾导致未分配过大。若未来临时恢复这段分支，不能随意改写为 LEFT JOIN；本环境验证二者结果不同（原始 NOT IN 未分配约 33.6 万，LEFT JOIN 变成 0），且必须加 `pay_type IN ('全款','尾款') AND first_level='课程'`。
- 未分配池必须排除已经进入休学池的订单：`service_camp_name='' AND service_emp_name='' AND order_no NOT IN (SELECT flow_no FROM stop_study_flag)`。同时休学池不要加 `t.service_camp_name != ''`，否则会漏掉服务营期为空但 `drh.stop_study_status=1` 的休学订单。
- Excel/Feishu 写入前清洗控制字符（如 `\b赵继红`），否则 openpyxl 会报 `IllegalCharacterError`
- 这版明细规模可能远超飞书单表 500 万单元格限制；如果 `冻课明细` 行数×列数超过限制，不要强写单 sheet。优先：本地 Excel 全量 + 飞书只写汇总，或按年份/SKU 拆分明细 sheet
- 飞书表格的单元格上限按 **整张 sheet 当前网格** 计算，不只按本次写入区域计算；旧明细 sheet 若保留十几万历史行，即使新数据只有几万行，也可能在追加列时触发 `cells excess:5000000`。处理顺序：先查 `grid_properties.row_count/column_count`，必要时删除多余列/行；如果历史网格过大且无法安全缩小，重建目标 sheet 后写入并读回校验。

## 汇总 sheet 展示要求

用户后续手工调整过汇总 sheet 格式；刷新时要尽量按当前板块结构写内容，不要恢复成长表拼接。

### 首款订单汇总

保留板块：

1. 核心规模
2. 按年趋势
3. SKU Top20
4. 前后端分布
5. 金额分桶

不要展示单独的 `按上课情况` 板块；核心规模中只保留学习行为相关总指标，不保留 `有上课订单数` / `有上课学员数` / `上课订单率`。明细同样不展示 `是否有上课记录` / `上课记录数`。

### 冻课汇总

保留板块：

1. 核心规模
2. SKU Top20
3. 前后端分布
4. 金额分桶

不要展示：

- `休学订单数` / `冻课订单数` 拆分
- `仅休学` / `仅冻课` / `休学+冻课`
- `关键词命中` / `状态字段命中`
- `其中关键词命中订单数`
- `匹配课程支付订单数`
- `课程支付订单匹配率`

### 金额分桶排序

金额分桶必须按金额正序，不要按金额或订单数倒序。当前用户确认的分桶是：

1. `1-99`
2. `100-199`
3. `200-500`
4. `501-1000`
5. `1001-2980`
6. `2980+`
7. `其他`

### 数值格式

用户明确纠正：数字都用数值格式，不要写成文本。

- 金额写元级数值，例如 `71404981.66`，不要写 `7140.5 万`
- 比率写数值小数，例如 `0.0730029142`，不要写 `7.30%`
- 飞书端可用格式显示百分比，但写入值本身必须是数值

## Feishu 写入注意

目标表底层 token：`JsJssm2cNhbXWWtmXracroh8neg`

已验证 sheet ids：

- `首款订单汇总`: `8d244a`
- `首款订单明细`: `35dI3e`
- `冻课汇总`: `35dI3f`
- `冻课明细`: `35dI3g`

写入顺序：

1. 重新拉 ClickHouse 数据并构造四个表
2. 汇总 sheet 清空有限区域，例如前 `220` 行、`30` 列，保留用户手工调整过的 sheet 级格式
3. 明细 sheet 直接覆盖目标区域
4. 每个 sheet 写入后读取 `A1:B3` 验证；若刚写完读返回 `90235 data not ready,retry later`，等待后重试，不代表写入失败

关键坑：

- `dimension_range` 一次追加十几万行会报 `90204 invalid parameter: Dimension.Length`；按 5000 行分批追加
- 不要在大明细表写入前清空整张表，容易触发 SSL EOF 或巨量请求；直接覆盖目标区域即可
- Feishu Open Platform 能解析 Wiki 节点不等于有写权限；无权限时会返回 `403 / 91403 Forbidden`
