# Project Quality Hub

`project-quality-hub` wraps project analysis, multi-branch intelligence, smart incremental updates, and quality scoring into a Model Context Protocol (MCP) server that works with clients such as Claude and Cursor.

## Key Features
- **Project Graph Analysis**: Build a knowledge graph with dependency and entity insight.
- **Branch Awareness**: Analyse, switch, and compare Git branches individually.
- **Smart Incremental Updates**: Watch file changes via `watchdog` and refresh results in near real time.
- **Quality Scoring**: Combine metrics, static analysis, and heuristics to produce a 0‑100 score with recommendations.

## Installation
```bash
pip install project-quality-hub
```
For development:
```bash
pip install -e .[dev]
```

## Command Line Interface
Installing the package adds a `project-quality-hub` CLI which surfaces the core capabilities:
```bash
# Analyse and cache a project (monitoring is opt-in)
project-quality-hub analyze /path/to/project [--force] [--monitor]

# Retrieve project summary
project-quality-hub summary /path/to/project

# Score the whole project or a single file
project-quality-hub score /path/to/project [--file relative/path.py] [--max-files N]

# Control incremental monitoring
project-quality-hub monitor /path/to/project start|stop|status

# Start the MCP stdio server (alias of the dedicated script)
project-quality-hub server
```

Prefer a dedicated server command? Use:
```bash
project-quality-hub-server
```
Check all CLI options via `project-quality-hub --help`.

## Integrating with MCP Clients
1. **Install dependencies** (`pip install project-quality-hub`). For offline environments, pre-download the wheels for `mcp`, `networkx`, `watchdog`, etc.
2. **Configure a stdio endpoint** (Claude Desktop example):
   ```json
   {
     "endpoints": [
       {
         "name": "project-quality-hub",
         "command": ["project-quality-hub-server"],
         "transport": { "type": "stdio" }
       }
     ]
   }
   ```
3. **Restart the client** so the tools appear automatically.
4. **Reuse in scripts**: CLI and MCP server share the same implementation, enabling automated workflows and conversational assistants alike.

## Architecture
- `project_quality_hub/core`: project knowledge graph, branch management, incremental updates.
- `project_quality_hub/quality`: AST parsing, static analysis adapters, quality scoring.
- `project_quality_hub/server`: stdio MCP server, tool registry, task management.
- `project_quality_hub/cli.py`: command line entry point.
- `tests/`: smoke tests (extend with integration/acceptance cases as needed).

## Development Guide
1. **Install dependencies**
   ```bash
   pip install -e .[dev]
   ```
   For restricted networks, stage wheel files and install offline.

2. **Run tests**
   ```bash
   pytest
   ```
   Currently covers import smoke tests; contributions for end-to-end coverage are welcome.

3. **Static analysis / formatting**
   ```bash
   pip install ruff black
   ruff check src
   black src
   ```

4. **Notes**
   - Quality scoring inspects compiled assets (`dist/` etc.). Clean artifacts or limit the scope with `--max-files` when necessary.
   - `watchdog` requires file-system permissions; disable monitoring in sandboxes/CI as appropriate.

## Release Checklist
1. Bump the version in `pyproject.toml` and `project_quality_hub/__init__.py`.
2. Build artifacts:
   ```bash
   python -m build
   ```
3. Publish to PyPI:
   ```bash
   twine upload dist/*
   ```
4. Tag the release and update GitHub release notes.

## License
Distributed under the [MIT License](LICENSE).

## Contributing
We welcome issues and pull requests—see the [CONTRIBUTING guide](docs/CONTRIBUTING.md) for details on coding standards and workflow.
