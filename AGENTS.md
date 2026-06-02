# Repository Guidelines

## Project Structure & Module Organization

This repository packages the `internal-data-query` skill. Core behavior lives in `SKILL.md`; package metadata and file hashes live in `manifest.json`. Python CLI utilities are in `scripts/`, including connection setup, query execution, Metabase helpers, manifest validation, sensitive-info scanning, and offline evals. Templates are in `templates/`, method references and historical SQL are in `references/`, and shared query knowledge is under `data-query-knowledge/`. Offline fixtures live in `evals/`. Release assets are generated under `dist/` and are not source.

## Build, Test, and Development Commands

- `python scripts/validate_manifest.py`: verify every packaged file against `manifest.json`.
- `python scripts/scan_sensitive_info.py .`: scan the repo for credentials, internal URLs, and other sensitive material.
- `python scripts/eval_skill_pack.py --allow-blocked`: run the offline eval pack without real data connections.
- `python scripts/query_static_check.py --sql-file evals/fixtures/readonly.sql --engine clickhouse`: validate readonly SQL safety rules.
- `python scripts/package_skill.py --json`: build the release zip in `dist/`.
- `python -m pip install -r requirements.txt`: install optional runtime dependencies for real queries and exports.

## Coding Style & Naming Conventions

Use Python 3 scripts with explicit CLI arguments via `argparse`. Prefer small, single-purpose scripts and repository-relative paths unless a user-owned local path is required. Use snake_case for Python functions, variables, and script names. Keep templates and knowledge files descriptive, lowercase, and hyphen-separated, for example `metric-definition.md`.

## Testing Guidelines

The primary test harness is `scripts/eval_skill_pack.py`; it must remain offline and fixture-driven. Add fixtures under `evals/fixtures/` and update expected outputs when behavior changes intentionally. For query changes, include static checks for readonly behavior, rejected DML, and required time ranges. Do not require live Metabase, ClickHouse, ODPS, or MySQL access for CI validation.

## Commit & Pull Request Guidelines

Recent commits use short imperative summaries, such as `Add automated release versioning`. Keep commits focused and mention user-visible changes first. PRs should include purpose, changed scripts or templates, validation commands run, and any manifest or release impact.

## Security & Configuration Tips

Never commit real credentials, tokens, hosts, sessions, exports, or local `data-sources.yaml` files. Real profiles belong in `~/.internal-data-query/data-sources.yaml` or another user-owned local path with restrictive permissions. After changing packaged files, update `manifest.json` and rerun validation.

## Agent-Specific Instructions

Before any git workflow action, ask for and receive explicit approval. This includes branch creation or switching, commit, rebase, push, pull, merge, cherry-pick, reset, PR creation, and remote tracking changes. Prefer Chinese for user-facing responses when practical.
