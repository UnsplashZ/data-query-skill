---
name: sql-query-method-internal
description: Use when answering internal business data questions with SQL across ODPS, ClickHouse, or similar warehouse/query engines. Provides a reliability-first workflow for choosing the data source, verifying schema, writing dialect-safe SQL, testing locally, and reporting results without fabricating data.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [sql, odps, clickhouse, data-analysis, schema-verification]
    related_skills: [odps-clickhouse-schema-kb, local-cashflow-sql-querying, refund-report-method, handover-stats-report-method]
---

# SQL Query Method

## Overview

This skill captures a reliability-first way to answer business questions with SQL. The core principle is simple: do not guess table names, fields, dialect behavior, business definitions, or numeric results. Determine the right data source, inspect schema and prior knowledge, write a candidate query, run small tests, verify the output, and only then provide SQL and results.

It is designed for agents working with ODPS/MaxCompute, ClickHouse, Feishu/Sheets reporting, or any environment where a wrong SQL answer is worse than a slower answer.

## When to Use

Use this skill when:

- A user asks for a SQL query, business metric, export, report, or data diagnosis.
- The task may involve ODPS, ClickHouse, local warehouse scripts, data marts, dashboards, or Feishu reports.
- The user gives a business definition but not the exact physical table/field names.
- The output must include actual query results, a file, or a directly executable SQL statement.
- Prior definitions or existing SQL may exist and should be reused instead of reinvented.

Do not use this skill as the only source of truth for domain-specific definitions. If a task has a dedicated skill or runbook, load it too and let the domain skill define the business口径.

## Non-Negotiable Rules

1. Never fabricate data, table names, fields, row counts, or query results.
2. Decide the data source before writing final SQL.
3. Verify schema before relying on a field.
4. Run a small test before a full query when execution is available.
5. Treat business口径 and physical fields as separate layers.
6. State unverified assumptions explicitly.
7. If query execution is impossible, mark the SQL or result as unverified.
8. Prefer existing validated SQL, reports, skills, and schema indexes over fresh guessing.

## Standard Workflow

### 1. Restate the Request as a Data Problem

Extract these items before writing SQL:

- Metric or entity: GMV, refund amount, order count, user count, cohort, conversion, retention, etc.
- Grain: order, user, camp, class, teacher, date, month, SKU, channel, track, etc.
- Time range: start/end date, pay date/refund date/handover date/event date.
- Filters: product, front/back-end, camp, stage, payment status, refund status, official class, user type.
- Output shape: direct SQL, table, Excel/CSV, Feishu Sheet, chart, diagnosis text.
- Required freshness: realtime/near-realtime vs offline warehouse standard口径.

If any missing item materially changes the query, ask one concise clarification question. If there is an obvious default in the user’s known context, proceed but state the assumption.

### 2. Choose the Data Source First

Use this decision rule:

- ODPS / MaxCompute: preferred for standard warehouse口径, dwd/dws tables, finance/cashflow definitions, offline wide tables, historically consistent reporting.
- ClickHouse: preferred for fast lookup, dashboard-backed tables, Feishu group realtime questions, exploratory validation, large but indexed exports, or when the relevant CK table is already known.
- Existing local scripts/reports: preferred when a maintained project already implements the required口径.
- Cross-source verification: use when the result is high-stakes, definitions are uncertain, or ODPS and ClickHouse may differ.

Do not switch sources silently. If using a faster source instead of the standard source, say so and explain the expected口径 difference.

### 3. Search Existing Knowledge Before Writing New SQL

Check in this order:

1. Dedicated domain skills or runbooks.
2. Existing project SQL files and cron scripts.
3. Local schema knowledge base or data catalog.
4. Prior exports/reports that use the same metric.
5. Live database schema inspection.

Look for:

- The canonical fact table.
- Date/time fields.
- Status fields.
- Amount fields and units.
- Join keys.
- Partition fields.
- Known table aliases, renamed fields, or source mappings.
- Existing filters for the exact business口径.

### 4. Verify Schema and Field Semantics

Before relying on a field, verify:

