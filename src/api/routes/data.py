"""Data management API routes."""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional
import time
import pandas as pd
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
            tickers = TickerIntelligence.batch_enrich_flat(tickers, asset_type="equities")

            # Fallback: Add country/exchange directly from FinanceDatabase if missing
            try:
                import financedatabase as fd
                db = fd.Equities()
                all_data = db.select()
                for ticker in tickers:
                    symbol = ticker.get("symbol", "").upper()
                    if symbol in all_data.index and (not ticker.get("country") or not ticker.get("exchange")):
                        row = all_data.loc[symbol]
                        if not ticker.get("country") and "country" in all_data.columns:
                            ticker["country"] = str(row["country"]) if pd.notna(row["country"]) else None
                        if not ticker.get("exchange"):
                            exchange_val = None
                            if "exchange" in all_data.columns and pd.notna(row["exchange"]):
                                exchange_val = str(row["exchange"])
                            elif "market" in all_data.columns and pd.notna(row["market"]):
                                exchange_val = str(row["market"])
                            if exchange_val:
                                ticker["exchange"] = exchange_val
            except Exception as e:
                pass  # Fallback failed, continue with what we have

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


@router.get("/filter")
async def filter_tickers(
    countries: str = Query(None, description="Comma-separated country codes (FR,US,DE,NL,etc.)"),
    asset_type: str = Query(None, description="Asset type (stocks, etfs, funds, indices)"),
    limit: int = Query(1000, description="Max number of tickers"),
    enrich: bool = Query(True, description="Enrich with fundamentals data"),
):
    """Filter tickers by country and asset type using FinanceDatabase.

    Queries FinanceDatabase directly for maximum coverage:
    - All countries and exchanges supported
    - All asset types available
    - No universe file limitations

    Examples:
    - ?countries=US&asset_type=etfs → US ETFs (NASDAQ, NYSE ARCA, etc.)
    - ?countries=FR,DE&asset_type=stocks → French and German stocks
    - ?asset_type=etfs → All ETFs (worldwide)
    """
    try:
        import financedatabase as fd

        # Country code to FinanceDatabase country name mapping (for stocks)
        country_name_map = {
            "FR": "France",
            "US": "United States",
            "DE": "Germany",
            "NL": "Netherlands",
            "GB": "United Kingdom",
            "IT": "Italy",
            "ES": "Spain",
            "CH": "Switzerland",
            "SE": "Sweden",
            "CA": "Canada",
            "AU": "Australia",
            "JP": "Japan",
            "HK": "Hong Kong",
            "SG": "Singapore",
            "IN": "India",
            "BR": "Brazil",
            "MX": "Mexico",
            "ZA": "South Africa",
        }

        # Country code to exchange MIC codes mapping (for ETFs)
        country_to_exchanges = {
            "US": ["ARCX", "XNAS", "XNYS"],  # NYSE ARCA, NASDAQ, NYSE
            "FR": ["XPAR", "XFRA"],  # Euronext Paris, Euroclear
            "DE": ["XBER", "XMUN", "XDUS", "XFRA", "XHAM"],  # German exchanges
            "NL": ["XAMS"],  # Amsterdam
            "GB": ["XLON"],  # London Stock Exchange
            "IT": ["XMIL"],  # Milan
            "ES": ["XMAD"],  # Madrid
            "CH": ["XSWX"],  # Swiss Exchange
            "SE": ["XSTO"],  # Stockholm
            "CA": ["XTSE"],  # Toronto
            "AU": ["XASX"],  # Australian
            "JP": ["XTKS"],  # Tokyo
            "HK": ["XHKG"],  # Hong Kong
            "SG": ["XSES"],  # Singapore
            "BR": ["BVMF"],  # Brazil
            "MX": ["XMEX"],  # Mexico
        }

        all_tickers = []

        # Determine which database to query
        asset_type_lower = asset_type.lower() if asset_type else None

        if asset_type_lower == "stocks":
            db = fd.Equities()
        elif asset_type_lower == "etfs":
            db = fd.ETFs()
        elif asset_type_lower == "funds":
            db = fd.Funds()
        elif asset_type_lower == "indices":
            db = fd.Indices()
        else:
            return {
                "countries": countries,
                "asset_type": asset_type,
                "tickers": [],
                "count": 0,
                "error": "Invalid asset_type. Must be: stocks, etfs, funds, or indices"
            }

        # Build query filters
        query_kwargs = {}

        if countries:
            # Parse country codes
            country_list = [c.strip().upper() for c in countries.split(",")]

            if asset_type_lower == "etfs":
                # ETFs: Query by exchange MIC codes
                exchanges = []
                for code in country_list:
                    exchanges.extend(country_to_exchanges.get(code, []))

                if exchanges:
                    try:
                        data = db.select(mic=exchanges)
                        if not data.empty:
                            for idx, row in data.iterrows():
                                ticker_data = {
                                    "symbol": idx,
                                    "name": str(row.get("name", idx)) if pd.notna(row.get("name")) else idx,
                                }

                                # Add available fields
                                if "currency" in data.columns and pd.notna(row.get("currency")):
                                    ticker_data["currency"] = str(row.get("currency"))
                                if "exchange" in data.columns and pd.notna(row.get("exchange")):
                                    ticker_data["exchange"] = str(row.get("exchange"))

                                all_tickers.append(ticker_data)
                    except Exception:
                        pass
            else:
                # Stocks, Funds, Indices: Query by country name
                country_names = []
                for code in country_list:
                    if code in country_name_map:
                        country_names.append(country_name_map[code])

                if country_names:
                    for country_name in country_names:
                        try:
                            data = db.select(country=country_name)
                            if not data.empty:
                                for idx, row in data.iterrows():
                                    ticker_data = {
                                        "symbol": idx,
                                        "name": str(row.get("name", idx)) if pd.notna(row.get("name")) else idx,
                                    }

                                    # Add available fields based on asset type
                                    if "currency" in data.columns and pd.notna(row.get("currency")):
                                        ticker_data["currency"] = str(row.get("currency"))
                                    if "exchange" in data.columns and pd.notna(row.get("exchange")):
                                        ticker_data["exchange"] = str(row.get("exchange"))
                                    if "country" in data.columns and pd.notna(row.get("country")):
                                        ticker_data["country"] = str(row.get("country"))

                                    # Add sector/industry for stocks
                                    if asset_type_lower == "stocks":
                                        if "sector" in data.columns and pd.notna(row.get("sector")):
                                            ticker_data["sector"] = str(row.get("sector"))
                                        if "industry" in data.columns and pd.notna(row.get("industry")):
                                            ticker_data["industry"] = str(row.get("industry"))

                                    all_tickers.append(ticker_data)
                        except Exception:
                            pass
        else:
            # No country filter - get all tickers for this asset type
            try:
                data = db.select()
                if not data.empty:
                    for idx, row in data.iterrows():
                        ticker_data = {
                            "symbol": idx,
                            "name": str(row.get("name", idx)) if pd.notna(row.get("name")) else idx,
                        }

                        # Add available fields
                        if "currency" in data.columns and pd.notna(row.get("currency")):
                            ticker_data["currency"] = str(row.get("currency"))
                        if "exchange" in data.columns and pd.notna(row.get("exchange")):
                            ticker_data["exchange"] = str(row.get("exchange"))
                        if "country" in data.columns and pd.notna(row.get("country")):
                            ticker_data["country"] = str(row.get("country"))

                        # Add sector for stocks
                        if asset_type_lower == "stocks" and "sector" in data.columns and pd.notna(row.get("sector")):
                            ticker_data["sector"] = str(row.get("sector"))
                        if asset_type_lower == "stocks" and "industry" in data.columns and pd.notna(row.get("industry")):
                            ticker_data["industry"] = str(row.get("industry"))

                        all_tickers.append(ticker_data)
            except Exception:
                pass

        # Deduplicate by symbol
        seen = set()
        unique_tickers = []
        for ticker in all_tickers:
            symbol = ticker.get("symbol", "").upper()
            if symbol and symbol not in seen:
                seen.add(symbol)
                unique_tickers.append(ticker)

        # Optionally enrich with additional data (price, fundamentals)
        if enrich and unique_tickers:
            try:
                unique_tickers = TickerIntelligence.batch_enrich_flat(
                    unique_tickers,
                    asset_type=asset_type_lower if asset_type_lower else "equities"
                )
            except Exception:
                pass  # Continue even if enrichment fails

        # Limit results
        unique_tickers = unique_tickers[:limit]

        return {
            "countries": countries,
            "asset_type": asset_type,
            "tickers": unique_tickers,
            "count": len(unique_tickers),
        }

    except Exception as e:
        return {"error": str(e)}, 400


