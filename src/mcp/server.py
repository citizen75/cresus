"""MCP server for portfolio tools."""

import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


class CresusMCPServer:
    """MCP server exposing portfolio tools."""

    TOOLS = {
        "portfolio_list": {
            "description": "List all portfolios with summary",
            "inputSchema": {"type": "object", "properties": {}, "required": []},
        },
        "portfolio_details": {
            "description": "Get portfolio details with positions",
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
        "portfolio_value": {
            "description": "Get current portfolio value",
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
        "portfolio_performance": {
            "description": "Get performance metrics",
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
        "portfolio_metrics": {
            "description": "Get comprehensive metrics (Sharpe, Sortino, etc.)",
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
        "portfolio_history": {
            "description": "Get portfolio value history",
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
        "portfolio_positions": {
            "description": "Get open positions",
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    }

    def __init__(self):
        self.server = Server("cresus-portfolio")
        self._register_handlers()

    def _register_handlers(self):
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name=name,
                    description=info["description"],
                    inputSchema=info["inputSchema"],
                )
                for name, info in self.TOOLS.items()
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            from mcp.tools import portfolio as pt

            fn = getattr(pt, name, None)
            if fn is None:
                result = {"error": f"Unknown tool: {name}"}
            else:
                try:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: fn(**arguments)
                    )
                except Exception as e:
                    result = {"error": str(e)}

            return [TextContent(type="text", text=json.dumps(result, default=str))]

    async def run_async(self):
        """Run MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream)

    def run(self):
        """Run MCP server (blocking)."""
        asyncio.run(self.run_async())