- The field exists in the chosen table.
- Its type supports the planned filter or aggregation.
- Its business meaning matches the request.
- Date fields use the expected timezone and type.
- Amount fields are in the expected unit.
- Status fields use the expected enum values.
- Join keys are available on both sides and at compatible grain.

For ClickHouse, inspect `system.columns` and sample enum values. For ODPS, inspect table schema and partitions. In any system, sample a few rows only when safe.

### 5. Write Candidate SQL with Grain Control

Build the query from the target grain upward:

1. Create a base CTE/subquery at the correct grain.
2. Apply source filters and status filters early.
3. Normalize dates and product/channel labels explicitly.
4. Join dimensions only after checking join cardinality.
5. Aggregate only after the base grain is correct.
6. Keep final aliases ASCII inside SQL if the driver has encoding issues; rename to Chinese in pandas/export layer.

Common grain mistakes:

- Joining user-level attributes into order-level facts and then counting rows as users.
- Aggregating before excluding refunds, cancelled orders, or related tail payments.
- Using a current-status table for a historical-state question.
- Treating “has WeCom friend” as proof of “in official class” without a validated business rule.

### 6. Check Dialect and Engine-Specific Rules

ClickHouse checks:

- Confirm server version if syntax is uncertain.
- Avoid unsupported JOIN conditions in older versions.
- Use subqueries when reusing aggregate aliases in later calculations.
- Be careful comparing String dates with Date/DateTime.
- For collapsing/replacing style tables, check whether `FINAL` and sign filters are required.
- Avoid Chinese SQL aliases if the client/driver may decode server errors incorrectly.
- Do not default to `local` tables unless the environment requires them.

ODPS / MaxCompute checks:

- Ensure partition filters are present when needed.
- Validate `${param}` and template variables before execution.
- Use MaxCompute-compatible date functions and type casts.
- Check whether window functions and CTEs follow the installed dialect constraints.
- Avoid full table scans unless the scope requires it and the user accepts the cost.

Generic SQL checks:

- Null-safe division with `nullIf`, `CASE`, or equivalent.
- Explicit inclusive/exclusive date boundaries.
- Avoid ambiguous column references after joins.
- Avoid grouping by display labels if the raw key is needed later.
- Preserve stable ordering for exports.

### 7. Test in Small Scope First

When execution is available, run tests in this order:

1. Schema query or dry-run equivalent.
2. Small date range or `LIMIT` query.
3. Enum/sanity checks for filters.
4. Join cardinality check.
5. Aggregate reasonableness check.
6. Full-range query.

Examples of sanity checks:

- Row count is non-zero when expected.
- Payment status distribution matches the chosen filters.
- Refund amount does not exceed GMV without an explainable reason.
- Distinct users/orders are not inflated after joins.
- Date range matches the request exactly.
- Top SKU/channel/camp values look plausible.

If a test fails, fix the SQL before presenting it. Do not present a failed SQL as final output.

### 8. Produce the Final Answer

Final output should include the parts the user needs, not every intermediate detail:

- The directly executable SQL, if requested.
- The result table or output file path, if produced.
- Data source used.
- Main tables and fields used.
- Key口径 choices.
- Verification performed.
- Remaining assumptions or unverified parts.

For business users, prioritize the result and口径. For technical users, include the SQL and enough verification details to reproduce it.

## Internal References Included

This internal package includes extra references for data department users:

- `references/schema-kb/`: generated ODPS / ClickHouse schema KB index files.
- `references/old-sql/`: historical SQL library and prior query-result SQLs.
- `references/method-skills/`: related data-science skills and reference notes for business definitions and maintenance workflows.

Use these references before writing new SQL. Prefer previously validated SQL and schema KB over guessing.

## Reusable Query Skeletons

### ClickHouse Schema Inspection

```sql
SELECT
    table,
    name,
    type,
    position
FROM system.columns
WHERE database = currentDatabase()
  AND table IN ('your_table_1', 'your_table_2')
ORDER BY table, position;
```

### ClickHouse Enum/Distribution Check

