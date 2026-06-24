"""Financial data management for universes and tickers."""

import logging
from typing import List, Dict, Any, Optional
from tools.universe.universe import Universe

logger = logging.getLogger(__name__)


class FinancialDataManager:
    """Manage financial data and universes."""

    def __init__(self):
        self.logger = logger
        # Kept in sync with the universe files actually shipped under
        # db/universes/ - there's no naming convention that lets us derive
        # asset class from a universe id, so this has to be a hand-kept map.
        self.universe_map = {
            "stocks": ["srd", "cac40", "nasdaq_100", "nasdaq_tech", "sp_25", "enx_large", "enx_mid", "enx_small", "xetra"],
            "etfs": ["etf_pea", "etf_fr", "etf_pea_full"],
            "funds": [],
            "indices": ["index"],
            "currencies": [],
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
            "nasdaq_tech": "NASDAQ Tech",
            "sp_25": "S&P 25",
            "enx_large": "Euronext Large Cap",
            "enx_mid": "Euronext Mid Cap",
            "enx_small": "Euronext Small Cap",
            "xetra": "Xetra (Germany)",
            "etf_pea": "ETF PEA (France)",
            "etf_fr": "French ETFs",
            "etf_pea_full": "ETF PEA (Full)",
            "index": "Major Indices",
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

    def search_tickers(self, query: str, category: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
        """Search for tickers by symbol or name across universes.

        Args:
            query: Substring to match against ticker symbol or name (case-insensitive)
            category: Optional category to restrict the search to (see get_asset_categories)
            limit: Max number of matches to return
        """
        self.logger.info(f"Searching tickers: {query}")
        query_lower = query.strip().lower()
        if not query_lower:
            return []

        universe_ids = self.universe_map.get(category, []) if category else [
            uid for ids in self.universe_map.values() for uid in ids
        ]

        seen = set()
        matches = []
        for uni_id in universe_ids:
            try:
                universe = Universe(uni_id)
                if not universe.exists():
                    continue
                for ticker_data in universe.get_tickers_with_metadata():
                    symbol = ticker_data.get("symbol", "")
                    if symbol in seen:
                        continue
                    name = ticker_data.get("name", "")
                    if query_lower in symbol.lower() or query_lower in name.lower():
                        seen.add(symbol)
                        matches.append(ticker_data)
                        if len(matches) >= limit:
                            return matches
            except Exception as e:
                self.logger.warning(f"Failed to search universe {uni_id}: {e}")

        return matches

    def get_ticker_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a ticker.

        Combines universe metadata, fundamentals, and FinanceDatabase data
        via TickerIntelligence.
        """
        self.logger.info(f"Getting info for {ticker}")
        from tools.data.enrichment import TickerIntelligence

        try:
            summary = TickerIntelligence(ticker).get_summary()
            return summary or None
        except Exception as e:
            self.logger.warning(f"Failed to get ticker info for {ticker}: {e}")
            return None
