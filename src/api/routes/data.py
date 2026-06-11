"""Data management API routes."""

from fastapi import APIRouter, Query
from tools.data.manager import DataManager

router = APIRouter(prefix="/api/v1/data", tags=["data"])
manager = DataManager()


@router.get("/categories")
async def get_categories():
    """Get available asset categories."""
    return {"categories": manager.get_asset_categories()}


@router.get("/universes")
async def get_universes(category: str = Query(..., description="Asset category")):
    """Get universes for a category."""
    universes = manager.get_universes(category)
    return {"category": category, "universes": universes}


@router.get("/tickers")
async def get_tickers(
    category: str = Query(..., description="Asset category"),
    universe: str = Query(..., description="Universe ID"),
    limit: int = Query(1000, description="Max number of tickers"),
):
    """Get tickers for a category and universe."""
    tickers = manager.get_tickers(category, universe, limit)
    return {"category": category, "universe": universe, "tickers": tickers, "count": len(tickers)}


@router.get("/search")
async def search_tickers(
    q: str = Query(..., description="Search query"),
    category: str = Query(None, description="Optional category filter"),
):
    """Search for tickers."""
    results = manager.search_tickers(q, category)
    return {"query": q, "category": category, "results": results, "count": len(results)}


@router.get("/tickers/{ticker}")
async def get_ticker_info(ticker: str):
    """Get detailed information about a ticker."""
    info = manager.get_ticker_info(ticker)
    if not info:
        return {"error": "Ticker not found"}, 404
    return {"ticker": ticker, "info": info}
