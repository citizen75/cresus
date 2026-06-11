"""Integration with FinanceDatabase for ticker enrichment."""

import logging
from typing import List, Dict, Any, Optional
import financedatabase as fd

logger = logging.getLogger(__name__)

# Initialize databases (expensive, done once)
_equities = None
_equities_data = None
_etfs = None
_etfs_data = None
_funds = None
_funds_data = None
_indices = None
_indices_data = None


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


def get_equities_data():
    """Get cached equities data (loads once)."""
    global _equities_data
    if _equities_data is None:
        logger.info("Loading all equities data...")
        _equities_data = get_equities().select()
    return _equities_data


def get_etfs_data():
    """Get cached ETFs data (loads once)."""
    global _etfs_data
    if _etfs_data is None:
        logger.info("Loading all ETFs data...")
        _etfs_data = get_etfs().select()
    return _etfs_data


def get_funds_data():
    """Get cached funds data (loads once)."""
    global _funds_data
    if _funds_data is None:
        logger.info("Loading all funds data...")
        _funds_data = get_funds().select()
    return _funds_data


def get_indices_data():
    """Get cached indices data (loads once)."""
    global _indices_data
    if _indices_data is None:
        logger.info("Loading all indices data...")
        _indices_data = get_indices().select()
    return _indices_data


def enrich_ticker(ticker_symbol: str, asset_type: str = "equities") -> Optional[Dict[str, Any]]:
    """Enrich a single ticker with FinanceDatabase metadata.

    Args:
        ticker_symbol: Ticker symbol (e.g., 'AAPL', 'AC.PA')
        asset_type: Type of asset ('equities', 'etfs', 'funds', 'indices')

    Returns:
        Dictionary with enriched ticker data, or None if not found
    """
    logger.debug(f"Enriching {ticker_symbol} ({asset_type})")
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

        # Get cached data (loads once per database)
        if asset_type == "equities":
            all_data = get_equities_data()
        elif asset_type == "etfs":
            all_data = get_etfs_data()
        elif asset_type == "funds":
            all_data = get_funds_data()
        else:  # indices
            all_data = get_indices_data()

        # Look up by index (ticker symbol is the index)
        if ticker_symbol.upper() not in all_data.index:
            return None

        row = all_data.loc[ticker_symbol.upper()]

        # Get exchange - try exchange first, fallback to market
        exchange_value = None
        try:
            if pd.notna(row["exchange"]):
                exchange_value = str(row["exchange"])
            elif pd.notna(row["market"]):
                exchange_value = str(row["market"])
        except (KeyError, TypeError):
            pass

        result = {
            "symbol": ticker_symbol.upper(),
            "name": str(row["name"]) if "name" in row and pd.notna(row["name"]) else ticker_symbol,
            "sector": str(row["sector"]) if "sector" in row and pd.notna(row["sector"]) else None,
            "industry": str(row["industry"]) if "industry" in row and pd.notna(row["industry"]) else None,
            "industry_group": str(row["industry_group"]) if "industry_group" in row and pd.notna(row["industry_group"]) else None,
            "country": str(row["country"]) if "country" in row and pd.notna(row["country"]) else None,
            "currency": str(row["currency"]) if "currency" in row and pd.notna(row["currency"]) else None,
            "exchange": exchange_value,
            "market": str(row["market"]) if "market" in row and pd.notna(row["market"]) else None,
            "website": str(row["website"]) if "website" in row and pd.notna(row["website"]) else None,
            "market_cap": str(row["market_cap"]) if "market_cap" in row and pd.notna(row["market_cap"]) else None,
        }
        logger.debug(f"Enriched {ticker_symbol}: country={result.get('country')}, exchange={result.get('exchange')}")
        return result
    except Exception as e:
        logger.error(f"Failed to enrich {ticker_symbol}: {e}", exc_info=True)
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
