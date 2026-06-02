# Data Query Checklist

## Intake

- [ ] Business question has been restated as a data problem.
- [ ] Metric/entity is clear.
- [ ] Time range and time field are clear.
- [ ] Grain is clear: order, user, day, month, SKU, camp, channel, class, etc.
- [ ] Filters and scope are clear.
- [ ] Output shape is clear: SQL, result table, CSV/XLSX, dashboard input, report.
- [ ] Result use is clear: one-off answer, meeting, dashboard, recurring report, API design, QA.
- [ ] Ambiguous choices are either clarified or written as assumptions.

## Source Explorer

- [ ] Current repository/workspace has been searched.
- [ ] External schema index, live metadata, or target-repo data catalog has been searched when available.
- [ ] Scoped schema refresh has been run with `--table-list` when the question is limited to known tables.
- [ ] External historical SQL index has been searched when available.
- [ ] Target-repo runbooks or business docs have been searched when available.
- [ ] Recommended and rejected sources are listed.
- [ ] Source status is labeled: confirmed, evidence, historical, draft, gap, unknown.
- [ ] Key fields exist.
- [ ] Time, amount, and status fields are understood.
- [ ] Join keys and grain are checked.

## SQL Author

- [ ] SQL is readonly.
- [ ] Time range is explicit.
- [ ] Scope, limit, or aggregation constraint is present.
- [ ] Base grain is controlled before joins and aggregation.
- [ ] Date boundaries are explicit.
- [ ] Ratio calculations handle divide-by-zero.
- [ ] Refund/cancel/status filters match the stated metric.
- [ ] Historical SQL is not copied without current review.
- [ ] Source, fields, assumptions, and risks are documented.

## Execution

- [ ] Schema/dry-run/metadata check completed.
- [ ] `sample_tables.py` dry-run or sample completed when schema-index table examples are needed.
- [ ] Small-range or `LIMIT` query completed.
- [ ] Enum/status distribution checked.
- [ ] Join cardinality checked.
- [ ] Row, amount, user, or order sanity checks completed.
- [ ] Full-scope query executed, or marked unverified with reason.

## Review

- [ ] SQL answers the original business question.
- [ ] Time range, scope, and grain are correct.
- [ ] Joins do not inflate metrics unexpectedly.
- [ ] Distinct counts and row counts are not mixed.
- [ ] Historical or evidence-only sources are not presented as confirmed.
- [ ] SQL dialect matches the chosen engine.
- [ ] High-risk metric is cross-checked, or lack of cross-check is stated.
- [ ] Review status is `PASS`, `PASS_WITH_RISKS`, or `FAIL`.

## Delivery

- [ ] Executable SQL or result path is provided.
- [ ] Data source, tables, and key fields are listed.
- [ ] Business definition and assumptions are stated.
- [ ] Verification performed is stated.
- [ ] Remaining risks and follow-up checks are stated.
- [ ] Reusable outputs are saved under `data-query-work/` or the user-selected local folder.
- [ ] Exports and sample outputs are masked before writing; residual sensitive scan has no high-risk findings.
