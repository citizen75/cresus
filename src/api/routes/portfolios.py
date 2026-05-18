"""Portfolio API endpoints."""

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from functools import lru_cache
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd

from tools.portfolio.manager import PortfolioManager
from tools.portfolio.metrics import PortfolioMetrics
from tools.watchlist.watchlist_manager import WatchlistManager


class CreatePortfolioRequest(BaseModel):
    name: str
    portfolio_type: str = "paper"
    initial_capital: Optional[float] = 100000.0
    currency: str = "EUR"
    description: str = ""


class UpdatePortfolioRequest(BaseModel):
    portfolio_type: Optional[str] = None
    currency: Optional[str] = None
    description: Optional[str] = None
    initial_capital: Optional[float] = None
    strategy: Optional[str] = None


@lru_cache(maxsize=1)
def _get_portfolio_manager() -> PortfolioManager:
    return PortfolioManager()


@lru_cache(maxsize=1)
def _get_metrics() -> PortfolioMetrics:
    return PortfolioMetrics()


router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.get("")
async def list_portfolios():
    """List all portfolios by scanning folder structure."""
    pm = _get_portfolio_manager()
    portfolios = pm.list_portfolios()

    return {
        "status": "success",
        "portfolios": portfolios,
        "total": len(portfolios),
    }


@router.get("/cache/all")
async def get_portfolio_cache():
    """Get all portfolios from cache."""
    pm = _get_portfolio_manager()
    cached = pm.cache.get_all_portfolios()
    return {
        "cached_portfolios": cached,
        "count": len(cached),
    }


@router.post("")
async def create_portfolio(req: CreatePortfolioRequest):
    """Create new portfolio with default strategy."""
    pm = _get_portfolio_manager()
    result = pm.create_portfolio(
        name=req.name,
        portfolio_type=req.portfolio_type,
        currency=req.currency,
        description=req.description,
        initial_capital=req.initial_capital,
    )
    if result.get("status") == "error":
        raise HTTPException(400, result.get("message", "Failed to create portfolio"))
    return result


@router.put("/{name}")
async def update_portfolio(name: str, req: UpdatePortfolioRequest):
    """Update portfolio configuration."""
    pm = _get_portfolio_manager()

    # Prepare update data (only include provided fields)
    update_data = {}
    if req.portfolio_type is not None:
        update_data["portfolio_type"] = req.portfolio_type
    if req.currency is not None:
        update_data["currency"] = req.currency
    if req.description is not None:
        update_data["description"] = req.description
    if req.initial_capital is not None:
        update_data["initial_capital"] = req.initial_capital

    result = pm.update_portfolio(name, update_data)
    if result.get("status") == "error":
        raise HTTPException(400, result.get("message", "Failed to update portfolio"))
    return result


@router.delete("/{name}")
async def delete_portfolio(name: str):
    """Delete a portfolio."""
    pm = _get_portfolio_manager()
    result = pm.delete_portfolio(name)
    if result.get("status") == "error":
        raise HTTPException(404, result.get("message", "Failed to delete portfolio"))
    return result


@router.get("/{name}/orders")
async def get_portfolio_orders(name: str):
    """Get orders for a portfolio (pending, executed, rejected)."""
    pm = _get_portfolio_manager()
    return pm.get_portfolio_orders(name)


@router.get("/{name}/metadata")
async def get_portfolio_metadata(name: str):
    """Get portfolio metadata only (no expensive price lookups)."""
    pm = _get_portfolio_manager()
    result = pm.get_portfolio_metadata(name)
    if not result:
        raise HTTPException(404, f"Portfolio '{name}' not found")
    return result


@router.get("/{name}")
async def get_portfolio_details(name: str):
    """Get portfolio details."""
    pm = _get_portfolio_manager()
    result = pm.get_portfolio_details(name)
    if not result:
        raise HTTPException(404, f"Portfolio '{name}' not found")
    return result


@router.get("/{name}/positions")
async def get_portfolio_positions(name: str):
    """Get open positions (read-only)."""
    pm = _get_portfolio_manager()
    result = pm.get_portfolio_positions(name)
    if not result:
        raise HTTPException(404, f"Portfolio '{name}' not found")
    return result


@router.get("/{name}/transactions")
async def get_portfolio_transactions(name: str, ticker: Optional[str] = None):
    """Get all transactions for a portfolio, optionally filtered by ticker."""
    pm = _get_portfolio_manager()
    result = pm.get_portfolio_transactions(name, ticker)

    return {
        "name": name,
        "transactions": result.get("transactions", []),
        "total_count": len(result.get("transactions", [])),
        "ticker_filter": ticker,
    }


@router.get("/{name}/performance")
async def get_portfolio_performance(name: str):
    """Get performance metrics."""
    pm = _get_portfolio_manager()
    result = pm.get_portfolio_performance(name)
    if not result:
        raise HTTPException(404, f"Portfolio '{name}' not found")
    return result


