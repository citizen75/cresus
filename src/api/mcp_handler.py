"""MCP server for HTTP/SSE transport integrated with FastAPI gateway."""

import json
import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent, CallToolResult
from loguru import logger


def create_mcp_server_for_gateway() -> Server:
    """Create MCP server with Cresus tools for HTTP/SSE transport.

    Returns a server that can be used with FastAPI HTTP/SSE endpoints.
    """
    server = Server("cresus-portfolio-api")

    # Define tools
    portfolio_list_tool = Tool(
        name="portfolio_list",
        description="List all portfolios (real, paper, or all)",
        inputSchema={
            "type": "object",
            "properties": {
                "portfolio_type": {
                    "type": "string",
                    "enum": ["real", "paper", "all"],
                    "description": "Type of portfolios to list (default: all)",
                }
            },
        },
    )

    portfolio_holdings_tool = Tool(
        name="portfolio_holdings",
        description="Get holdings for a specific portfolio",
        inputSchema={
            "type": "object",
            "properties": {
                "portfolio_name": {
                    "type": "string",
                    "description": "Name of the portfolio",
                }
            },
            "required": ["portfolio_name"],
        },
    )

    watchlist_rank_tool = Tool(
        name="watchlist_rank",
        description="Get ranking scores for a watchlist",
        inputSchema={
            "type": "object",
            "properties": {
                "watchlist_name": {
                    "type": "string",
                    "description": "Name of the watchlist",
                }
            },
            "required": ["watchlist_name"],
        },
    )

    screener_run_tool = Tool(
        name="screener_run",
        description="Run a screener with optional portfolio filter",
        inputSchema={
            "type": "object",
            "properties": {
                "screener_name": {
                    "type": "string",
                    "description": "Name of the screener to run",
                },
                "portfolio": {
                    "type": "string",
                    "description": "Portfolio filter (optional)",
                },
            },
            "required": ["screener_name"],
        },
    )

    # Register list_tools handler
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List all available tools."""
        return [
            portfolio_list_tool,
            portfolio_holdings_tool,
            watchlist_rank_tool,
            screener_run_tool,
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> CallToolResult:
        """Handle tool calls from Hermes via MCP protocol."""
        try:
            if name == "portfolio_list":
                return await handle_portfolio_list(arguments)
            elif name == "portfolio_holdings":
                return handle_portfolio_holdings(arguments)
            elif name == "watchlist_rank":
                return handle_watchlist_rank(arguments)
            elif name == "screener_run":
                return handle_screener_run(arguments)
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                    isError=True,
                )
        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}", exc_info=True)
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {str(e)}")],
                isError=True,
            )

    return server


async def handle_portfolio_list(arguments: dict) -> CallToolResult:
    """List portfolios."""
    try:
        from tools.portfolio.manager import PortfolioManager

        portfolio_type = arguments.get("portfolio_type", "all").lower()
        pm = PortfolioManager()
        portfolios = pm.list_portfolios()

        if portfolio_type == "real":
            portfolios = [p for p in portfolios if p not in ["PEA", "PEP"]]
        elif portfolio_type == "paper":
            portfolios = [p for p in portfolios if p in ["PEA", "PEP"]]

        result = {"portfolios": portfolios, "count": len(portfolios), "type": portfolio_type}
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result))],
            isError=False,
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=str(e))],
            isError=True,
        )


def handle_portfolio_holdings(arguments: dict) -> CallToolResult:
    """Get portfolio holdings."""
    try:
        from tools.portfolio.manager import PortfolioManager

        portfolio_name = arguments.get("portfolio_name")
        if not portfolio_name:
            raise ValueError("portfolio_name is required")

        pm = PortfolioManager()
        holdings = pm.get_holdings(portfolio_name)

        result = {"portfolio": portfolio_name, "holdings": holdings}
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, default=str))],
            isError=False,
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=str(e))],
            isError=True,
        )


def handle_watchlist_rank(arguments: dict) -> CallToolResult:
    """Get watchlist rankings."""
    try:
        watchlist_name = arguments.get("watchlist_name")
        if not watchlist_name:
            raise ValueError("watchlist_name is required")

        # TODO: Implement via API call
        result = {
            "watchlist": watchlist_name,
            "rankings": [],
            "note": "Watchlist ranking not yet implemented",
        }
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result))],
            isError=False,
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=str(e))],
            isError=True,
        )


def handle_screener_run(arguments: dict) -> CallToolResult:
    """Run a screener."""
    try:
        screener_name = arguments.get("screener_name")
        portfolio = arguments.get("portfolio")

        if not screener_name:
            raise ValueError("screener_name is required")

        # TODO: Implement via API call
        result = {
            "screener": screener_name,
            "portfolio": portfolio or "all",
            "results": [],
            "note": "Screener execution not yet implemented",
        }
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result))],
            isError=False,
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=str(e))],
            isError=True,
        )
