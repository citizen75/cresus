"""Integration with FinanceDatabase for ticker enrichment."""

import logging
from typing import List, Dict, Any, Optional
import financedatabase as fd

logger = logging.getLogger(__name__)

# Initialize databases (expensive, done once)
_equities = None
_etfs = None
_funds = None
_indices = None


def get_equities():
    """Lazy load equities database."""
    global _equities
    if _equities is None:
        logger.info("Loading FinanceDatabase Equities...")
        _equities = fd.Equities()
    return _equities


def get_etfs():
    """Lazy load ETFs database."""
    global _etfs
    if _etfs is None:
        logger.info("Loading FinanceDatabase ETFs...")
        _etfs = fd.ETFs()
    return _etfs


def get_funds():
    """Lazy load Funds database."""
    global _funds
    if _funds is None:
        logger.info("Loading FinanceDatabase Funds...")
        _funds = fd.Funds()
    return _funds


def get_indices():
    """Lazy load Indices database."""
    global _indices
    if _indices is None:
        logger.info("Loading FinanceDatabase Indices...")
        _indices = fd.Indices()
    return _indices


def enrich_ticker(ticker_symbol: str, asset_type: str = "equities") -> Optional[Dict[str, Any]]:
    """Enrich a single ticker with FinanceDatabase metadata.

    Args:
        ticker_symbol: Ticker symbol (e.g., 'AAPL', 'AC.PA')
        asset_type: Type of asset ('equities', 'etfs', 'funds', 'indices')

    Returns:
        Dictionary with enriched ticker data, or None if not found
    """
    try:
        if asset_type == "equities":
            db = get_equities()
        elif asset_type == "etfs":
            db = get_etfs()
        elif asset_type == "funds":
            db = get_funds()
        elif asset_type == "indices":
            db = get_indices()
        else:
            return None

        # Query by symbol
        results = db.select(symbol=ticker_symbol.upper())
        if results.empty:
            return None

        # Get the first result (primary listing)
        row = results.iloc[0]

        # Get exchange - try exchange first, fallback to market
        exchange_value = None
        if pd.notna(row.get("exchange")):
            exchange_value = str(row.get("exchange"))
        elif pd.notna(row.get("market")):
            exchange_value = str(row.get("market"))

        return {
            "symbol": str(row.get("symbol", ticker_symbol)),
            "name": str(row.get("name", ticker_symbol)),
            "sector": str(row.get("sector")) if pd.notna(row.get("sector")) else None,
            "industry": str(row.get("industry")) if pd.notna(row.get("industry")) else None,
            "industry_group": str(row.get("industry_group")) if pd.notna(row.get("industry_group")) else None,
            "country": str(row.get("country")) if pd.notna(row.get("country")) else None,
            "currency": str(row.get("currency")) if pd.notna(row.get("currency")) else None,
            "exchange": exchange_value,
            "market": str(row.get("market")) if pd.notna(row.get("market")) else None,
            "website": str(row.get("website")) if pd.notna(row.get("website")) else None,
            "market_cap": str(row.get("market_cap")) if pd.notna(row.get("market_cap")) else None,
        }
    except Exception as e:
        logger.warning(f"Failed to enrich {ticker_symbol}: {e}")
        return None


def enrich_tickers(ticker_symbols: List[str], asset_type: str = "equities") -> List[Dict[str, Any]]:
    """Enrich multiple tickers with FinanceDatabase metadata.

    Args:
        ticker_symbols: List of ticker symbols
        asset_type: Type of asset ('equities', 'etfs', 'funds', 'indices')

    Returns:
        List of enriched ticker data
    """
    enriched = []
    for symbol in ticker_symbols:
        data = enrich_ticker(symbol, asset_type)
        if data:
            enriched.append(data)
    return enriched


def search_by_country(country: str, asset_type: str = "equities", market: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search tickers by country using FinanceDatabase.

    Args:
        country: Country name (e.g., 'Netherlands', 'United States', 'France')
        asset_type: Type of asset ('equities', 'etfs', 'funds', 'indices')
        market: Optional market/exchange to filter

    Returns:
        List of tickers matching the criteria
    """
    try:
        if asset_type == "equities":
            db = get_equities()
        elif asset_type == "etfs":
            db = get_etfs()
        elif asset_type == "funds":
            db = get_funds()
        elif asset_type == "indices":
            db = get_indices()
        else:
            return []

        # Build query
        kwargs = {"country": country}
        if market:
            kwargs["market"] = market

        results = db.select(**kwargs)
        if results.empty:
            return []

        # Convert to list of dicts
        tickers = []
        for idx, row in results.iterrows():
            # Get exchange - try exchange first, fallback to market
            exchange_value = None
            if pd.notna(row.get("exchange")):
                exchange_value = str(row.get("exchange"))
            elif pd.notna(row.get("market")):
                exchange_value = str(row.get("market"))

            tickers.append({
                "symbol": str(row.get("symbol")),
                "name": str(row.get("name")),
                "sector": str(row.get("sector")) if pd.notna(row.get("sector")) else None,
                "industry": str(row.get("industry")) if pd.notna(row.get("industry")) else None,
                "country": str(row.get("country")) if pd.notna(row.get("country")) else None,
                "currency": str(row.get("currency")) if pd.notna(row.get("currency")) else None,
                "exchange": exchange_value,
            })

        return tickers
    except Exception as e:
        logger.warning(f"Failed to search by country {country}: {e}")
        return []


# Import pandas for type checking
import pandas as pd
