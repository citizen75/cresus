"""Unified ticker data enrichment system combining metadata, fundamentals, and market data."""

import logging
import threading
import time
from typing import Dict, Any, Optional
from pathlib import Path
import json

from tools.universe.universe import Universe
from tools.data.core import Fundamental
from tools.data.financedatabase_manager import enrich_ticker as fd_enrich_ticker
from utils.env import get_db_root

logger = logging.getLogger(__name__)

# Process-wide ticker->metadata index, rebuilt at most once per TTL window.
# Without this, every uncached ticker enrichment re-reads and re-parses every
# universe CSV from disk just to find the one row it needs - O(universes *
# tickers) per ticker, instead of O(1) after a single shared index build.
_UNIVERSE_INDEX_TTL = 300
_universe_index_lock = threading.Lock()
_universe_index: Optional[Dict[str, Dict[str, Any]]] = None
_universe_index_built_at: float = 0.0


def _build_universe_index() -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for uni_id in Universe.list_universes():
        try:
            uni = Universe(uni_id)
            if not uni.exists():
                continue
            for ticker_data in uni.get_tickers_with_metadata():
                symbol = ticker_data.get("symbol")
                if symbol:
                    index.setdefault(symbol.upper(), ticker_data)
        except Exception as e:
            # db/universes/ also holds non-universe housekeeping files
            # (blacklist.csv, *_errors.csv) that don't parse as ticker lists.
            logger.debug(f"Skipped {uni_id} while building universe index: {e}")
    return index


def _get_universe_index() -> Dict[str, Dict[str, Any]]:
    global _universe_index, _universe_index_built_at
    now = time.time()
    if _universe_index is not None and (now - _universe_index_built_at) < _UNIVERSE_INDEX_TTL:
        return _universe_index

    with _universe_index_lock:
        now = time.time()
        if _universe_index is None or (now - _universe_index_built_at) >= _UNIVERSE_INDEX_TTL:
            _universe_index = _build_universe_index()
            _universe_index_built_at = now
        return _universe_index


