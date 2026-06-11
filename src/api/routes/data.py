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

class EnrichedTickersRequest(BaseModel):
    """Request to add enriched tickers with metadata."""
    tickers: List[dict]  # List of {"symbol": "...", "name": "...", etc}

router = APIRouter(prefix="/data", tags=["data"])
manager = FinancialDataManager()

# Cache for loaded data to avoid repeated Parquet reads
_data_cache = {}
_cache_max_size = 5  # Keep last 5 tickers

# Cache for universe list (TTL: 300 seconds / 5 minutes)
_universe_list_cache = None
_universe_list_cache_time = 0
CACHE_TTL = 300

def _clear_universe_cache():
  """Clear the universe list cache."""
  global _universe_list_cache, _universe_list_cache_time
  _universe_list_cache = None
  _universe_list_cache_time = 0


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
    limit: int = Query(None, description="Max number of tickers (None = all results)"),
    enrich: bool = Query(True, description="Enrich with fundamentals data"),
    asset_type: str = Query("equities", description="Asset type (equities, etfs, funds, indices)"),
):
    """Get tickers for a specific universe with optional metadata enrichment.

    Args:
        universe_id: Universe ID
        limit: Max number of tickers
        enrich: Whether to enrich with fundamentals (sector, industry, price, etc.)
        asset_type: Asset type for enrichment (equities, etfs, funds, indices)
    """
    try:
        universe = Universe(universe_id)
        if not universe.exists():
            return {"error": f"Universe '{universe_id}' not found"}, 404

        # Load only ticker symbols (not metadata)
        symbols = universe.get_tickers()
        if limit:
            symbols = symbols[:limit]

        # Convert symbols to basic ticker dict
        tickers = [{"symbol": symbol} for symbol in symbols]

        # Enrich with fundamentals on-the-fly
        if enrich and tickers:
            # Primary enrichment via TickerIntelligence
            try:
                tickers = TickerIntelligence.batch_enrich_flat(tickers, asset_type=asset_type)
            except Exception as e:
                # If enrichment fails, continue with basic symbols
                pass

            # Secondary enrichment from FinanceDatabase
            try:
                import financedatabase as fd

                # Select correct database based on asset type
                if asset_type == "etfs":
                    db = fd.ETFs()
                elif asset_type == "funds":
                    db = fd.Funds()
                elif asset_type == "indices":
                    db = fd.Indices()
                else:
                    db = fd.Equities()

                all_data = db.select()
                for ticker in tickers:
                    symbol = ticker.get("symbol", "").upper()
                    if symbol in all_data.index:
                        row = all_data.loc[symbol]

                        # Fill missing fields from FinanceDatabase
                        if not ticker.get("name") and "name" in all_data.columns and pd.notna(row["name"]):
                            ticker["name"] = str(row["name"])
                        if not ticker.get("country") and "country" in all_data.columns and pd.notna(row["country"]):
                            ticker["country"] = str(row["country"])
                        if not ticker.get("currency") and "currency" in all_data.columns and pd.notna(row["currency"]):
                            ticker["currency"] = str(row["currency"])
                        if not ticker.get("exchange"):
                            exchange_val = None
                            if "exchange" in all_data.columns and pd.notna(row["exchange"]):
                                exchange_val = str(row["exchange"])
                            elif "market" in all_data.columns and pd.notna(row["market"]):
                                exchange_val = str(row["market"])
                            if exchange_val:
                                ticker["exchange"] = exchange_val
            except Exception as e:
                pass  # FinanceDatabase fallback failed, continue with enriched data

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
        _clear_universe_cache()  # Invalidate cache
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
        _clear_universe_cache()  # Invalidate cache
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
        _clear_universe_cache()  # Invalidate cache
        return {"status": "deleted", "universe": universe_id}
    except Exception as e:
        return {"error": str(e)}, 400


class RenameRequest(BaseModel):
    """Request to rename a universe."""
    new_id: str


@router.patch("/universe/{universe_id}")
async def rename_universe(universe_id: str, request: RenameRequest):
    """Rename a universe."""
    try:
        from pathlib import Path

        old_universe = Universe(universe_id)
        if not old_universe.exists():
            return {"error": f"Universe '{universe_id}' not found"}, 404

        new_universe = Universe(request.new_id)
        if new_universe.exists():
            return {"error": f"Universe '{request.new_id}' already exists"}, 409

        # Rename the file
        old_path = old_universe.filepath
        new_path = new_universe.filepath
        old_path.rename(new_path)

        _clear_universe_cache()  # Invalidate cache
        return {
            "status": "renamed",
            "old_id": universe_id,
            "new_id": request.new_id,
        }
    except Exception as e:
        return {"error": str(e)}, 400