```sql
SELECT
    status_field,
    count() AS row_count
FROM your_table
GROUP BY status_field
ORDER BY row_count DESC
LIMIT 50;
```

### Safe Ratio Pattern

```sql
SELECT
    scope,
    numerator,
    denominator,
    round(numerator / nullIf(denominator, 0), 6) AS ratio
FROM
(
    SELECT
        scope,
        sum(metric_a) AS numerator,
        sum(metric_b) AS denominator
    FROM base
    GROUP BY scope
) t;
```

### Inclusive/Exclusive Date Boundary

```sql
WHERE event_time >= toDateTime('2026-05-01 00:00:00')
  AND event_time <  toDateTime('2026-06-01 00:00:00')
```

### Join Cardinality Check

```sql
SELECT
    count() AS rows_after_join,
    uniqExact(base_id) AS distinct_base_ids
FROM
(
    SELECT base_id
    FROM base_table
    WHERE event_date >= '2026-05-01'
) b
LEFT JOIN dim_table d
    ON b.base_id = d.base_id;
```

If `rows_after_join` is much larger than `distinct_base_ids`, inspect whether the dimension table has multiple rows per key.

## Business口径 Handling

Treat every business term as a definition to resolve, not a keyword to search literally.

Examples:

- “GMV” may mean pay amount, original price, net amount, paid order amount, or finance-recognized amount.
- “退款率” may use refund amount / GMV, refund users / paid users, or cohort refund over M0/M1.
- “前端” may be a channel field, organization field, or product-flow label.
- “正价班” may come from order attributes, handover records, class records, or a combined rule.
- “声乐 SKU” may be `main_goods_sku`, `cci3_name`, `sku`, `main_goods_name`, or another product field depending on table.

When a term is ambiguous:

1. Search existing definitions first.
2. If a known user/project口径 exists, use it and state it.
3. If no known口径 exists, ask or provide a clearly labeled assumption.
4. Do not silently substitute a convenient field.

## Export and Reporting Rules

When producing tabular deliverables:

- Use Chinese headers when the deliverable is for Chinese business users.
- Keep numeric cells numeric in Excel/Sheets; do not convert to strings like “12.3万” or “45%” unless explicitly requested.
- Keep blank cells blank when the target system expects blanks.
- Include a “口径说明” sheet or section for non-trivial reports.
- Save intermediate SQL and scripts in a maintainable project/output directory if the query may be reused.
- For large exports, consider user-level summaries, chunked queries, cached intermediate files, and resumable processing.

## Failure Handling

If the query fails:

- Report the error class plainly: syntax, field missing, permission, timeout, memory, network, dialect, data missing, or口径 unclear.
- Try the cheapest safe fix first: schema inspection, smaller date range, corrected type cast, or simplified join.
- For large ClickHouse queries, split into smaller queries and merge locally when appropriate.
- For ODPS partition or cost issues, narrow partitions and verify filters.
- If the result remains unverified, say it is unverified.

Do not hide a failed test behind a polished explanation.

## Common Pitfalls

1. Writing SQL before choosing ODPS vs ClickHouse.
2. Using a business label as a physical field name without schema verification.
3. Mixing order-level and user-level grains.
4. Reusing old SQL without checking whether the business口径 changed.
5. Filtering by display name when an ID/key is required for correctness.
6. Comparing dates as strings when the column is DateTime, or the reverse.
7. Forgetting partition filters in ODPS.
8. Assuming dashboards and offline warehouses use identical definitions.
9. Returning SQL that was never run while implying it was verified.
10. Renaming fields in SQL in a way that breaks the client driver or downstream export.

## Verification Checklist

Before finalizing:

- [ ] Data source selection is explicit.
- [ ] Required business口径 is known or assumptions are stated.
- [ ] Tables and fields were checked through schema/catalog/prior validated SQL.
- [ ] Dialect-specific risks were checked.
- [ ] Query grain is correct.
- [ ] Joins do not inflate metrics unexpectedly.
- [ ] Small-scope test ran successfully, or lack of execution is stated.
- [ ] Full query/result was verified when possible.
- [ ] Final answer includes SQL/result,口径, and remaining uncertainty.
