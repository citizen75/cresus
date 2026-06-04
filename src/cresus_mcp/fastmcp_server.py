"""Cresus MCP Server using FastMCP - HTTP/SSE enabled."""

import os
import json
from pathlib import Path
from typing import Any, Optional

from fastmcp import FastMCP
from loguru import logger
import httpx

# Initialize FastMCP server
mcp = FastMCP("cresus-mcp")

# Global API client
api_client: Optional[httpx.AsyncClient] = None
api_base_url: str = os.getenv("CRESUS_API_URL", "http://192.168.0.130:6501/api/v1")


async def get_client() -> httpx.AsyncClient:
    """Get or create async HTTP client."""
    global api_client
    if api_client is None:
        api_client = httpx.AsyncClient(
            base_url=api_base_url,
            timeout=30.0,
        )
        logger.info(f"Connected to Cresus API at {api_base_url}")
    return api_client


# Portfolio Query Tools

@mcp.tool()
async def list_portfolios() -> str:
    """List all available portfolios with summary information."""
    client = await get_client()
    response = await client.get("/portfolios")
    data = response.json()
    portfolios = data.get("portfolios", [])
    return json.dumps({
        "count": len(portfolios),
        "portfolios": [
            {
                "name": p.get("name"),
                "type": p.get("type"),
                "value": p.get("total_portfolio_value"),
                "positions": p.get("num_positions"),
            }
            for p in portfolios
        ]
    }, indent=2)


@mcp.tool()
async def get_portfolio(name: str) -> str:
    """Get detailed portfolio information including positions, metrics, and performance."""
    client = await get_client()
    response = await client.get(f"/portfolios/{name}")
    data = response.json()
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
async def get_portfolio_positions(portfolio_name: str) -> str:
    """Get current positions in a portfolio with quantities, prices, and values."""
    client = await get_client()
    response = await client.get(f"/portfolios/{portfolio_name}")
    data = response.json()
    positions = data.get("positions", [])
    return json.dumps({
        "portfolio": portfolio_name,
        "count": len(positions),
        "positions": [
            {
                "ticker": p.get("ticker"),
                "quantity": p.get("quantity"),
                "entry_price": p.get("entry_price"),
                "current_price": p.get("current_price"),
                "position_value": p.get("position_value"),
                "pnl": p.get("pnl"),
                "pnl_pct": p.get("pnl_pct"),
            }
            for p in positions
        ]
    }, indent=2, default=str)


@mcp.tool()
async def get_portfolio_metrics(portfolio_name: str) -> str:
    """Get portfolio performance metrics (Sharpe ratio, max drawdown, win rate, etc)."""
    client = await get_client()
    response = await client.get(f"/portfolios/{portfolio_name}/metrics")
    data = response.json()
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
async def get_portfolio_performance(portfolio_name: str) -> str:
    """Get portfolio performance data (returns, drawdown, etc over time)."""
    client = await get_client()
    response = await client.get(f"/portfolios/{portfolio_name}/performance")
    data = response.json()
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
async def get_portfolio_allocation(portfolio_name: str) -> str:
    """Get portfolio asset allocation by ticker and sector."""
    client = await get_client()
    response = await client.get(f"/portfolios/{portfolio_name}/allocation")
    data = response.json()
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
async def get_portfolio_value(portfolio_name: str) -> str:
    """Get current portfolio total value and cash balance."""
    client = await get_client()
    response = await client.get(f"/portfolios/{portfolio_name}/value")
    data = response.json()
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
async def get_portfolio_risk(portfolio_name: str) -> str:
    """Get portfolio risk metrics (beta, volatility, Value at Risk, etc)."""
    client = await get_client()
    response = await client.get(f"/portfolios/{portfolio_name}/risk")
    data = response.json()
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
async def get_portfolio_transactions(portfolio_name: str) -> str:
    """Get portfolio transaction history and trade log."""
    client = await get_client()
    response = await client.get(f"/portfolios/{portfolio_name}/transactions")
    data = response.json()
    return json.dumps(data, indent=2, default=str)


# Portfolio Management Tools

@mcp.tool()
async def create_portfolio(name: str, portfolio_type: str = "paper", currency: str = "EUR") -> str:
    """Create a new portfolio."""
    client = await get_client()
    response = await client.post("/portfolios", json={
        "name": name,
        "type": portfolio_type,
        "currency": currency,
    })
    data = response.json()
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
async def update_portfolio(name: str, config: dict) -> str:
    """Update portfolio configuration."""
    client = await get_client()
    response = await client.put(f"/portfolios/{name}", json=config)
    data = response.json()
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
async def delete_portfolio(name: str) -> str:
    """Delete a portfolio."""
    client = await get_client()
    response = await client.delete(f"/portfolios/{name}")
    return json.dumps({"status": "deleted", "portfolio": name}, indent=2)


@mcp.tool()
async def add_position(portfolio_name: str, ticker: str, quantity: float, entry_price: float) -> str:
    """Add a position to portfolio (manual entry)."""
    client = await get_client()
    response = await client.post(f"/portfolios/{portfolio_name}/positions", json={
        "ticker": ticker,
        "quantity": quantity,
        "entry_price": entry_price,
    })
    data = response.json()
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
async def close_position(portfolio_name: str, position_id: str) -> str:
    """Close a position in portfolio."""
    client = await get_client()
    response = await client.post(f"/portfolios/{portfolio_name}/positions/{position_id}/close")
    data = response.json()
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
async def compare_portfolios(portfolio_names: list) -> str:
    """Compare performance of multiple portfolios."""
    client = await get_client()
    response = await client.post("/portfolios/compare", json={"names": portfolio_names})
    data = response.json()
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
async def rebalance_portfolio(portfolio_name: str, target_allocation: dict) -> str:
    """Rebalance portfolio to target allocation."""
    client = await get_client()
    response = await client.post(f"/portfolios/{portfolio_name}/rebalance", json={
        "target_allocation": target_allocation
    })
    data = response.json()
    return json.dumps(data, indent=2, default=str)