@router.post("/universe/{universe_id}/fetch-data")
async def fetch_universe_data(
    universe_id: str,
    asset_type: str = Query("equities", description="Asset type (equities, etfs, funds, indices)"),
):
    """Fetch and cache historical data and fundamentals for all tickers in a universe."""
    try:
        import yfinance as yf
        import financedatabase as fd

        universe = Universe(universe_id)
        if not universe.exists():
            return {"error": f"Universe '{universe_id}' not found"}, 404

        # Get all tickers
        symbols = universe.get_tickers()
        if not symbols:
            return {"status": "no_tickers", "universe": universe_id, "count": 0}

        # Select correct database based on asset type
        if asset_type == "etfs":
            db = fd.ETFs()
        elif asset_type == "funds":
            db = fd.Funds()
        elif asset_type == "indices":
            db = fd.Indices()
        else:
            db = fd.Equities()

        all_data = db.select()

        # Fetch data for each ticker
        results = {
            "universe": universe_id,
            "total": len(symbols),
            "fetched": 0,
            "failed": 0,
            "tickers": {},
        }

        for symbol in symbols:
            try:
                ticker_result = {"symbol": symbol, "history": False, "fundamentals": False}

                # Fetch historical data
                try:
                    hist = yf.download(symbol, period="365d", progress=False)
                    if not hist.empty:
                        ticker_result["history"] = True
                except Exception as e:
                    pass

                # Fetch fundamentals from FinanceDatabase
                try:
                    if symbol.upper() in all_data.index:
                        row = all_data.loc[symbol.upper()]
                        ticker_result["fundamentals"] = True
                except Exception as e:
                    pass

                if ticker_result["history"] or ticker_result["fundamentals"]:
                    results["fetched"] += 1
                    results["tickers"][symbol] = ticker_result
                else:
                    results["failed"] += 1

            except Exception as e:
                results["failed"] += 1
                results["tickers"][symbol] = {"symbol": symbol, "error": str(e)}

        return results

    except Exception as e:
        return {"error": str(e)}, 500


@router.post("/universe/{universe_id}/tickers")
async def add_tickers_to_universe(universe_id: str, request: TickersRequest):
    """Add tickers to an existing universe.

    Optionally accepts enriched ticker data to preserve metadata.
    """
    try:
        universe = Universe(universe_id)
        if not universe.exists():
            return {"error": f"Universe '{universe_id}' not found"}, 404

        # If enriched data provided, add tickers with metadata columns
        if hasattr(request, 'enriched') and request.enriched:
            try:
                df = universe.load_df()
                # Add enriched rows
                for ticker_data in request.enriched:
                    new_row = {
                        'TickerYahoo': ticker_data.get('symbol'),
                        'name': ticker_data.get('name'),
                        'country': ticker_data.get('country'),
                        'currency': ticker_data.get('currency'),
                        'exchange': ticker_data.get('exchange'),
                        'sector': ticker_data.get('sector'),
                        'industry': ticker_data.get('industry'),
                    }
                    # Add row to dataframe
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(universe.filepath, index=False, encoding='utf-8-sig')
            except Exception as e:
                # Fallback to simple add if enriched add fails
                universe.add_tickers(request.tickers)
        else:
            # Simple add without enrichment data
            universe.add_tickers(request.tickers)

        tickers = universe.get_tickers()
        _clear_universe_cache()  # Invalidate cache
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
        _clear_universe_cache()  # Invalidate cache
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
    limit: int = Query(None, description="Max number of tickers (None = all results)"),
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
        # Note: Enrichment only for stocks with reasonable limits (ETF enrichment is too slow)
        if enrich and unique_tickers and asset_type_lower != "etfs" and len(unique_tickers) < 500:
            try:
                unique_tickers = TickerIntelligence.batch_enrich_flat(
                    unique_tickers,
                    asset_type=asset_type_lower if asset_type_lower else "equities"
                )
            except Exception:
                pass  # Continue even if enrichment fails

        # Apply limit if specified (otherwise return all)
        if limit:
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


