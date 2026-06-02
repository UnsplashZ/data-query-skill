# Repository Guidelines

## Project Structure & Module Organization

This repository packages the `internal-data-query` skill. Core behavior lives in `SKILL.md`. Python CLI utilities are in `scripts/`, including connection setup, query execution, Metabase helpers, sensitive-info scanning, and post-install checks. Templates are in `templates/`; generic query method references are in `references/`. Do not store real business schema, historical SQL, exports, credentials, or team knowledge in this repository. Release assets are generated under `dist/` and are not source.

## Build, Test, and Development Commands

- `python scripts/scan_sensitive_info.py .`: scan the repo for credentials, internal URLs, and other sensitive material.
- `python -m py_compile scripts/*.py`: catch syntax errors in packaged scripts.
- `python scripts/package_skill.py --json`: build the release zip in `dist/`.
- `python scripts/post_install_check.py --offline-ok`: run lightweight install smoke checks.
- `python -m pip install -r requirements.txt`: install optional runtime dependencies for real queries and exports.

## Coding Style & Naming Conventions

Use Python 3 scripts with explicit CLI arguments via `argparse`. Prefer small, single-purpose scripts and repository-relative paths unless a user-owned local path is required. Use snake_case for Python functions, variables, and script names. Keep templates and knowledge files descriptive, lowercase, and hyphen-separated, for example `metric-definition.md`.

## Testing Guidelines

Keep validation lightweight. At minimum, run Python compilation, sensitive-info scanning, packaging, and post-install smoke checks. Do not require live Metabase, ClickHouse, ODPS, or MySQL access for CI validation.

## Commit & Pull Request Guidelines

Recent commits use short imperative summaries, such as `Add automated release versioning`. Keep commits focused and mention user-visible changes first. PRs should include purpose, changed scripts or templates, and validation commands run.

## Security & Configuration Tips

Never commit real credentials, tokens, hosts, sessions, exports, local `data-sources.yaml` files, business schema snapshots, historical SQL, or team knowledge. Real profiles belong in `~/.internal-data-query/data-sources.yaml` or another user-owned local path with restrictive permissions.

## Agent-Specific Instructions

Before any git workflow action, ask for and receive explicit approval. This includes branch creation or switching, commit, rebase, push, pull, merge, cherry-pick, reset, PR creation, and remote tracking changes. Prefer Chinese for user-facing responses when practical.
