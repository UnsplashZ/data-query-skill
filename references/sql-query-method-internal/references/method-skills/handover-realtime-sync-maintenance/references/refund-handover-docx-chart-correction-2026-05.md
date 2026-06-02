# Refund-handover Feishu Docx chart correction (2026-05)

## Context

A Feishu Docx report, `<REDACTED_FEISHU_URL>`, analyzed whether handover efficiency optimization reduced refund rate.

The user corrected that the first chart/report rebuild used 选期率 / 加微率 values that differed sharply from the daily push.

## Root cause

The first rebuild used an ad hoc ClickHouse query over:

- `dwd_order_flow_df`
- `dwd_order_handover_df`
- `tock_ast_process_data`

It defined:

- `selected_flag = h.flow_no != '' AND (ast_emp_name != '' OR class_camp_id > 0 OR class_camp_name != '')`
- `wechat_flag = h.flow_no != '' AND ast_friend_time > 1970-01-02`
- denominator = non-refund orders

This produced low values, e.g. 声乐:

- 3月选期率 `61.41%`
- 4月选期率 `52.22%`
- 3月当前加微率 `55.82%`
- 4月当前加微率 `48.61%`

These values were not aligned with the daily handover push.

## Correct口径

Use the daily handover sync pipeline:

- SQL: `~/.hermes/sql/projects/handover-realtime-sync/交接数据-实时.sql`
- Python: `~/.hermes/python/projects/handover-realtime-sync/run_sync.py`
- handover source: `drh_handover_plus`
- wechat source: `drh_emp_external_user`
- selected: final `选期状态 = '已选期'`
- wechat: final `加微状态 = '已加微'`

For the 声乐 report scope:

- `商品SKU = 声乐`
- `营期SKU = 声乐`
- `商品原价 >= 1880`
- `营期阶段 = 销转营期`
- payment dates `2026-03-01` through `2026-04-30` for the correction check

Originally verified current-status values were:

| month | orders | refund_cnt | selected_all | wechat_all | select_rate_all | wechat_rate_all | select_rate_non_ref | wechat_rate_non_ref |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-03 | 2365 | 144 | 2193 | 2057 | 92.73% | 86.98% | 95.05% | 90.90% |
| 2026-04 | 1140 | 30 | 1113 | 1085 | 97.63% | 95.18% | 98.83% | 96.85% |

The user then corrected the cohort-comparison method: for reports, do not use current final status for all historical months. Use a fixed observation cutoff per pay month: `pay_month_end + 7 days`, inclusive.

Final report values after applying this cutoff and including both 声乐 scopes:

| scope | month | orders | refund_rate | select_rate | wechat_rate | selected_wechat_rate |
|---|---:|---:|---:|---:|---:|---:|
| 全部订单 | 2026-03 | 3041 | 3.29% | 75.96% | 62.94% | 82.47% |
| 全部订单 | 2026-04 | 1478 | 2.90% | 77.81% | 74.56% | 95.74% |
| 课程全款尾款1880+ | 2026-03 | 2365 | 3.12% | 87.40% | 72.98% | 83.26% |
| 课程全款尾款1880+ | 2026-04 | 1140 | 2.44% | 97.81% | 95.18% | 97.22% |

## Reusable one-off extraction pattern

```python
import importlib.util, sys
from pathlib import Path
import pandas as pd

project = Path('/Users/zheng/.hermes/python/projects/handover-realtime-sync')
spec = importlib.util.spec_from_file_location('run_sync', project / 'run_sync.py')
rs = importlib.util.module_from_spec(spec)
sys.modules['run_sync'] = rs
spec.loader.exec_module(rs)

cfg = rs.load_yaml(project / 'config.yaml')
sql_template = Path(cfg['sql_file']).read_text(encoding='utf-8')
rs.SKU_QUERY_RULES = [
    {'name': 'voice_only', 'goods_skus': ['声乐'], 'camp_skus': ['声乐'], 'min_price': 1880},
]
raw = rs.query_target_raw_df(
    sql_template,
    start_date='2026-03-01',
    end_date='2026-04-30',
    stage=cfg['stage'],
    base_goods_price=int(cfg['goods_price']),
)
detail, helper = rs.build_detail(raw, pd.Timestamp('2026-05-07'))
helper['pay_month'] = pd.to_datetime(helper['支付日期']).dt.strftime('%Y-%m')
```

## Feishu Docx image replacement verification

After regenerating images:

1. Upload image media with `parent_type='docx_image'` and `parent_node=<image_block_id>`.
2. Patch each image block with `replace_image: {'token': file_token}`.
3. Re-read `/open-apis/docx/v1/documents/:document_id/raw_content`.
4. Assert stale low values are absent, especially `61.41%`, `52.22%`, `55.82%`, `48.61%`.
5. Report the generated workbook path and image paths.

Correction output from the session:

- Workbook: `/Users/zheng/.hermes/output/query_results/refund-handover-effect/声乐交接常用指标验证_修正版_20260507_121111.xlsx`
- Images:
  - `/Users/zheng/.hermes/output/query_results/refund-handover-effect/doc_images_corrected/00_corrected_hero.png`
  - `/Users/zheng/.hermes/output/query_results/refund-handover-effect/doc_images_corrected/01_corrected_big_market.png`
  - `/Users/zheng/.hermes/output/query_results/refund-handover-effect/doc_images_corrected/02_corrected_vocal_metrics.png`
  - `/Users/zheng/.hermes/output/query_results/refund-handover-effect/doc_images_corrected/03_corrected_dim_check.png`
