---
name: profitability-analysis-local
description: Run the user's migrated local profitability analysis workflow from Hermes without depending on OpenClaw. Use when the user wants to compute 分工作室利润率 from the standard Excel workbook.
---

# Local profitability analysis

Use this for the user's migrated 分工作室利润率 workflow.

Files:
- Script: `~/.hermes/python/projects/profitability/calc_profitability.py`
- Rules: `~/.hermes/docs/projects/profitability/rules.md`

## Environment
Run in conda env `hermes-sql`.

## Command
```bash
eval "$(conda shell.bash hook)"
conda activate hermes-sql
python ~/.hermes/python/projects/profitability/calc_profitability.py \
  --input-file /path/to/input.xlsx \
  --output-file ~/.hermes/output/exports/profitability_result.csv
```

## Notes
- Input workbook should contain sheets like `4月GMV`, `分SKU预算`, `人力成本`.
- If `--output-file` is omitted, the script writes `分工作室利润率_SKUx渠道.csv` next to the input workbook.
- Business rules are documented in `~/.hermes/docs/projects/profitability/rules.md`.