@router.get("/{name}/metrics")
async def get_portfolio_metrics(name: str):
    """Get comprehensive metrics."""
    metrics = _get_metrics()
    result = metrics.get_daily_metrics(name)
    if not result:
        raise HTTPException(404, f"Portfolio '{name}' not found")
    return result


@router.get("/{name}/value")
async def get_portfolio_value(name: str, use_cache: bool = True):
    """Get current portfolio value."""
    pm = _get_portfolio_manager()
    result = pm.calculate_portfolio_value(name, use_cache)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.get("/{name}/history")
async def get_portfolio_history(name: str, fetch: bool = False):
    """Get portfolio value history from transactions.

    Returns daily portfolio values (positions + cash) replayed from journal.

    Args:
        fetch: If True, fetch fresh price data from yfinance. Default uses cached prices only.
    """
    pm = _get_portfolio_manager()
    # Calculate is always done (fast enough) - only fetch if explicitly requested
    result = pm.calculate_portfolio_history(name, recalculate=False, use_cache_only=not fetch)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.post("/{name}/refresh")
async def refresh_portfolio(name: str):
    """Refresh portfolio prices."""
    pm = _get_portfolio_manager()
    result = pm.refresh_portfolio_fundamentals(name)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.post("/{name}/transactions")
async def record_transaction(name: str, data: Dict[str, Any]):
    """Record a transaction.

    Operations: BUY, SELL, CASH
    For CASH: ticker should be "CASH", quantity is the amount (positive=deposit, negative=withdrawal)
    """
    pm = _get_portfolio_manager()
    result = pm.record_transaction(
        name,
        data.get("operation", ""),
        data.get("ticker", "CASH") if data.get("operation", "").upper() == "CASH" else data.get("ticker", ""),
        data.get("quantity", 0),
        data.get("price", 1.0) if data.get("operation", "").upper() == "CASH" else data.get("price", 0),
        data.get("fees", 0),
        data.get("notes", ""),
        data.get("created_at"),
    )
    return result


@router.get("/{name}/allocation")
async def get_portfolio_allocation(name: str):
    """Get portfolio allocation by position weight."""
    pm = _get_portfolio_manager()
    result = pm.get_portfolio_allocation(name)
    if not result:
        raise HTTPException(404, f"Portfolio '{name}' not found")
    return result


@router.get("/{name}/holdings")
async def get_top_holdings(name: str, limit: int = 10):
    """Get top holdings by weight."""
    pm = _get_portfolio_manager()
    result = pm.get_top_holdings(name, limit)
    if not result:
        raise HTTPException(404, f"Portfolio '{name}' not found")
    return result


@router.get("/{name}/strategy")
async def get_portfolio_strategy(name: str):
    """Get portfolio strategy configuration."""
    pm = _get_portfolio_manager()
    details = pm.get_portfolio_details(name)
    if not details:
        raise HTTPException(404, f"Portfolio '{name}' not found")
    return {
        "name": name,
        "universe": "S&P 500 Equities (~500 stocks)",
        "entry_conditions": [
            "AI Relevance Score >= 80",
            "Revenue Growth (TTM) >= 15%",
            "Gross Margin >= 40%",
        ],
        "exit_conditions": [
            "AI Relevance Score <= 40",
            "Revenue Growth (TTM) < 5%",
            "Drawdown high > 25%",
        ],
        "position_sizing": {
            "method": "Risk parity",
            "target_volatility": "15%",
            "max_position_size": "8%",
        },
        "rebalance": {
            "frequency": "Weekly",
            "drift_threshold": "5%",
        },
    }


@router.get("/{name}/watchlist")
async def get_portfolio_watchlist(name: str, limit: int = 50):
    """Get watchlist for portfolio from its associated strategy."""
    from tools.portfolio.manager import PortfolioManager
    from pathlib import Path
    from utils.env import get_db_root
    import json

    # Get portfolio metadata directly without fetching prices
    db_root = get_db_root()
    portfolio_dir = db_root / "portfolios" / name
    portfolio_json = portfolio_dir / "portfolio.json"

    if not portfolio_json.exists():
        raise HTTPException(404, f"Portfolio '{name}' not found")

    # Load portfolio metadata
    with open(portfolio_json, 'r') as f:
        metadata = json.load(f)

    # Get the strategy name (defaults to portfolio name if not set)
    strategy_name = metadata.get("strategy", name)

    # Load watchlist using WatchlistManager
    wm = WatchlistManager(strategy_name, portfolio_name=name)
    df = wm.load()

    watchlist = []
    if df is not None and len(df) > 0:
        # Convert to list of dicts, limit to requested amount
        watchlist = df.head(limit).to_dict('records')

    return {
        "name": name,
        "strategy": strategy_name,
        "watchlist": watchlist,
        "total_stocks": len(watchlist),
    }


