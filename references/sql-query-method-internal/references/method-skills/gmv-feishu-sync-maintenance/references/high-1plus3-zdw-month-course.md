# 高阶1+3：张大伟月课商品名归类

本参考记录一次可复用的口径调整方式，不保留一次性运行日志。

## 场景

用户要求：同步数据到高阶1+3表的 GMV明细时，把商品名命中以下规则的记录都算到「张大伟月课」：

```sql
main_goods_name RLIKE '35天韵味|35天全能|张大伟28天'
```

## 目标脚本

```text
/Users/zheng/.hermes/python/projects/gmv-daily/vocal_gmv_refund_daily/run_job.py
```

该脚本负责声乐 GMV/退款日报，并写入飞书表格的 GMV sheet：

```text
spreadsheet_token = <REDACTED_FEISHU_SPREADSHEET_TOKEN>
sheet_id = <REDACTED_FEISHU_SHEET_ID>
```

## 推荐实现

定义商品名规则常量：

```python
ZDW_MONTH_COURSE_GOODS_PATTERN = '35天韵味|35天全能|张大伟28天'
```

在 GMV 查询里把声乐分支的 `class_stage_name` 改成：

```sql
CASE
    WHEN a.main_goods_name RLIKE '{ZDW_MONTH_COURSE_GOODS_PATTERN}' THEN '张大伟月课'
    ELSE c.class_stage_name
END AS class_stage_name
```

同时把原阶段过滤：

```sql
c.class_stage_name IN ('二阶营期','三阶营期','四阶营期','五阶营期')
```

改为：

```sql
(
    c.class_stage_name IN ('二阶营期','三阶营期','四阶营期','五阶营期')
    OR a.main_goods_name RLIKE '{ZDW_MONTH_COURSE_GOODS_PATTERN}'
)
```

退款查询也要做同样处理。

## 为什么要同时改 WHERE

如果只改 SELECT CASE，不改 WHERE，那么商品名命中「35天韵味/35天全能/张大伟28天」但营期阶段不在四个白名单阶段内的记录仍会被过滤掉，不会进入「张大伟月课」。

## 验证命令

语法检查：

```bash
python -m py_compile /Users/zheng/.hermes/python/projects/gmv-daily/vocal_gmv_refund_daily/run_job.py
```

正式同步：

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy \
/opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python \
/Users/zheng/.hermes/python/projects/gmv-daily/vocal_gmv_refund_daily/run_job.py
```

读回飞书验证时，可复用该项目 `common.py` 里的 `feishu_token` 和 `sheet_get_values`，读取 `a5qFM6!B1:H7` 检查表头与「张大伟月课」列。