@router.get("/category/{category}")
async def get_category_tickers(
    category: str,
    limit: int = Query(1000, description="Max number of tickers"),
    enrich: bool = Query(True, description="Enrich with fundamentals data"),
):
    """Get all tickers in a category with optional enrichment.

    Category mapping:
    - stocks: All stock universes (srd, cac40, nasdaq_100, sp_25, xetra, etc.)
    - etfs: All ETF universes (etf_pea, etf_fr, etf_pea_full)
    - funds: Fund universes
    - indices: Index universes
    - currencies: Currency universes
    """
    category_map = {
        "stocks": ["srd", "cac40", "nasdaq_100", "sp_25", "enx_large", "enx_mid", "enx_small", "xetra"],
        "etfs": ["etf_pea", "etf_fr", "etf_pea_full", "etf_pea_test"],
        "funds": [],  # No fund universes currently
        "indices": ["index"],
        "currencies": [],  # No currency universes currently
    }

    universes = category_map.get(category.lower(), [])
    if not universes:
        return {"category": category, "tickers": [], "count": 0}

    all_tickers = []
    try:
        for uni_id in universes:
            try:
                uni = Universe(uni_id)
                if uni.exists():
                    tickers = uni.get_tickers_with_metadata()
                    all_tickers.extend(tickers)
            except Exception as e:
                pass

        # Optionally enrich with fundamentals
        if enrich:
            all_tickers = TickerIntelligence.batch_enrich_flat(all_tickers, asset_type=category.lower() if category.lower() in ["stocks", "etfs", "funds", "indices"] else "equities")

        # Limit results
        all_tickers = all_tickers[:limit]

        return {
            "category": category,
            "tickers": all_tickers,
            "count": len(all_tickers),
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