class TickerIntelligence:
    """Unified enrichment system for complete ticker financial data.
    
    Combines:
    - Universe metadata (name, sector, industry, market cap)
    - Fundamentals (P/E, earnings, margins, analyst ratings)
    - Market data (price, change, volume)
    """

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.cache_dir = get_db_root() / "cache" / "enriched"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / f"{self.ticker}.json"

    def _load_universe_metadata(self) -> Optional[Dict[str, Any]]:
        """Look up ticker metadata from the shared universe index."""
        try:
            return _get_universe_index().get(self.ticker)
        except Exception as e:
            logger.warning(f"Failed to load universe metadata for {self.ticker}: {e}")
            return None

    def _load_fundamentals(self) -> Optional[Dict[str, Any]]:
        """Load fundamental data from yfinance."""
        try:
            fd = Fundamental(self.ticker)
            return fd.fetch()
        except Exception as e:
            logger.warning(f"Failed to load fundamentals for {self.ticker}: {e}")
            return None

    def _load_from_cache(self) -> Optional[Dict[str, Any]]:
        """Load cached enriched data."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file) as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cache for {self.ticker}: {e}")
        return None

    def _save_to_cache(self, data: Dict[str, Any]) -> None:
        """Save enriched data to cache."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache for {self.ticker}: {e}")

    def get_enriched_data(self, use_cache: bool = True, asset_type: str = "equities") -> Dict[str, Any]:
        """Get complete enriched ticker data.

        Combines universe metadata, fundamentals, and market data.

        Args:
            use_cache: Use cached data if available

        Returns:
            Complete ticker financial data
        """
        # Try cache first
        if use_cache:
            cached = self._load_from_cache()
            if cached:
                return cached

        # Start with ticker symbol
        enriched = {
            "symbol": self.ticker,
            "metadata": {},
            "fundamentals": {},
            "financedatabase": {},
        }

        # Load universe metadata (name, sector, industry, market_cap, price)
        metadata = self._load_universe_metadata()
        if metadata:
            enriched["metadata"] = metadata
        else:
            enriched["metadata"]["symbol"] = self.ticker

        # Load FinanceDatabase metadata (sector, industry, country, exchange, etc.)
        try:
            logger.debug(f"Calling fd_enrich_ticker for {self.ticker} ({asset_type})")
            fd_metadata = fd_enrich_ticker(self.ticker, asset_type=asset_type)
            logger.debug(f"fd_enrich_ticker returned: {fd_metadata is not None}")
            if fd_metadata:
                logger.debug(f"FinanceDB data: country={fd_metadata.get('country')}, exchange={fd_metadata.get('exchange')}")
                enriched["financedatabase"] = fd_metadata
            else:
                logger.debug(f"fd_enrich_ticker returned None for {self.ticker}")
        except Exception as e:
            logger.error(f"Failed to load FinanceDatabase metadata for {self.ticker}: {e}", exc_info=True)

        # Load fundamentals (P/E, earnings, margins, analyst ratings)
        fundamentals = self._load_fundamentals()
        if fundamentals:
            enriched["fundamentals"] = fundamentals

        # Combine into flat structure for easier API use
        enriched["combined"] = self._combine_data(enriched)

        # Cache the enriched data
        self._save_to_cache(enriched)

        return enriched

    @staticmethod
    def _combine_data(enriched: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten enriched data for API responses.

        Merges all data sources into a single level for easier consumption.
        Priority: FinanceDatabase > Fundamentals > Universe Metadata
        """
        combined = {}

        # Add metadata (universe data)
        if enriched["metadata"]:
            combined.update(enriched["metadata"])

        # Add fundamentals (yfinance data)
        if enriched["fundamentals"]:
            combined.update(enriched["fundamentals"])

        # Add FinanceDatabase data (highest priority, overwrites previous)
        if enriched["financedatabase"]:
            combined.update(enriched["financedatabase"])

        return combined

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of key financial metrics.

        Returns:
            Dictionary with key metrics from all data sources
        """
        enriched = self.get_enriched_data()
        combined = enriched["combined"]

        summary = {
            "symbol": enriched["symbol"],
            "name": combined.get("name", enriched["symbol"]),
            "sector": combined.get("sector"),
            "industry": combined.get("industry"),
            "price": combined.get("price"),
            "market_cap": combined.get("market_cap"),
            "pe_ratio": combined.get("pe_ratio"),
            "earnings_growth": combined.get("earnings_growth"),
            "dividend_yield": combined.get("dividend_yield"),
            "analyst_rating": combined.get("analyst_rating"),
        }

        # Filter out None values
        return {k: v for k, v in summary.items() if v is not None}

    @staticmethod
    def batch_enrich(tickers: list, use_cache: bool = True) -> Dict[str, Dict[str, Any]]:
        """Enrich multiple tickers at once.

        Args:
            tickers: List of ticker symbols
            use_cache: Use cached data if available

        Returns:
            Dictionary mapping ticker -> enriched data
        """
        results = {}
        for ticker in tickers:
            try:
                ti = TickerIntelligence(ticker)
                results[ticker] = ti.get_enriched_data(use_cache=use_cache)
            except Exception as e:
                logger.warning(f"Failed to enrich {ticker}: {e}")
                results[ticker] = {"symbol": ticker, "error": str(e)}

        return results

    @staticmethod
    def batch_enrich_flat(tickers_data: list, asset_type: str = "equities") -> list:
        """Enrich ticker data with fundamentals and return flattened results.

        Args:
            tickers_data: List of ticker dicts with symbol, name, etc.
            asset_type: Asset type for FinanceDatabase enrichment (equities, etfs, funds, indices)

        Returns:
            List of enriched ticker dicts with fundamentals merged in
        """
        enriched_tickers = []

        for ticker_dict in tickers_data:
            symbol = ticker_dict.get("symbol")
            if not symbol:
                enriched_tickers.append(ticker_dict)
                continue

            try:
                ti = TickerIntelligence(symbol)
                enriched = ti.get_enriched_data(use_cache=True, asset_type=asset_type)

                # Start with original metadata
                enriched_row = dict(ticker_dict)

                # Add FinanceDatabase metadata (country, exchange, sector, industry, etc.)
                if enriched.get("financedatabase"):
                    fd_data = enriched["financedatabase"]
                    for key, value in fd_data.items():
                        if value is not None:
                            enriched_row[key] = value

                # Add fundamentals data if available
                if enriched.get("fundamentals") and enriched["fundamentals"].get("data"):
                    fund_data = enriched["fundamentals"]["data"]

                    # Add company info
                    if fund_data.get("company"):
                        company = fund_data["company"]
                        if company.get("sector"):
                            enriched_row["sector"] = company.get("sector")
                        if company.get("industry"):
                            enriched_row["industry"] = company.get("industry")

                    # Add quotation data
                    if fund_data.get("quotation"):
                        quotation = fund_data["quotation"]
                        price = quotation.get("current_price")
                        enriched_row["price"] = f"{price:.2f}" if price else None

                    # Add analysts data
                    if fund_data.get("analysts"):
                        analysts = fund_data["analysts"]
                        enriched_row["recommendation"] = analysts.get("recommendation")
                        enriched_row["target_price"] = analysts.get("target_price")

                enriched_tickers.append(enriched_row)

            except Exception as e:
                logger.warning(f"Failed to enrich {symbol}: {e}")
                enriched_tickers.append(ticker_dict)

        return enriched_tickers
