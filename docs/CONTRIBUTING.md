# Contributing to Project Quality Hub

Thanks for taking the time to contribute! This guide outlines the expectations for code, documentation, and collaboration so new features stay maintainable and friendly for AI clients.

## Getting Started

1. Fork the repository and clone your copy locally.
2. Create a virtual environment and install dependencies:
   ```bash
   pip install -e .[dev]
   ```
3. Run the test suite to ensure the baseline is green:
   ```bash
   pytest
   ```

## Development Workflow

- Work from a dedicated feature branch, e.g. `feat/improve-scoring`.
- Keep changes focused. If a change requires multiple logical steps, split it into separate commits or pull requests.
- Use conventional commit messages (`feat: add branch comparison`, `fix: handle missing repo`) so changelog generation is straightforward.

## Coding Standards

- Target Python 3.10+; include type hints on public interfaces.
- Follow the default `ruff` rules (aligned with PEP 8). Run `ruff check src` before opening a PR.
- Format Python files with `black` to avoid style churn.
- Write docstrings for new public modules, functions, and classes when behaviour is non-trivial.
- Prefer descriptive logging over silent failures. If an exception is swallowed intentionally, document why.

## Testing

- Add or update unit tests alongside your changes. Place them under `tests/` mirroring the module layout.
- Use `pytest -k <pattern>` for focused development loops, then run `pytest` with no filters before submitting.
- Integration tests that exercise the CLI or MCP server belong in `tests/integration/`. Skip them in environments where external tooling (e.g. git) is unavailable, and mark the reason with `pytest.mark.skipif`.

## Documentation

- Update `README.md` when user-facing behaviour changes.
- Extend `docs/` for in-depth design notes or client integration walkthroughs.
- When adding commands or configuration options, document them near the relevant module and in the CLI help text.

## Pull Request Checklist

- [ ] Tests added or adjusted and passing locally.
- [ ] `ruff check src` reports no errors.
- [ ] Documentation updated where appropriate.
- [ ] CI badge remains green (GitHub Actions will verify on the PR).
- [ ] Screenshots or terminal excerpts attached when behaviour changes materially.

## Communication

- Open an issue before large refactors to confirm direction.
- Be responsive to review feedback. If you cannot continue with a change, let maintainers know so someone else can pick it up.
- Respectful, inclusive language is expected. We follow the spirit of the [Contributor Covenant](https://www.contributor-covenant.org/) even without copying it verbatim.

Thanks for helping make Project Quality Hub a reliable tool for developers and assistants alike!
