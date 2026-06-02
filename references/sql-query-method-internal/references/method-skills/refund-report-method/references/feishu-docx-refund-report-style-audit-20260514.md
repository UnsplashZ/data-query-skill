# Feishu Docx refund report style audit pattern (2026-05-14)

Use when a refund/handover Feishu Docx report already has correct numbers but the user asks to professionalize language.

## Workflow
1. Read back the current document `raw_content` through Feishu Docx API before editing and save a local audit copy.
2. Identify style issues separately from metric logic:
   - conversational phrasing
   - over-strong causal statements
   - mixed terminology (`退款` vs `退费`, unclear GMV denominator labels)
   - internal-discussion wording in section titles or recommendations
3. Patch the report-generation source rather than hand-editing the current document if the report may be regenerated.
4. Publish through the existing backup-before-overwrite script.
5. Read back `raw_content` again and verify:
   - required headings exist
   - forbidden phrases are absent
   - image blocks still have tokens
   - source link is still present

## Preferred heading style
- `声乐前端3月/4月退费结构与交接状态分析`
- `核心判断`
- `大盘表现：4月M0退费率较3月回落，但仍高于历史基准`
- `3月M0原因增量：主要来自客观约束与长尾原因`
- `3月M0原始退费说明中的风险信号`
- `渠道维度：BD1-KOL风险突出，但并非单一来源`
- `3月M1：3月支付订单的次月退费释放`
- `4月M0问题定位`
- `交接状态的解释边界`
- `问题定位、原因判断与处理建议`

## Forbidden / replace-with patterns
- `猫腻` -> `主要增量不集中在支付错误类问题`
- `确实异常` -> `显著高于历史区间，属于需要重点复盘的渠道`
- `不是...造成` -> `现有数据不支持将其主要归因于...`
- `单一渠道事故` -> `不宜归因为单一渠道`
- `全局风险抬升` / `系统性风险` -> `多渠道同步抬升，提示阶段性共性风险`
- `不等于4月新增支付问题` -> `口径上不应并入4月新增支付订单的M0问题`
- `看是否有` -> `核查...是否存在...并评估其影响`
- `追D4-D15订单...` -> `建立D4-D15订单跟踪清单，逐单核查...`

## Verification snippet
```python
forbidden = ['猫腻','确实异常','仍不低','不能只追','只盯','一起看','看是否有','售后原因前置','单一渠道事故','全局风险抬升','系统性风险','原始退款说明','退款原因']
required = ['核心判断','3月M0原因增量','交接状态的解释边界','问题定位、原因判断与处理建议']
print({'forbidden_hits': {w: content.count(w) for w in forbidden if w in content},
       'required_missing': [w for w in required if w not in content]})
```