@router.get("/history/{ticker}")
async def get_ticker_history(
    ticker: str,
    days: int = Query(365, description="Number of days of history"),
    indicator: str = Query(None, description="Optional indicator to compute (e.g., sha_10)")
):
    """Get historical price data using /src/tools/data/ (Parquet cache).

    Args:
        ticker: Ticker symbol
        days: Number of days to return
        indicator: Optional indicator (sha_10)
    """
    try:
        from tools.data.core import DataHistory, Fundamental
        from tools.indicators import calculate
        from datetime import datetime, timedelta

        # Check in-memory cache first
        global _data_cache
        if ticker in _data_cache:
            df = _data_cache[ticker]
        else:
            # Load from Parquet cache (~/.cresus/db/cache/history/)
            data_history = DataHistory(ticker)
            df = data_history.load_all()
            if df.empty:
                data_history.fetch()
                df = data_history.load_all()

            # Store in memory cache
            if len(_data_cache) >= _cache_max_size:
                _data_cache.pop(next(iter(_data_cache)))
            _data_cache[ticker] = df

        # Load fundamental data
        fundamental = Fundamental(ticker)

        if df.empty:
            return {"ticker": ticker, "data": [], "history": []}

        # Limit to requested days
        if days:
            cutoff = datetime.now() - timedelta(days=days)
            if 'timestamp' in df.columns:
                df_filtered = df[pd.to_datetime(df['timestamp']) >= cutoff].copy()
            else:
                df_filtered = df[df.index >= cutoff].copy()
        else:
            df_filtered = df.copy()

        # Calculate indicators on the filtered dataset
        indicators_dict = {}
        if not df_filtered.empty and indicator:
            try:
                indicators_dict = calculate([indicator], df_filtered)
            except Exception as e:
                pass

        # Convert to dict list and merge indicators
        history = []
        for idx, row in df_filtered.iterrows():
            # Handle timestamp/date
            if 'timestamp' in row and row['timestamp']:
                date_str = pd.to_datetime(row['timestamp']).strftime('%Y-%m-%d')
            elif hasattr(idx, 'strftime'):
                date_str = idx.strftime('%Y-%m-%d')
            else:
                date_str = str(idx)[:10]

            row_dict = {
                "timestamp": date_str,
                "date": date_str,
                "open": float(row.get('open', row.get('Open', 0))),
                "high": float(row.get('high', row.get('High', 0))),
                "low": float(row.get('low', row.get('Low', 0))),
                "close": float(row.get('close', row.get('Close', 0))),
                "volume": int(row.get('volume', row.get('Volume', 0))),
            }

            # Add indicators if available
            for ind_key, ind_series in indicators_dict.items():
                # Find the value for this row (by position in the filtered dataframe)
                position = df_filtered.index.get_loc(idx)
                if position < len(ind_series):
                    val = ind_series.iloc[position]
                    if pd.notna(val):
                        if hasattr(val, 'item'):
                            val = val.item()
                        row_dict[ind_key] = round(float(val), 4) if isinstance(val, (int, float)) else val

            history.append(row_dict)

        fund = fundamental.load() or {}
        return {
            "ticker": ticker,
            "data": history,
            "history": history,
            "fundamentals": fund.get("data", {}),
            "source": "parquet+indicators"
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"ticker": ticker, "data": [], "history": [], "error": str(e)}


@router.get("/fundamental/{ticker}")
async def get_ticker_fundamental(ticker: str):
    """Get fundamental data for a ticker (cached from tools.data.core.Fundamental).

    Args:
        ticker: Ticker symbol
    """
    try:
        from tools.data.core import Fundamental

        fundamental = Fundamental(ticker)

        # Try to load from cache first (instant if available)
        cached_data = fundamental.load()
        if cached_data:
            print(f"✅ Using cached fundamental for {ticker}")
            return cached_data

        # If not cached, fetch and cache (slow first time)
        print(f"📡 Fetching fresh fundamental for {ticker}")
        result = fundamental.fetch()

        return result

    except Exception as e:
        from fastapi.responses import JSONResponse
        print(f"❌ Error fetching fundamental for {ticker}: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "ticker": ticker,
                "data": {
                    "company": {},
                    "quotation": {}
                },
                "error": str(e)
            }
        )
