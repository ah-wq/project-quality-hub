# Integrating Project Quality Hub with AI Clients

Project Quality Hub ships both a CLI and a Model Context Protocol (MCP) stdio server so AI assistants can analyse repositories, monitor changes, and surface quality insights on demand. This guide walks through common setups.

## Prerequisites

- Python 3.10 or newer.
- A cloned repository you want to analyse.
- (Optional) Git available on the `PATH` for branch-aware features.
- For long-running monitoring, ensure the process can watch the filesystem. When polling is required (e.g. in sandboxed environments), export `WATCHDOG_FORCE_POLLING=1`.

Install the package on the machine hosting your MCP server:

```bash
pip install project-quality-hub
```

## Launching the MCP Server

Run the stdio server directly:

```bash
project-quality-hub-server
```

Or call the CLI alias:

```bash
project-quality-hub server
```

Both commands expose the same tools defined in `src/project_quality_hub/server/tools.py`.

## Claude Desktop

1. Open the Claude configuration file (usually `~/.claude/config.json`).
2. Add the endpoint definition:
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
3. Restart Claude Desktop. The assistant now offers the `analyze_project`, `get_project_summary`, `score_project`, and related tools automatically.

## Cursor

1. Launch `project-quality-hub-server` in a terminal.
2. In Cursor, open *Settings → Labs → MCP Servers* and add:
   ```
   project-quality-hub = "project-quality-hub-server"
   ```
3. Restart Cursor. Interact with the new tools via the command palette or chat sidebar.

## CLI-Only Workflows

You can access the same capabilities from shell scripts or CI pipelines:

```bash
# Analyse a repo and cache the knowledge graph
project-quality-hub analyze /path/to/repository --force

# Compare two branches
project-quality-hub compare /path/to/repository main feature/x

# Score the project and dump detailed recommendations
project-quality-hub score /path/to/repository --max-files 200 --format json
```

Combine commands with `jq`, `rg`, or custom tooling to feed results into dashboards or automation.

## Troubleshooting

- **Command not found**: Ensure the Python environment (or virtualenv) holding `project-quality-hub` is on your `PATH`.
- **Monitoring does not start**: Check filesystem permissions. In containerised setups enable polling via `WATCHDOG_FORCE_POLLING=1`.
- **Slow analyses**: Use `--max-files` to limit scope, or exclude generated directories before running `analyze`.
- **Large repositories**: Persist the cache directory (controlled by `ProjectMemoryManager`) to avoid repeated full analyses.

Need more ideas? File an issue with your client setup and we will extend this document.
