"""Data management API routes."""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional
from tools.data.financial import FinancialDataManager
from tools.universe.universe import Universe

# Request/Response models
class UniverseCreateRequest(BaseModel):
    """Request to create a new universe."""
    tickers: List[str]
    columns: Optional[List[str]] = ["TickerYahoo"]

class TickersRequest(BaseModel):
    """Request to add/remove tickers."""
    tickers: List[str]

router = APIRouter(prefix="/data", tags=["data"])
manager = FinancialDataManager()


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


@router.get("/universes/list")
async def list_all_universes():
    """List all available universes."""
    try:
        universes = Universe.list_universes()
        details = []
        for uni_id in universes:
            try:
                uni = Universe(uni_id)
                if uni.exists():
                    tickers = uni.get_tickers()
                    details.append({
                        "id": uni_id,
                        "name": manager._format_universe_name(uni_id),
                        "count": len(tickers),
                    })
            except Exception:
                pass
        return {"universes": details, "total": len(details)}
    except Exception as e:
        return {"error": str(e)}, 500


@router.get("/universe/{universe_id}")
async def get_universe_tickers(universe_id: str, limit: int = Query(1000, description="Max number of tickers")):
    """Get tickers for a specific universe."""
    try:
        universe = Universe(universe_id)
        if not universe.exists():
            return {"error": f"Universe '{universe_id}' not found"}, 404

        ticker_symbols = universe.get_tickers()[:limit]
        tickers = [{"symbol": symbol, "name": symbol} for symbol in ticker_symbols]

        return {
            "universe": universe_id,
            "tickers": tickers,
            "count": len(tickers),
        }
    except Exception as e:
        return {"error": str(e)}, 500


@router.get("/universe/{universe_id}/info")
async def get_universe_info(universe_id: str):
    """Get information about a specific universe."""
    try:
        info = Universe.get_universe_info(universe_id)
        if not info:
            return {"error": f"Universe '{universe_id}' not found"}, 404
        return {"universe": universe_id, "info": info}
    except Exception as e:
        return {"error": str(e)}, 500


@router.post("/universe")
async def create_universe(request: UniverseCreateRequest):
    """Create a new universe with given tickers."""
    try:
        # TODO: Add universe_name to request
        return {"error": "universe_name required"}, 400
    except Exception as e:
        return {"error": str(e)}, 500


@router.post("/universe/{universe_id}")
async def create_universe_with_id(universe_id: str, request: UniverseCreateRequest):
    """Create a new universe with given ID and tickers."""
    try:
        universe = Universe(universe_id)
        if universe.exists():
            return {"error": f"Universe '{universe_id}' already exists"}, 409

        universe.create(request.tickers, request.columns)
        return {
            "status": "created",
            "universe": universe_id,
            "count": len(request.tickers),
        }
    except Exception as e:
        return {"error": str(e)}, 400


@router.put("/universe/{universe_id}")
async def update_universe(universe_id: str, request: UniverseCreateRequest):
    """Replace all tickers in a universe."""
    try:
        universe = Universe(universe_id)
        if not universe.exists():
            return {"error": f"Universe '{universe_id}' not found"}, 404

        universe.delete()
        universe.create(request.tickers, request.columns)
        return {
            "status": "updated",
            "universe": universe_id,
            "count": len(request.tickers),
        }
    except Exception as e:
        return {"error": str(e)}, 400


@router.delete("/universe/{universe_id}")
async def delete_universe(universe_id: str):
    """Delete a universe."""
    try:
        universe = Universe(universe_id)
        if not universe.exists():
            return {"error": f"Universe '{universe_id}' not found"}, 404

        universe.delete()
        return {"status": "deleted", "universe": universe_id}
    except Exception as e:
        return {"error": str(e)}, 400


@router.post("/universe/{universe_id}/tickers")
async def add_tickers_to_universe(universe_id: str, request: TickersRequest):
    """Add tickers to an existing universe."""
    try:
        universe = Universe(universe_id)
        if not universe.exists():
            return {"error": f"Universe '{universe_id}' not found"}, 404

        universe.add_tickers(request.tickers)
        tickers = universe.get_tickers()
        return {
            "status": "added",
            "universe": universe_id,
            "count": len(tickers),
            "added": len(request.tickers),
        }
    except Exception as e:
        return {"error": str(e)}, 400


@router.delete("/universe/{universe_id}/tickers")
async def remove_tickers_from_universe(universe_id: str, request: TickersRequest):
    """Remove tickers from a universe."""
    try:
        universe = Universe(universe_id)
        if not universe.exists():
            return {"error": f"Universe '{universe_id}' not found"}, 404

        universe.remove_tickers(request.tickers)
        tickers = universe.get_tickers()
        return {
            "status": "removed",
            "universe": universe_id,
            "count": len(tickers),
            "removed": len(request.tickers),
        }
    except Exception as e:
        return {"error": str(e)}, 400


@router.get("/tickers/{ticker}")
async def get_ticker_info(ticker: str):
    """Get detailed information about a ticker."""
    info = manager.get_ticker_info(ticker)
    if not info:
        return {"error": "Ticker not found"}, 404
    return {"ticker": ticker, "info": info}
