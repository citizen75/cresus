"""MCP portfolio tools."""

from functools import lru_cache
from portfolio.metrics import PortfolioMetrics


@lru_cache(maxsize=1)
def _get_metrics() -> PortfolioMetrics:
    return PortfolioMetrics()


def portfolio_list():
    """List all portfolios."""
    pm = _get_metrics()
    return {"portfolios": pm.list_portfolios()}


def portfolio_details(name: str):
    """Get portfolio details."""
    pm = _get_metrics()
    result = pm.get_portfolio_details(name)
    return result or {"error": f"Portfolio '{name}' not found"}


def portfolio_value(name: str, use_cache: bool = True):
    """Get portfolio value."""
    pm = _get_metrics()
    return pm.calculate_portfolio_value(name, use_cache)


def portfolio_performance(name: str):
    """Get performance metrics."""
    pm = _get_metrics()
    result = pm.get_portfolio_performance(name)
    return result or {"error": f"Portfolio '{name}' not found"}


def portfolio_metrics(name: str):
    """Get comprehensive metrics."""
    pm = _get_metrics()
    result = pm.get_daily_metrics(name)
    return result or {"error": f"Portfolio '{name}' not found"}


def portfolio_history(name: str):
    """Get portfolio history."""
    pm = _get_metrics()
    return pm.calculate_portfolio_history(name)


def portfolio_positions(name: str):
    """Get open positions."""
    pm = _get_metrics()
    result = pm.get_portfolio_positions(name)
    return result or {"error": f"Portfolio '{name}' not found"}
