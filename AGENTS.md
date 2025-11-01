# Repository Guidelines

## Project Structure & Module Organization
Source lives in `src/project_quality_hub`, split into `core/` for project graph logic, `quality/` for scoring utilities, and `server/` for the MCP stdio adapter. The CLI entry point (`cli.py`) re-exports these capabilities. Tests reside in `tests/` and currently cover import safety; expand them alongside new features. Reference material and design notes sit in `docs/`.

## Build, Test, and Development Commands
- `pip install -e .[dev]`: set up an editable environment with pytest and ruff.
- `pytest`: run the Python test suite; add `-k pattern` for focused runs.
- `ruff check src`: lint the package; run before committing to keep CI green.
- `python -m build`: create distribution artifacts prior to release.
- `project-quality-hub analyze ./demo [--force] [--monitor]`: smoke-test the CLI; monitoring is opt-in.

## Coding Style & Naming Conventions
Target Python 3.10+ with 4-space indentation and type hints on public interfaces. Follow `ruff` defaults (PEP 8, sensible imports) and auto-format new modules with `black` before submission. Modules and functions use `snake_case`; classes use `PascalCase`; CLI commands stay hyphenated to match the published script names.

## Testing Guidelines
Prefer `pytest` functions named `test_<behaviour>` inside files that mirror the module under test. New features should include happy-path and failure-mode coverage; integration exercises that hit the CLI or MCP server belong in `tests/integration/` if added. Aim to keep quality scoring rules covered by unit assertions so regressions are obvious.

## Commit & Pull Request Guidelines
History is fresh, so adopt Conventional Commit prefixes (`feat:`, `fix:`, `docs:`) with imperative summaries. Group related work per commit and reference issue numbers when available. Pull requests should describe intent, list notable changes, outline testing performed, and include screenshots or captured CLI output when behaviour changes.

## MCP Agent Notes
When iterating on the server, run `project-quality-hub-server` in a separate terminal and point your MCP client at the `stdio` transport. Use small sample repositories while refining scoring rules to keep responses fast, and flush caches by rerunning `analyze --force` whenever the storage schema changes. The incremental monitor now falls back to watchdog’s polling observer automatically; if you need deterministic behaviour in sandboxes, export `WATCHDOG_FORCE_POLLING=1` or trigger monitoring explicitly with `start_monitoring`.
