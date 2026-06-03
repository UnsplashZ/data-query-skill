# YYYY-MM-DD / domain / topic / sql review

- Status: `PASS / PASS_WITH_RISKS / FAIL`
- Owner:
- Source:
- Related files:
- Validation:
- Risk:
- Suggested file: `data-query-work/reviews/YYYY-MM-DD__domain__topic__sql-review.md`
- SQL file:
- Engine:
- Prior brief:
- Static check:
- Sample query:

## Checks

- [ ] Source and schema verified.
- [ ] Repo docs, discovered schema index, Metabase, historical SQL, and knowledge were searched before SQL drafting.
- [ ] `scripts/query_static_check.py` ran before execution.
- [ ] Static check errors are absent.
- [ ] Static check warnings are recorded.
- [ ] Time range and time field are correct.
- [ ] Grain is controlled before joins.
- [ ] Join cardinality checked.
- [ ] Status/state/cancel/error filters match the metric.
- [ ] Amount units are clear.
- [ ] Query is readonly.
- [ ] Small sample executed before full range.
- [ ] Validation checked row count, join hit rate/cardinality, enum distribution, NULL/0 distribution, amount units, time field, and dedup risk as applicable.
- [ ] Result sanity checked.

## Risks

-

## Required Fixes

-

## Final Decision

-
