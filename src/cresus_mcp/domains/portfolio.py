"""Portfolio domain for MCP."""

import json
from typing import List, Dict, Any
import httpx
from mcp.types import Tool, Resource, TextContent
from loguru import logger

from ..base import BaseDomain


class PortfolioDomain(BaseDomain):
    """Portfolio management domain."""

    TOOLS_SCHEMA = [
        {
            "name": "list_portfolios",
            "description": "List all available portfolios with summary",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "get_portfolio",
            "description": "Get detailed portfolio information including positions and cash",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Portfolio name",
                    },
                },
                "required": ["name"],
            },
        },
        {
            "name": "create_portfolio",
            "description": "Create a new portfolio",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Portfolio name",
                    },
                    "portfolio_type": {
                        "type": "string",
                        "enum": ["paper", "live"],
                        "description": "Paper (simulation) or live trading",
                        "default": "paper",
                    },
                    "initial_capital": {
                        "type": "number",
                        "description": "Initial capital amount",
                        "default": 100000.0,
                    },
                    "currency": {
                        "type": "string",
                        "description": "Portfolio currency",
                        "default": "EUR",
                    },
                    "description": {
                        "type": "string",
                        "description": "Portfolio description",
                    },
                },
                "required": ["name"],
            },
        },
        {
            "name": "update_portfolio",
            "description": "Update portfolio configuration",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Portfolio name",
                    },
                    "portfolio_type": {
                        "type": "string",
                        "enum": ["paper", "live"],
                    },
                    "currency": {
                        "type": "string",
                    },
                    "description": {
                        "type": "string",
                    },
                    "initial_capital": {
                        "type": "number",
                    },
                },
                "required": ["name"],
            },
        },
        {
            "name": "delete_portfolio",
            "description": "Delete a portfolio",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Portfolio name",
                    },
                },
                "required": ["name"],
            },
        },
        {
            "name": "get_portfolio_positions",
            "description": "Get current positions in a portfolio",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "portfolio_name": {
                        "type": "string",
                        "description": "Portfolio name",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max positions to return",
                        "default": 100,
                    },
                },
                "required": ["portfolio_name"],
            },
        },
        {
            "name": "get_portfolio_metrics",
            "description": "Get portfolio performance metrics (Sharpe ratio, max drawdown, Sortino, etc.)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "portfolio_name": {
                        "type": "string",
                        "description": "Portfolio name",
                    },
                },
                "required": ["portfolio_name"],
            },
        },
        {
            "name": "get_portfolio_performance",
            "description": "Get portfolio performance data (returns, drawdown, etc.)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "portfolio_name": {
                        "type": "string",
                        "description": "Portfolio name",
                    },
                },
                "required": ["portfolio_name"],
            },
        },
        {
            "name": "get_portfolio_transactions",
            "description": "Get portfolio transaction history",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "portfolio_name": {
                        "type": "string",
                        "description": "Portfolio name",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max transactions to return",
                        "default": 50,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset for pagination",
                        "default": 0,
                    },
                },
                "required": ["portfolio_name"],
            },
        },
        {
            "name": "get_portfolio_value",
            "description": "Get current portfolio total value and cash",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "portfolio_name": {
                        "type": "string",
                        "description": "Portfolio name",
                    },
                },
                "required": ["portfolio_name"],
            },
        },
        {
            "name": "get_portfolio_allocation",
            "description": "Get portfolio asset allocation by ticker",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "portfolio_name": {
                        "type": "string",
                        "description": "Portfolio name",
                    },
                },
                "required": ["portfolio_name"],
            },
        },
        {
            "name": "get_portfolio_risk",
            "description": "Get portfolio risk metrics (beta, volatility, VaR)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "portfolio_name": {
                        "type": "string",
                        "description": "Portfolio name",
                    },
                },
                "required": ["portfolio_name"],
            },
        },
        {
            "name": "add_position",
            "description": "Add a position to portfolio (manual entry)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "portfolio_name": {
                        "type": "string",
                        "description": "Portfolio name",
                    },
                    "ticker": {
                        "type": "string",
                        "description": "Ticker symbol",
                    },
                    "quantity": {
                        "type": "number",
                        "description": "Number of shares",
                    },
                    "entry_price": {
                        "type": "number",
                        "description": "Entry price per share",
                    },
                },
                "required": ["portfolio_name", "ticker", "quantity", "entry_price"],
            },
        },
        {
            "name": "close_position",
            "description": "Close a position in portfolio",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "portfolio_name": {
                        "type": "string",
                        "description": "Portfolio name",
                    },
                    "ticker": {
                        "type": "string",
                        "description": "Ticker symbol",
                    },
                    "exit_price": {
                        "type": "number",
                        "description": "Exit price per share",
                    },
                },
                "required": ["portfolio_name", "ticker"],
            },
        },
        {
            "name": "compare_portfolios",
            "description": "Compare performance of multiple portfolios",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "portfolio_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of portfolio names to compare",
                    },
                },
                "required": ["portfolio_names"],
            },
        },
        {
            "name": "rebalance_portfolio",
            "description": "Rebalance portfolio to target allocation",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "portfolio_name": {
                        "type": "string",
                        "description": "Portfolio name",
                    },
                    "target_allocation": {
                        "type": "object",
                        "description": "Target allocation as {ticker: percentage}",
                    },
                },
                "required": ["portfolio_name", "target_allocation"],
            },
        },
    ]

    async def get_resources(self) -> List[Resource]:
        """Return portfolio documentation resource."""
        docs = {
            "domain": "Portfolio Management",
            "description": "Manage and analyze investment portfolios",
            "endpoints": [
                {
                    "path": "/portfolios",
                    "method": "GET",
                    "tool": "list_portfolios",
                    "description": "List all portfolios",
                },
                {
                    "path": "/portfolios/{name}",
                    "method": "GET",
                    "tool": "get_portfolio",
                    "description": "Get portfolio details",
                },
                {
                    "path": "/portfolios",
                    "method": "POST",
                    "tool": "create_portfolio",
                    "description": "Create new portfolio",
                },
                {
                    "path": "/portfolios/{name}",
                    "method": "PUT",
                    "tool": "update_portfolio",
                    "description": "Update portfolio",
                },
                {
                    "path": "/portfolios/{name}",
                    "method": "DELETE",
                    "tool": "delete_portfolio",
                    "description": "Delete portfolio",
                },
                {
                    "path": "/portfolios/{name}/positions",
                    "method": "GET",
                    "tool": "get_portfolio_positions",
                    "description": "Get current positions",
                },
                {
                    "path": "/portfolios/{name}/metrics",
                    "method": "GET",
                    "tool": "get_portfolio_metrics",
                    "description": "Get performance metrics",
                },
                {
                    "path": "/portfolios/{name}/performance",
                    "method": "GET",
                    "tool": "get_portfolio_performance",
                    "description": "Get performance history",
                },
                {
                    "path": "/portfolios/{name}/transactions",
                    "method": "GET",
                    "tool": "get_portfolio_transactions",
                    "description": "Get transaction history",
                },
            ],
        }

        resource = Resource(
            uri="portfolio://docs",
            name="Portfolio Management API",
            description="Complete portfolio management documentation",
            mimeType="application/json",
            contents=[TextContent(type="text", text=json.dumps(docs, indent=2))],
        )
        return [resource]

    async def get_tools(self) -> List[Tool]:
        """Return portfolio tools."""
        return [
            Tool(
                name=tool["name"],
                description=tool["description"],
                inputSchema=tool["inputSchema"],
            )
            for tool in self.TOOLS_SCHEMA
        ]

    async def call_tool(self, name: str, arguments: dict) -> Dict[str, Any]:
        """Execute a portfolio tool."""
        try:
            if name == "list_portfolios":
                return await self._list_portfolios()
            elif name == "get_portfolio":
                return await self._get_portfolio(arguments["name"])
            elif name == "create_portfolio":
                return await self._create_portfolio(arguments)
            elif name == "update_portfolio":
                return await self._update_portfolio(arguments)
            elif name == "delete_portfolio":
                return await self._delete_portfolio(arguments["name"])
            elif name == "get_portfolio_positions":
                return await self._get_portfolio_positions(
                    arguments["portfolio_name"],
                    arguments.get("limit", 100),
                )
            elif name == "get_portfolio_metrics":
                return await self._get_portfolio_metrics(arguments["portfolio_name"])
            elif name == "get_portfolio_performance":
                return await self._get_portfolio_performance(arguments["portfolio_name"])
            elif name == "get_portfolio_transactions":
                return await self._get_portfolio_transactions(
                    arguments["portfolio_name"],
                    arguments.get("limit", 50),
                    arguments.get("offset", 0),
                )
            elif name == "get_portfolio_value":
                return await self._get_portfolio_value(arguments["portfolio_name"])
            elif name == "get_portfolio_allocation":
                return await self._get_portfolio_allocation(arguments["portfolio_name"])
            elif name == "get_portfolio_risk":
                return await self._get_portfolio_risk(arguments["portfolio_name"])
            elif name == "add_position":
                return await self._add_position(arguments)
            elif name == "close_position":
                return await self._close_position(arguments)
            elif name == "compare_portfolios":
                return await self._compare_portfolios(arguments["portfolio_names"])
            elif name == "rebalance_portfolio":
                return await self._rebalance_portfolio(arguments)
            else:
                return {"error": f"Unknown tool: {name}"}
        except Exception as e:
            logger.error(f"Error calling portfolio tool {name}: {e}")
            return {"error": str(e)}

    # Tool implementations
    async def _list_portfolios(self) -> Dict[str, Any]:
        """List all portfolios."""
        try:
            response = await self.client.get("/portfolios")
            return response.json()
        except Exception as e:
            return {"error": str(e), "portfolios": []}

    async def _get_portfolio(self, name: str) -> Dict[str, Any]:
        """Get portfolio details."""
        try:
            response = await self.client.get(f"/portfolios/{name}")
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def _create_portfolio(self, args: dict) -> Dict[str, Any]:
        """Create a new portfolio."""
        try:
            payload = {
                "name": args["name"],
                "portfolio_type": args.get("portfolio_type", "paper"),
                "initial_capital": args.get("initial_capital", 100000.0),
                "currency": args.get("currency", "EUR"),
                "description": args.get("description", ""),
            }
            response = await self.client.post("/portfolios", json=payload)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def _update_portfolio(self, args: dict) -> Dict[str, Any]:
        """Update portfolio."""
        try:
            name = args.pop("name")
            response = await self.client.put(f"/portfolios/{name}", json=args)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def _delete_portfolio(self, name: str) -> Dict[str, Any]:
        """Delete portfolio."""
        try:
            response = await self.client.delete(f"/portfolios/{name}")
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def _get_portfolio_positions(
        self, name: str, limit: int = 100
    ) -> Dict[str, Any]:
        """Get portfolio positions."""
        try:
            response = await self.client.get(
                f"/portfolios/{name}/positions", params={"limit": limit}
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def _get_portfolio_metrics(self, name: str) -> Dict[str, Any]:
        """Get portfolio metrics."""
        try:
            response = await self.client.get(f"/portfolios/{name}/metrics")
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def _get_portfolio_performance(self, name: str) -> Dict[str, Any]:
        """Get portfolio performance."""
        try:
            response = await self.client.get(f"/portfolios/{name}/performance")
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def _get_portfolio_transactions(
        self, name: str, limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        """Get portfolio transactions."""
        try:
            response = await self.client.get(
                f"/portfolios/{name}/transactions",
                params={"limit": limit, "offset": offset},
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def _get_portfolio_value(self, name: str) -> Dict[str, Any]:
        """Get portfolio value."""
        try:
            response = await self.client.get(f"/portfolios/{name}/value")
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def _get_portfolio_allocation(self, name: str) -> Dict[str, Any]:
        """Get portfolio allocation."""
        try:
            response = await self.client.get(f"/portfolios/{name}/allocation")
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def _get_portfolio_risk(self, name: str) -> Dict[str, Any]:
        """Get portfolio risk metrics."""
        try:
            response = await self.client.get(f"/portfolios/{name}/risk")
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def _add_position(self, args: dict) -> Dict[str, Any]:
        """Add position to portfolio."""
        try:
            portfolio_name = args.pop("portfolio_name")
            response = await self.client.post(
                f"/portfolios/{portfolio_name}/positions", json=args
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def _close_position(self, args: dict) -> Dict[str, Any]:
        """Close position in portfolio."""
        try:
            portfolio_name = args.pop("portfolio_name")
            ticker = args.pop("ticker")
            response = await self.client.delete(
                f"/portfolios/{portfolio_name}/positions/{ticker}", json=args
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def _compare_portfolios(self, names: List[str]) -> Dict[str, Any]:
        """Compare portfolios."""
        try:
            response = await self.client.post(
                "/portfolios/compare", json={"portfolio_names": names}
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def _rebalance_portfolio(self, args: dict) -> Dict[str, Any]:
        """Rebalance portfolio."""
        try:
            portfolio_name = args.pop("portfolio_name")
            response = await self.client.post(
                f"/portfolios/{portfolio_name}/rebalance", json=args
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
