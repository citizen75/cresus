"""MCP server using FastMCP with proper HTTP/SSE support."""

from mcp.server import FastMCP
from mcp.types import Tool, TextContent
import json
from loguru import logger

# Create FastMCP instance with HTTP/SSE support
mcp = FastMCP(
    name="cresus",
    instructions="Portfolio and watchlist management tools",
)


@mcp.tool()
def portfolio_list(portfolio_type: str = "all") -> str:
    """List all portfolios.

    Args:
        portfolio_type: Type of portfolios to list (real, paper, or all)
    """
    try:
        from tools.portfolio.manager import PortfolioManager

        pm = PortfolioManager()
        portfolios = pm.list_portfolios()

        if portfolio_type == "real":
            portfolios = [p for p in portfolios if p not in ["PEA", "PEP"]]
        elif portfolio_type == "paper":
            portfolios = [p for p in portfolios if p in ["PEA", "PEP"]]

        return json.dumps({
            "portfolios": portfolios,
            "count": len(portfolios),
            "type": portfolio_type,
        })
    except Exception as e:
        logger.error(f"Error listing portfolios: {e}")
        return json.dumps({"error": str(e)})


@mcp.tool()
def portfolio_holdings(portfolio_name: str) -> str:
    """Get holdings for a specific portfolio.

    Args:
        portfolio_name: Name of the portfolio
    """
    try:
        from tools.portfolio.manager import PortfolioManager

        pm = PortfolioManager()
        holdings = pm.get_holdings(portfolio_name)

        return json.dumps({
            "portfolio": portfolio_name,
            "holdings": holdings,
        }, default=str)
    except Exception as e:
        logger.error(f"Error getting portfolio holdings: {e}")
        return json.dumps({"error": str(e)})


@mcp.tool()
def watchlist_rank(watchlist_name: str) -> str:
    """Get ranking scores for a watchlist.

    Args:
        watchlist_name: Name of the watchlist
    """
    try:
        # TODO: Implement watchlist ranking via API
        return json.dumps({
            "watchlist": watchlist_name,
            "rankings": [],
            "note": "Watchlist ranking not yet implemented",
        })
    except Exception as e:
        logger.error(f"Error getting watchlist rankings: {e}")
        return json.dumps({"error": str(e)})


@mcp.tool()
def screener_run(screener_name: str, portfolio: str = None) -> str:
    """Run a screener.

    Args:
        screener_name: Name of the screener to run
        portfolio: Optional portfolio filter
    """
    try:
        # TODO: Implement screener execution via API
        return json.dumps({
            "screener": screener_name,
            "portfolio": portfolio or "all",
            "results": [],
            "note": "Screener execution not yet implemented",
        })
    except Exception as e:
        logger.error(f"Error running screener: {e}")
        return json.dumps({"error": str(e)})
