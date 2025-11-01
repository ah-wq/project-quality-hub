"""Entry point for the Project Quality Hub MCP server."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.models import InitializationOptions, ServerCapabilities
from mcp.server.stdio import stdio_server
from mcp.types import TextContent

from .context import MCPServerContext
from .tools import ToolHandlers

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


app = Server("project-quality-hub")
context = MCPServerContext()
handlers = ToolHandlers(context)


@app.list_tools()
async def handle_list_tools() -> List[Any]:
    return handlers.list_tools()


@app.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any] | None) -> List[TextContent]:
    arguments = arguments or {}
    result = await handlers.call_tool(name, arguments)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    return [TextContent(type="text", text=payload)]


async def _async_main() -> None:
    _configure_logging()
    logger.info("Starting Project Quality Hub server")
    init_options = InitializationOptions(
        server_name="project-quality-hub",
        server_version="0.1.0",
        capabilities=ServerCapabilities(),
    )
    async with stdio_server() as (read_stream, write_stream):
        try:
            await app.run(read_stream, write_stream, init_options)
        finally:
            context.shutdown()
    logger.info("Project Quality Hub server stopped")


def run() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    run()
