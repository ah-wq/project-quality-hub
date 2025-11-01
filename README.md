# Project Quality Hub

[![CI](https://github.com/WangQiao/project-quality-hub/actions/workflows/ci.yml/badge.svg)](https://github.com/WangQiao/project-quality-hub/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/project-quality-hub.svg)](https://pypi.org/project/project-quality-hub/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Model Context Protocol tooling that gives AI assistants a trustworthy project graph, branch intelligence, smart incremental updates, and explainable quality scores.

> Looking for the Chinese overview? Jump to [中文简介](#中文简介).

## Quickstart

```bash
# 1. Install the package
pip install project-quality-hub

# 2. Analyse a repository and optionally enable live monitoring
project-quality-hub analyze ./demo --monitor

# 3. Retrieve the knowledge graph summary
project-quality-hub summary ./demo

# 4. Score a project or a single file
project-quality-hub score ./demo --file src/example.py --max-files 50
```

Prefer editable installs while developing?
```bash
pip install -e .[dev]
pytest
ruff check src
```

## Why Project Quality Hub?

- **Project graph intelligence** – Build a knowledge graph with entity-level insights, dependency edges, and risk scoring so assistants can reason about codebases.
- **Branch-aware memories** – Cache per-branch analyses, switch between them, and compare git branches without rebuilding from scratch.
- **Smart incremental updates** – Watch file changes with `watchdog` to refresh analysis results in the background.
- **Quality scoring built for AI** – Blend metrics, static-analysis findings, and heuristics into transparent 0‑100 scores with actionable recommendations.
- **MCP-native experience** – Ship the same capabilities via CLI commands or an MCP stdio server for Claude, Cursor, and other compatible clients.

## CLI Essentials

```bash
# Analyse and cache a project (monitoring is opt-in)
project-quality-hub analyze /path/to/project [--force] [--monitor]

# Retrieve a summary of the analysed project
project-quality-hub summary /path/to/project

# Run quality scoring across the repo or a single file
project-quality-hub score /path/to/project [--file relative/path.py] [--max-files N]

# Control background monitoring
project-quality-hub monitor /path/to/project start|stop|status

# Launch the MCP stdio server
project-quality-hub server
project-quality-hub-server  # dedicated entry point
```

See `project-quality-hub --help` for the full command list.

## MCP Client Integration

1. Install the package on the machine hosting your MCP server.
2. Point your client at the stdio transport. Claude Desktop example:
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
3. Restart the client. The tools listed above become available instantly.
4. Need more detail? Check the full walkthrough in [`docs/integration.md`](docs/integration.md).

## Project Layout

- `src/project_quality_hub/core`: knowledge-graph modelling, multi-branch management, incremental updates.
- `src/project_quality_hub/quality`: AST inspection, static-analysis adapters, scoring heuristics.
- `src/project_quality_hub/server`: MCP stdio adapter, task orchestration, utilities.
- `src/project_quality_hub/cli.py`: CLI entry point mirroring the MCP toolset.
- `tests/`: import safety plus behavioural tests for scoring and parsing.
- `docs/`: design notes, client integration, contributing guide.

## Testing & Development

- Run unit tests with `pytest`.
- Lint with `ruff check src`; format with `black src`.
- Export `WATCHDOG_FORCE_POLLING=1` in sandboxed environments to guarantee deterministic monitoring.
- Clean build artefacts (`dist/`, `build/`) before running quality scoring for the most accurate results.

## Releases

1. Bump the version in `pyproject.toml` and `project_quality_hub/__init__.py`.
2. Build artefacts via `python -m build`.
3. Publish to PyPI using `twine upload dist/*`.
4. Tag the release, open a GitHub Release, and capture the highlights in `CHANGELOG.md`.

## Contributing

We welcome issues and pull requests! Review the [contributing guide](docs/CONTRIBUTING.md) for coding standards, workflow, and communication expectations. A behaviour code and PR templates will keep contributions friendly and consistent.

## License

Distributed under the [MIT License](LICENSE).

---

## 中文简介

`project-quality-hub` 将项目图谱、分支管理、智能增量更新和质量评分能力封装为 Model Context Protocol (MCP) 服务，方便 Claude、Cursor 等客户端直接调用。

- **项目图谱分析**：构建实体级知识图谱，输出依赖关系和风险评估。
- **多分支记忆**：缓存并比较不同 Git 分支的分析结果，快速切换。
- **实时增量更新**：结合 `watchdog` 监听文件变化，自动刷新结果。
- **质量评分**：综合指标与静态分析，提供 0-100 分的评分和优化建议。

仓库提供 CLI 与 MCP 双入口。更多集成细节请参阅 [`docs/integration.md`](docs/integration.md)，贡献准则见 [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md)。

---

Historical versions of this README remain available in [`README_EN.md`](README_EN.md).
