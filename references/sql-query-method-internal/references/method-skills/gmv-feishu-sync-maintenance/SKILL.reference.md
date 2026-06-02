---
name: gmv-feishu-sync-maintenance
description: Maintain the user's GMV/退款 Feishu sync jobs, including high阶1+3 GMV明细口径、ODPS SQL分类规则、飞书写入与读回验证。
version: 1.0.0
---

# GMV / 退款飞书同步维护

适用场景：
- 用户要求调整飞书 GMV / 退款日报、月度更新、GMV明细或高阶1+3表的统计口径。
- 需要修改 Hermes 管理的 ODPS 查询脚本，并立即同步到飞书。
- 需要判断某个商品名、商品SKU、营期阶段或 cci3_name 应归入哪个展示分类。

## 关键路径

当前已知高阶1+3 GMV明细相关脚本：
- `/Users/zheng/.hermes/python/projects/gmv-daily/vocal_gmv_refund_daily/run_job.py`

相关 cron：
- 名称：`声乐GMV和退费日报`
- 典型命令：`/opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python /Users/zheng/.hermes/python/projects/gmv-daily/vocal_gmv_refund_daily/run_job.py`

当前已知飞书目标：
- spreadsheet_token: `<REDACTED_FEISHU_SPREADSHEET_TOKEN>`
- GMV sheet_id: `a5qFM6`
- 用户侧链接使用 `opensplendid.feishu.cn` 域名。

## 修改流程

1. 先定位 cron 和脚本：
   - `cronjob(action='list')` 查看当前任务名称、启停状态、命令路径。
   - 如需完整 prompt，读取 `~/.hermes/cron/jobs.json`。
   - 优先修改 Hermes 自有脚本目录，不要改原始业务项目。

2. 阅读目标脚本当前 SQL 和写入范围：
   - 确认 ODPS 表名、日期窗口、展示分类、飞书 range。
   - 区分 GMV 查询和退款查询；分类口径通常两边都要一致，否则净GMV会错位。

3. 分类规则建议写成常量：
   - 例如 `ZDW_MONTH_COURSE_GOODS_PATTERN = '35天韵味|35天全能|张大伟28天'`
   - SQL 中用 `CASE WHEN a.main_goods_name RLIKE '<pattern>' THEN '张大伟月课' ELSE ... END AS class_stage_name`。

4. 如果原 SQL 有 `class_stage_name IN (...)` 过滤，新增分类规则时要同步放宽过滤：
   - 保留原阶段过滤；
   - 额外允许命中新商品名规则的记录进入结果；
   - 否则 CASE 写了也可能在 WHERE 阶段被过滤掉。

5. 执行并验证：
   - 语法检查：`python -m py_compile <script>`。
   - 运行正式同步命令，观察 ODPS 查询行数、分类汇总、飞书写入结果。
   - 用飞书 API 读回写入范围，例如 `B1:H7`，确认表头和值已更新。

## 当前业务口径

### 高阶1+3 GMV明细：张大伟月课归类

在高阶1+3表的 GMV明细中：

```sql
main_goods_name RLIKE '35天韵味|35天全能|张大伟28天'
```

命中的记录归入：

```text
张大伟月课
```

维护要点：
- GMV订单查询和退款查询都要使用同一归类规则。
- 该规则是对 `cci3_name = '声乐'` 分支的补充；原有 `cci3_name = '声乐-月课'` 直接归入「张大伟月课」的分支保留。
- 如果记录原本不属于 `二阶营期/三阶营期/四阶营期/五阶营期`，但命中该商品名规则，也应进入「张大伟月课」。

参见：`references/high-1plus3-zdw-month-course.md`

## 验证标准

每次调整后至少确认：
- Python 语法检查通过。
- ODPS 查询成功，不只检查脚本启动。
- 飞书写入成功。
- 飞书读回目标 range，确认数据已变化或符合预期。
- 明确说明是否已经真实写入飞书；如果只改代码没运行，要说“没同步”。

## 常见坑

- 只改 GMV 查询、不改退款查询，会导致净GMV分类不一致。
- 只改 SELECT CASE、不改 WHERE 过滤，命中新分类但阶段不在白名单的记录仍会被过滤掉。
- `cronjob(action='list')` 里的 `last_status: ok/error` 不等价于业务结果；需要看脚本输出或飞书读回。
- 不要把一次性运行结果写入 skill；skill 只保留可复用口径、路径和验证方法。