# Data Query Knowledge

This directory is the shared, repo-native query knowledge base. Store only
reviewable text assets here: metric definitions, source profiles, join
contracts, golden queries, semantic notes, review records, and promotion logs.

Do not store credentials, private endpoints, local exports, temporary SQL, or
personal configuration in this directory. Put those in `data-query-work/` or a
local-only path.

Lifecycle:

```text
draft -> candidate -> reviewed -> approved -> deprecated
```

Default search excludes `draft`, `candidate`, `deprecated`, and expired items.
`approved` items still require checking `expires_at`, `validation_evidence`,
and applicability scope before reuse.
