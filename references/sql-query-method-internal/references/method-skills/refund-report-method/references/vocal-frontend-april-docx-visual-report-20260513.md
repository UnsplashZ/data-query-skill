# 声乐前端4月退费分析图文报告经验（2026-05-13）

适用场景：用户要求把声乐/前端/交接项目退费分析从 Sheet 或 Excel 改成可阅读的 Feishu Docx 图文报告。

## 用户纠正

多 tab 表格型报告即使数据完整，也可能“完全看不了”。当用户要求正式分析报告时，应优先交付图文业务报告，而不是让读者自己在表格里找结论。

## 推荐 Docx 结构

1. 标题 + 核心结论
2. 顶部 KPI 卡片图：4月同月退费率、已入群/入班退费率、无交接记录退费率
3. 分析口径：短 bullet，写明 `cci3_name='声乐'`、前端、课程、全款/尾款、支付成功
4. 大盘趋势：月度 M0 退费率，标出前6月加权基准
5. Cohort 滞后解释：M0/M1/M2 堆叠或矩阵，说明 4月不能直接承载全部因果归因
6. 交接影响：已入群/入班 vs 无交接记录，强调同状态内部退费率
7. 退款原因：原因归类金额与贡献
8. 结构风险：价格带、投手等高退费额/高退费率组合
9. 建议动作：继续追 4月 cohort M1/M2；把无交接记录作为风险池；单独看已承接组服务衔接类原因
10. 数据与限制：观察性分析，不强因果

## 报告语言

- 不写“4月交接优化直接导致整体退费率下降”。
- 推荐表达：“交接动作对已承接客户有效，但整体效果被未承接风险池和历史 cohort 滞后退费稀释”。
- 分清：4月支付 cohort 的 M0 退费、4月发生退费来自哪些支付月、2/3月历史 cohort 在4月释放。
- 如果 4月 M0 低于 3月但高于半年基准，要同时写两个事实，不只说下降。

## Feishu Docx 实施要点

- 先解析 Wiki token 得到 `obj_token` 和 `obj_type=docx`。
- 覆盖已有 Docx 前保存 `raw_content` 到本地备份。
- 删除 root children 后追加 block；Docx `children` 单次最多 50 个，超过要分批追加。
- 图片 block 流程：创建 `block_type=27` placeholder → `drive/v1/medias/upload_all`，`parent_type=docx_image`，`parent_node=<image_block_id>` → PATCH block `{ "replace_image": { "token": file_token } }`。
- 验证至少包含：raw_content 预览、block_count、image_count、image_token_count。

## 本次验证到的稳定形态

- 文档类型：Wiki-backed Docx，`get_node` 返回 `obj_type='docx'`，`obj_token` 可直接作为 document_id。
- 图文报告可用 4 张 PNG：KPI 总览、月度退费率+cohort、交接状态+原因、结构风险。
- Feishu `POST /docx/v1/documents/{doc_id}/blocks/{doc_id}/children` 单次 children 超过 50 会报 `99992402 field validation failed: the max len is 50`；按 45 个一批写入稳定。
