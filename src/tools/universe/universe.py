"""Universe management for ticker lists."""

from pathlib import Path
from typing import List, Optional, Dict, Any
import pandas as pd
import os

from utils.env import get_db_root
from .blacklist import get_blacklist


class Universe:
    """Load and manage ticker universes (market lists)."""

    def __init__(self, universe_name: str):
        """Initialize Universe loader.

        Args:
            universe_name: Name of the universe (e.g., 'cac40', 'nasdaq_100')
        """
        self.universe_name = universe_name.lower()
        self.filepath = get_db_root() / "universes" / f"{self.universe_name}.csv"

    def exists(self) -> bool:
        """Check if universe file exists."""
        return self.filepath.exists()

    def get_tickers(self) -> List[str]:
        """Get list of ticker symbols from universe.

        Uses TickerYahoo column if available, otherwise falls back to ISIN.
        Automatically excludes blacklisted tickers.

        Returns:
            List of ticker symbols or ISINs (excluding blacklisted)
        """
        if not self.exists():
            raise FileNotFoundError(f"Universe '{self.universe_name}' not found")

        try:
            df = self.load_df()
            blacklist = get_blacklist()
            blacklisted_tickers = blacklist.get_tickers()

            # Try TickerYahoo first (preferred)
            if "TickerYahoo" in df.columns:
                tickers = df["TickerYahoo"].dropna().str.strip().tolist()
                # Filter empty strings and blacklisted tickers
                return [t for t in tickers if t and t.upper() not in blacklisted_tickers]

            # Fallback to ISIN if TickerYahoo not available
            if "ISIN" in df.columns:
                isins = df["ISIN"].dropna().str.strip().tolist()
                # Filter empty strings and blacklisted ISINs
                return [i for i in isins if i and i.upper() not in blacklisted_tickers]

            # If neither column exists, raise error
            raise ValueError(f"Universe file missing both 'TickerYahoo' and 'ISIN' columns")

        except pd.errors.ParserError as e:
            raise ValueError(f"Error parsing universe file '{self.universe_name}': {e}")
        except Exception as e:
            raise ValueError(f"Error reading universe '{self.universe_name}': {e}")

    def load_df(self) -> pd.DataFrame:
        """Load universe as DataFrame.

        Automatically detects separator (comma or semicolon).
        """
        if not self.exists():
            raise FileNotFoundError(f"Universe '{self.universe_name}' not found")

        # Try to detect separator
        with open(self.filepath, 'r', encoding='utf-8-sig') as f:
            first_line = f.readline()

        separator = ',' if ',' in first_line else ';'
        return pd.read_csv(self.filepath, sep=separator, encoding='utf-8-sig')

    @staticmethod
    def list_universes() -> List[str]:
        """List all available universes."""
        universes_dir = get_db_root() / "universes"

        if not universes_dir.exists():
            return []

        universes = [f.stem for f in universes_dir.glob("*.csv")]
        return sorted(universes)

    @staticmethod
    def get_universe_info(universe_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a universe."""
        try:
            u = Universe(universe_name)
            if not u.exists():
                return None

            df = u.load_df()
            tickers = u.get_tickers()

            return {
                "name": universe_name,
                "count": len(tickers),
                "file_size_kb": u.filepath.stat().st_size / 1024,
                "columns": df.columns.tolist(),
                "path": str(u.filepath),
            }
        except Exception as e:
            return None
