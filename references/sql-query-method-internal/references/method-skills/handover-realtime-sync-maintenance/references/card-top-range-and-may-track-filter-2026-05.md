# 2026-05 卡片顶部指标时间范围与 5 月后端轨次规则

## 背景

用户要求调整交接经营看板飞书卡片：

1. 顶部指标时间范围先改为 `营期开课日期 >= 2026-05-01`，后因开课率大面积为 0 改回 `>= 2026-03-30`。
2. 后端轨次切换到 5 月。
3. 书法后端轨次展示 `105期及以后`，即使轨次名没有显式 `202605` / `2026-05` / `05xx`。
4. 刷新分页卡片缓存，但不要重复发送飞书卡片。

## 关键文件

- `/Users/zheng/.hermes/scripts/handover_team_report_card.py`
- `/Users/zheng/.hermes/scripts/handover_daily_card.py`
- 缓存：`/Users/zheng/.hermes/cache/handover_daily_card_page_cache.json`

## 当前稳定规则

### 顶部指标范围

当前应保持：

```python
CAMP_START_DATE = date(2026, 3, 30)
CAMP_RANGE_LABEL = f"营期开课日期≥{CAMP_START_DATE.isoformat()}"
```

卡片图片和互动卡片文案都应显示 `CAMP_RANGE_LABEL`。

### 后端轨次月份

后端轨次默认月份切到 5 月：

```python
DEFAULT_TRACK_MONTH_FILTER = "202605"
```

并且卡片服务应固定使用 `DEFAULT_TRACK_MONTH_FILTER`，不要继续沿用飞书筛选单元格 `p7dKLB!D1` 里的旧月份，否则缓存可能仍显示 `202604`。

推荐 `read_track_filter()` 行为：

```python
def read_track_filter(s, token: str) -> tuple[str, str]:
    row = (h.read_values(s, token, "p7dKLB!B1:D1") or [[]])[0]
    price_type = str(cell(row, 0, "全部") or "全部").strip()
    if not price_type:
        price_type = "全部"
    month = DEFAULT_TRACK_MONTH_FILTER
    return price_type, month
```

### 书法 5 月轨次兜底

书法 5 月轨次名可能没有显式月份，例如：

- `【院长班】书法提升训练营-105期`
- `【院长班】书法进阶训练营-106期`
- `【院长班】书法训练营-107期`

因此在 `sku == '书法'` 且 `month_key == '202605'` 时，额外纳入 `105期及以后`。`104期` 不应纳入。

## 开课率为 0 的 pitfall

当顶部指标范围改成 `营期开课日期 >= 2026-05-01` 时，开课率会大面积为 0，不是因为没有 `已开课人数`，而是因为顶部开课率按 `开课节点 = 开课封板` 的成熟营期计算。

当前开课封板阈值：

- 声乐 / 钢琴 / 书法：`营期封板日期 + 21天`
- 口琴：`营期封板日期 + 15天`
- 朗诵：`营期封板日期 + 30天`

在 2026-05-28 附近，5 月营期中只有口琴 `2026-05-04` 进入 `开课封板`；声乐、钢琴、书法、朗诵 5 月营期仍多为 `未封板`。所以如果业务要看成熟开课率，`>=2026-03-30` 更合适；如果业务要看 5 月当前已开课率，应明确改公式为与加微/选期相同的 `当前节点 = 加微封板` 分母，而不是沿用 `开课节点 = 开课封板`。

## 验证命令

```bash
/opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python -m py_compile \
  /Users/zheng/.hermes/scripts/handover_team_report_card.py \
  /Users/zheng/.hermes/scripts/handover_daily_card.py
```

本地断言建议检查：

- `CAMP_START_DATE.isoformat() == '2026-03-30'`
- `DEFAULT_TRACK_MONTH_FILTER == '202605'`
- 书法 `105期` / `106期` 对 `202605` 返回 True
- 书法 `104期` 对 `202605` 返回 False
- 非书法仍按正常月份匹配逻辑判断

## 安全刷新缓存

用户要求刷新缓存但不发送新卡片时，使用：

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy \
  PYTHONPATH=/Users/zheng/.hermes/scripts \
  /opt/homebrew/Caskroom/miniforge/base/envs/hermes-sql/bin/python \
  /Users/zheng/.hermes/scripts/handover_daily_card.py --update-cache-only
```

成功后验证缓存：

- `created_at_iso` 更新
- `data_updated_at` 反映最新实时同步文件 mtime
- 5 个 `sku_image_keys` 都存在
- 各 SKU 的 `debug.total_metrics_source.start_date_min` 为 `2026-03-30`
- 各 SKU 的 `debug.track_source.applied_month_filter` 为 `202605`
- 书法 `track_count` 应能看到 105/106/107 期相关轨次

## 注意

- `--update-cache-only` 会上传新的 SKU 图片并刷新分页缓存，但不会发送新卡片。
- 旧卡片按钮点击会读取新的缓存，因此这不是完全无副作用操作；汇报时要明确说明。