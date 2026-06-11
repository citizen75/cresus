"""Financial data management for universes and tickers."""

import logging
from typing import List, Dict, Any, Optional
from tools.universe.universe import Universe

logger = logging.getLogger(__name__)


class FinancialDataManager:
    """Manage financial data and universes."""

    def __init__(self):
        self.logger = logger
        self.universe_map = {
            "stocks": ["srd", "cac40", "nasdaq_100", "sp500"],
            "etfs": ["etf_pea", "etf_fr"],
            "funds": ["funds_fr"],
            "indices": ["indices_main"],
            "currencies": ["forex_major", "forex_exotic"],
        }

    def get_asset_categories(self) -> List[Dict[str, str]]:
        """Get available asset categories."""
        return [
            {"id": "stocks", "label": "Stocks"},
            {"id": "etfs", "label": "ETFs"},
            {"id": "funds", "label": "Funds"},
            {"id": "indices", "label": "Indices"},
            {"id": "currencies", "label": "Currencies"},
        ]

    def get_universes(self, category: str) -> List[Dict[str, Any]]:
        """Get universes for a category."""
        universe_ids = self.universe_map.get(category, [])
        universes = []

        for uni_id in universe_ids:
            try:
                universe = Universe(uni_id)
                if universe.exists():
                    tickers = universe.get_tickers()
                    count = len(tickers)
                    universes.append({
                        "id": uni_id,
                        "name": self._format_universe_name(uni_id),
                        "count": count,
                    })
                    self.logger.debug(f"Universe {uni_id}: {count} tickers")
            except Exception as e:
                self.logger.warning(f"Failed to load universe {uni_id}: {e}")

        return universes

    @staticmethod
    def _format_universe_name(universe_id: str) -> str:
        """Format universe ID as human-readable name."""
        names = {
            "srd": "Euronext SRD (France)",
            "cac40": "CAC 40 Index",
            "nasdaq_100": "NASDAQ 100",
            "sp500": "S&P 500",
            "etf_pea": "ETF PEA (France)",
            "etf_fr": "French ETFs",
            "funds_fr": "French Funds",
            "indices_main": "Major Indices",
            "forex_major": "Major Pairs",
            "forex_exotic": "Exotic Pairs",
        }
        return names.get(universe_id, universe_id.replace("_", " ").title())

    def get_tickers(self, category: str, universe: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get tickers for a category and universe."""
        self.logger.info(f"Loading tickers for {category}/{universe}")

        try:
            uni = Universe(universe)
            if not uni.exists():
                return []

            ticker_symbols = uni.get_tickers()
            tickers = []

            for symbol in ticker_symbols[:limit]:
                tickers.append({
                    "symbol": symbol,
                    "name": symbol,  # TODO: Get from financialdatabase
                    "sector": None,  # TODO: Get from financialdatabase
                    "market_cap": None,  # TODO: Get from financialdatabase
                })

            return tickers
        except Exception as e:
            self.logger.error(f"Failed to load tickers for {universe}: {e}")
            return []

    def search_tickers(self, query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for tickers by symbol or name."""
        self.logger.info(f"Searching tickers: {query}")
        return []

    def get_ticker_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a ticker."""
        self.logger.info(f"Getting info for {ticker}")
        return None
