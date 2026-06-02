---
name: renewal-forecast-vocal-method
description: Understand and reuse the user's vocal renewal forecasting method from the retired analysis project. Focus on cohort construction, primary service start anchoring, start-conversion detection, and future-month order/GMV forecasting.
---

# Vocal renewal forecasting method

Use this when the task is to reason about or reimplement the user's vocal renewal forecast logic, rather than blindly averaging by stage.

## Problem this method solves
Predict future months' actual renewal orders and GMV, not future class openings.

## Source material
- `~/.hermes/docs/projects/analysis-methods/renewal-forecast-vocal-method.md`
- Original source (may be deleted later): `/Users/zheng/dev/analysis/tasks/renewal_forecast_vocal/`

## Core business rules
1. Build cohorts by `阶段 × 营期名称`, not by stage-wide averages.
2. If a cohort has multiple `服务开课时间`, identify `主服务开课时间`:
   - choose the open time with the most orders
   - tie-break by earlier open time
3. Treat `1970-01-01` style timestamps as placeholders -> missing.
4. Exclude special camps like `延期` and `冻课`.
5. Identify `开始转化日` by cumulative orders:
   - anchor on `主服务开课时间`
   - aggregate daily orders
   - the first date where cumulative orders reach 15% of final orders is the start-conversion date
6. Forecast future months using:
   - mature cohorts' observed renewal rate
   - post-start-conversion release distribution
   - historical average GMV per renewal order
7. Add a confidence label based on matched cohorts and mature student count.

## Why this matters
- First-order dates are noisy because of long-tail orders.
- Start-conversion day is a better signal for when a cohort truly begins to release demand.
- Mixing different camps inside the same stage hides important cohort differences.

## Outputs to preserve
- cohort overview
- monthly order distribution
- start-conversion recognition table
- future-month forecast summary
- method diagnostics

## Common mistakes
- averaging all camps within a stage
- using first order date instead of start-conversion date
- keeping placeholder 1970 timestamps
- failing to filter delay/frozen camps
- using immature cohorts as if they were complete
