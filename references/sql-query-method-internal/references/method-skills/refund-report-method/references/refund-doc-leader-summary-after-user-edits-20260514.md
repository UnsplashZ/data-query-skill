# Refund Docx leader summary after user edits — 2026-05-14

## Trigger
The user asked for a short Feishu-message summary of a modified Feishu Docx refund report. I initially wrote from prior report memory instead of reading the modified document; the user corrected this.

## Durable lesson
For report-summary tasks, especially Feishu Docx reports the user says they edited, the current document is the source of truth. Do not summarize from prior session memory or earlier generated drafts.

## Workflow
1. Read the current Feishu document before summarizing.
   - If `feishu_doc_read` is available, use it.
   - If it fails because the session is not in Feishu comment context, use authenticated local Chrome/headless DOM or another readback path.
2. Extract the report body from the DOM/text and ignore sidebar/document-library noise.
3. Write a short business-facing Feishu message, not a full report.
4. For 3月/4月, M0/M1, or cohort refund-rate statements, include the GMV denominator next to refund amount and refund rate.
5. Keep causal boundaries cautious: distinguish single-channel attribution,交接变化,流量质量,预期管理, and支付后承接 as evidence-supported hypotheses unless causal fields prove otherwise.

## Example from the corrected document
Source facts read from the modified doc:
- 3月支付 cohort: GMV 725.15万, M0退费额 23.00万, M0退费率 3.17%, historical weighted benchmark 1.04%.
- 4月 M0: GMV 353.19万, M0退费额 9.19万, M0退费率 2.60%, down 0.57pp from March but still above benchmark.
- Current evidence does not support attributing the issue to a single channel or handover change.
- 3月 M1 continued to release in April: 退费额 14.57万, rate 2.01% against March GMV.
- 4月 D14内退费占比 78.72%, about 60%未选期; treat as correlation/uncertain causality unless initiator/failure-reason fields are available.

## Good message shape
> 声乐前端 3月出现明显 M0 高退费：3月支付月 GMV 725.15万，M0退费 23.00万，退费率 3.17%，显著高于历史基准 1.04%。4月已有缓和，但仍未恢复到历史区间：4月 GMV 353.19万，M0退费 9.19万，退费率 2.60%。  
> 从结构看，当前不支持简单归因为单一渠道或交接变化，3月当月退费主要来自健康/家庭、长尾未填、时间冲突等原因，且 BD1、BD2-图书、直播自然流等来源退费率均偏高。3月订单在4月仍继续释放 M1 退费，说明风险不是单点支付问题，而是成交质量、预期管理和支付后承接链路共同影响。  
> 建议后续重点复盘 3月高退费来源的流量质量与支付后交接动作，并持续观察 4月新成交 cohort 的 M0退费率、D14内退费占比和未选期退费情况。