@router.get("/{name}/current-prices")
async def get_current_prices(name: str, response: Response):
    """Get current prices for all positions using cached Fundamental data."""
    pm = _get_portfolio_manager()
    details = pm.get_portfolio_details(name)
    if not details:
        raise HTTPException(404, f"Portfolio '{name}' not found")

    # Add cache header: 5 minutes (300 seconds)
    response.headers["Cache-Control"] = "public, max-age=300"
    response.headers["Expires"] = (datetime.utcnow() + timedelta(seconds=300)).strftime("%a, %d %b %Y %H:%M:%S GMT")

    from tools.data import Fundamental

    positions_with_prices = []
    total_value = 0

    for pos in details.get("positions", []):
        ticker = pos["ticker"]
        quantity = pos["quantity"]
        avg_entry_price = pos["avg_entry_price"]

        # Get current price from cached Fundamental (don't fetch fresh)
        fundamental = Fundamental(ticker)
        current_price = fundamental.get_current_price()

        if current_price is None:
            current_price = pos["current_price"]  # Fallback to cached price

        position_value = quantity * current_price
        position_gain = (current_price - avg_entry_price) * quantity
        position_gain_pct = ((current_price - avg_entry_price) / avg_entry_price * 100) if avg_entry_price > 0 else 0

        total_value += position_value

        # Get company information from cached data
        company_info = fundamental.get_company_info()

        positions_with_prices.append({
            "ticker": ticker,
            "company_name": company_info.get("company_name"),
            "sector": company_info.get("sector"),
            "industry": company_info.get("industry"),
            "asset_type": company_info.get("asset_type"),
            "quantity": quantity,
            "avg_entry_price": round(avg_entry_price, 2),
            "current_price": round(current_price, 2),
            "position_value": round(position_value, 2),
            "position_gain": round(position_gain, 2),
            "position_gain_pct": round(position_gain_pct, 2),
            "last_updated": Fundamental(ticker).load().get("timestamp") if Fundamental(ticker).load() else None,
        })

    # Get cash balance
    cash = pm.get_portfolio_cash(name)
    total_value_with_cash = total_value + cash

    return {
        "name": name,
        "positions": positions_with_prices,
        "total_value": round(total_value, 2),
        "cash": round(cash, 2),
        "total_portfolio_value": round(total_value_with_cash, 2),
        "timestamp": datetime.now().isoformat(),
    }


@router.put("/{name}/transactions/{transaction_id}")
async def update_transaction(name: str, transaction_id: str, data: Dict[str, Any]):
    """Update a transaction."""
    pm = _get_portfolio_manager()
    result = pm.update_transaction(name, transaction_id, data)

    if result.get("status") == "error":
        raise HTTPException(400, result.get("message"))

    return {
        "status": "success",
        "message": f"Transaction {transaction_id} updated",
        "portfolio": name,
    }


@router.delete("/{name}/transactions/{transaction_id}")
async def delete_transaction(name: str, transaction_id: str):
    """Delete a transaction."""
    pm = _get_portfolio_manager()
    result = pm.delete_transaction(name, transaction_id)

    if result.get("status") == "error":
        raise HTTPException(400, result.get("message"))

    return {
        "status": "success",
        "message": f"Transaction {transaction_id} deleted",
        "portfolio": name,
    }


@router.get("/{name}/backtest")
async def get_portfolio_backtest(name: str):
    """Get portfolio backtest results."""
    pm = _get_portfolio_manager()
    details = pm.get_portfolio_details(name)
    if not details:
        raise HTTPException(404, f"Portfolio '{name}' not found")
    return {
        "name": name,
        "period": "Jan 2018 - May 2024",
        "summary": {
            "total_return_pct": 156.35,
            "cagr_pct": 19.7,
            "max_drawdown_pct": -18.6,
            "sharpe_ratio": 1.58,
            "win_rate_pct": 64.8,
            "avg_holding_months": 6.5,
        },
        "benchmark": {
            "total_return_pct": 88.2,
            "cagr_pct": 10.2,
            "max_drawdown_pct": -24.7,
            "sharpe_ratio": 0.84,
        },
        "annual_returns": [
            {"year": 2018, "portfolio": -8.2, "benchmark": -4.4},
            {"year": 2019, "portfolio": 31.2, "benchmark": 31.5},
            {"year": 2020, "portfolio": 38.7, "benchmark": 16.8},
            {"year": 2021, "portfolio": 24.1, "benchmark": 28.7},
            {"year": 2022, "portfolio": -12.6, "benchmark": -18.1},
            {"year": 2023, "portfolio": 35.4, "benchmark": 25.2},
            {"year": 2024, "portfolio": 12.8, "benchmark": 9.7},
        ],
    }
