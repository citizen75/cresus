"""Data management API routes."""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional
import time
from tools.data.financial import FinancialDataManager
from tools.data.enrichment import TickerIntelligence
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

# Cache for universe list (TTL: 300 seconds / 5 minutes)
_universe_list_cache = None
_universe_list_cache_time = 0
CACHE_TTL = 300


@router.get("/categories")
async def get_categories():
    """Get available asset categories."""
    return {"categories": manager.get_asset_categories()}


@router.get("/universes/list")
async def list_all_universes(use_cache: bool = Query(True, description="Use cached universe list")):
    """List all available universes with fast ticker counts.

    Uses optimized counting and caching for performance.
    """
    global _universe_list_cache, _universe_list_cache_time

    # Check cache
    if use_cache and _universe_list_cache is not None:
        if time.time() - _universe_list_cache_time < CACHE_TTL:
            return _universe_list_cache

    try:
        universes = Universe.list_universes()
        details = []

        for uni_id in universes:
            try:
                uni = Universe(uni_id)
                if uni.exists():
                    # Use fast count instead of loading all tickers
                    count = uni.count_tickers()
                    details.append({
                        "id": uni_id,
                        "name": manager._format_universe_name(uni_id),
                        "count": count,
                    })
            except Exception as e:
                # Log but continue
                pass

        result = {"universes": details, "total": len(details)}

        # Cache the result
        _universe_list_cache = result
        _universe_list_cache_time = time.time()

        return result
    except Exception as e:
        return {"error": str(e)}, 500


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
    enrich: bool = Query(True, description="Enrich with fundamentals data"),
):
    """Get tickers for a category and universe with optional metadata enrichment.

    Args:
        category: Asset category
        universe: Universe ID
        limit: Max number of tickers to return
        enrich: Whether to enrich with fundamentals (sector, industry, price, etc.)
    """
    try:
        uni = Universe(universe)
        if not uni.exists():
            return {"error": f"Universe '{universe}' not found"}, 404

        tickers = uni.get_tickers_with_metadata()[:limit]

        # Optionally enrich with fundamentals
        if enrich:
            tickers = TickerIntelligence.batch_enrich_flat(tickers)

        return {"category": category, "universe": universe, "tickers": tickers, "count": len(tickers)}
    except Exception as e:
        return {"error": str(e)}, 400


@router.get("/search")
async def search_tickers(
    q: str = Query(..., description="Search query"),
    category: str = Query(None, description="Optional category filter"),
):
    """Search for tickers."""
    results = manager.search_tickers(q, category)
    return {"query": q, "category": category, "results": results, "count": len(results)}


@router.get("/universe/{universe_id}")
async def get_universe_tickers(
    universe_id: str,
    limit: int = Query(1000, description="Max number of tickers"),
    enrich: bool = Query(True, description="Enrich with fundamentals data"),
):
    """Get tickers for a specific universe with optional metadata enrichment.

    Args:
        universe_id: Universe ID
        limit: Max number of tickers
        enrich: Whether to enrich with fundamentals (sector, industry, price, etc.)
    """
    try:
        universe = Universe(universe_id)
        if not universe.exists():
            return {"error": f"Universe '{universe_id}' not found"}, 404

        tickers = universe.get_tickers_with_metadata()[:limit]

        # Optionally enrich with fundamentals
        if enrich:
            tickers = TickerIntelligence.batch_enrich_flat(tickers)

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


@router.get("/ticker/{ticker}/enriched")
async def get_enriched_ticker(ticker: str, use_cache: bool = Query(True)):
    """Get complete enriched ticker data.

    Combines:
    - Universe metadata (name, sector, industry, market cap)
    - Fundamentals (P/E, earnings, margins, analyst ratings)
    - Market data (price, change, volume)
    """
    try:
        ti = TickerIntelligence(ticker)
        enriched = ti.get_enriched_data(use_cache=use_cache)
        return enriched
    except Exception as e:
        return {"error": str(e)}, 400


@router.get("/ticker/{ticker}/summary")
async def get_ticker_summary(ticker: str):
    """Get summary of key financial metrics for a ticker."""
    try:
        ti = TickerIntelligence(ticker)
        summary = ti.get_summary()
        return summary
    except Exception as e:
        return {"error": str(e)}, 400


@router.post("/tickers/enrich")
async def batch_enrich_tickers(request: TickersRequest, use_cache: bool = Query(True)):
    """Batch enrich multiple tickers at once.

    Returns complete financial data for multiple tickers.
    """
    try:
        results = TickerIntelligence.batch_enrich(request.tickers, use_cache=use_cache)
        return {
            "count": len(request.tickers),
            "enriched": results,
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
