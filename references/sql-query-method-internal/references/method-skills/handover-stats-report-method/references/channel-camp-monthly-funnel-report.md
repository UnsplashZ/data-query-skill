# 封板营期按月/渠道漏斗报表口径

适用场景：用户要按封板营期月份，汇总 leads、加微率、转化率、ROI、D1-D6 到课、D1-D9 逐日转化率与课中转化率，并要求同时输出「月汇总」和「月 x 渠道汇总」。

## 推荐数据源

优先走 ClickHouse，复用已有前端营期/渠道表：

- leads、加微、到课、线索消耗：`tock_applet_user`
- GMV、正价课学员、课中 GMV、D1-D9 GMV：`drh_order FINAL`
- 封板月份：`drh_live_camp_date FINAL.end_time`
- 营期开课日期：`drh_live_camp_date FINAL.class_time`
- 渠道归属：`tock_channel_id_belong`

## 核心口径

- 时间范围用封板日期：`cd.end_time >= start AND cd.end_time < end_exclusive`。
- leads 过滤：`is_repeat_leads = 0 AND is_callback != ''`；若用 `drh_applet_user`，对应为 `is_repeat_leads = 0 AND is_callback != 0`。
- 加微数：`sum(is_friend)`；加微率：`加微数 / leads`。
- 转化率：`正价课学员数 / leads`。
- 正价课学员数沿旧前端报表口径可用：`uniqExact(if(price >= 188000 AND pay_type IN (2,3), user_id, NULL))`。
- ROI：`GMV / 线索消耗`。
- D1-D9：`dateDiff('day', toDate(class_time), toDate(pay_time)) + 1`，按第 N 天 GMV 汇总。
- D1-D9 转化率沿旧 SQL 口径：`DNGMV / 2980 / leads`。
- 课中转化率：`课中GMV / 2980 / leads`；课中 GMV 可沿 `drh_order.in_class = 0` 口径。
- D1-D6 到课数/率：优先直接取 `tock_applet_user.d1_arrive ... d6_arrive`，分母为 leads。

## SKU / 前端限定

用户说「只看声乐 SKU 前端」时，不要生成全 SKU 报表，也不要保留多余明细列。应同时在 leads 侧和订单侧限定声乐：

- leads 侧：`tock_applet_user.sku = '声乐'`
- 订单侧：`drh_order.front_end = 1 AND drh_order.pay_status = 2`，并通过营期业务线限定 `drh_business_line.name = '声乐'`
- 订单侧 join：`drh_order.camp_id = drh_live_camp_date.camp_id`，再用 `drh_live_camp_date.category -> drh_business_line.category` 判断营期 SKU。

如果用户提供了桌面样例文件并要求「月汇总和月x渠道汇总」，输出结构应贴近样例：

1. `月汇总`
2. `月x渠道汇总`

列保持 25 列最终展示口径：

- `封板月`、`渠道`、`leads`、`加微率`、`转化率`、`ROI`
- `D1到课率` ... `D6到课率`
- `D1转化率` ... `D9转化率`
- `课中转化率`、`leads成本`、`GMV`、`课中GMV`

不要在这种场景默认输出 60 列的调试明细（加微数、D1-D6 到课数、D1-D9 GMV、D1-D9 课中 GMV等），除非用户明确要分子/分母明细。

## 渠道归类兼容旧报表

旧 SQL 中常见渠道归类：

```sql
CASE
  WHEN market_belong LIKE '%BD2%' AND teach_help = '图书' THEN 'BD2-图书'
  WHEN market_belong LIKE '%BD2%' AND is_callback = '0元' AND teach_help = '非图书' THEN 'BD2-0元'
  WHEN market_belong LIKE '%BD1%' THEN 'BD1'
  WHEN market_belong = '' OR market_belong IS NULL THEN '未归类'
  ELSE market_belong
END
```

订单侧没有 `is_callback` 字符串时，可用 `drh_channel_emp.is_pay = 0` 辅助识别 `BD2-0元`，但要在最终说明中标明这是兼容旧 SQL 的渠道归类。

## ClickHouse 21.8 注意点

- `FINAL` 后不要直接别名：使用子查询，例如 `(SELECT * FROM drh_order FINAL WHERE _sign > 0) AS o`。
- 外层引用封板日期时，要引用子查询透出的字段，例如 `o.camp_end_time`，不要在外层继续写 `cd.end_time`。
- 避免 `SELECT *` 后再新增同名列，例如订单子查询里 `o.*` 与 `cd.class_time AS class_time` 容易让 `pay_time` / `class_time` 解析异常。订单明细子查询建议显式列出所需字段：`id, user_id, price, pay_time, pay_type, in_class, channel_id, camp_id, front_end, pay_status`。
- SQL 层字段 alias 尽量 ASCII；导出 Excel 时再改中文列名，避免 driver 错误信息编码问题掩盖真实报错。
- 生成 Excel 时，如果当前环境没有 `xlsxwriter`，可用 `openpyxl` 写入并设置格式；这只是导出实现选择，不是业务口径。

## 输出建议

Excel 两个 sheet：

1. `月汇总`
2. `月x渠道汇总`

列保持数值单元格，不要把百分比或金额转成文本。若用户没有提供样例文件，默认可额外输出分子/分母列；若用户要求对齐样例或只要汇总，则优先使用上述 25 列。

## 验证清单

- 确认月份行数覆盖请求范围，例如 2025-11 到 2026-05 应为 7 个月。
- 检查 `drh_live_camp_date` 在日期范围内是否有重复 `camp_id`；如有重复，确认是否会放大订单行。
- 对比 `tock_applet_user` 与 `drh_applet_user` 的 leads 总量，确认过滤口径一致。
- 如果用户指定 SKU，分别验证 leads 侧和订单侧都加了 SKU 过滤。
- 输出后用 `openpyxl.load_workbook(..., read_only=True, data_only=True)` 检查文件存在、sheet 名、行列数。