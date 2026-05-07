"""Blacklist management for filtering out invalid/delisted tickers."""

from pathlib import Path
from typing import Set, Optional
import pandas as pd

from utils.env import get_db_root


class Blacklist:
    """Manage ticker blacklist to exclude invalid/delisted securities."""

    def __init__(self):
        """Initialize blacklist loader."""
        self.filepath = get_db_root() / "universes" / "blacklist.csv"
        self._tickers: Optional[Set[str]] = None

    def exists(self) -> bool:
        """Check if blacklist file exists."""
        return self.filepath.exists()

    def get_tickers(self) -> Set[str]:
        """Get set of blacklisted tickers.

        Returns:
            Set of blacklisted ticker symbols (uppercase)
        """
        if self._tickers is None:
            self._tickers = self._load_tickers()
        return self._tickers

    def _load_tickers(self) -> Set[str]:
        """Load blacklisted tickers from CSV.

        Returns:
            Set of ticker symbols (converted to uppercase)
        """
        if not self.exists():
            return set()

        try:
            df = pd.read_csv(self.filepath, keep_default_na=False, na_values=[])

            # Get tickers from 'ticker' column
            if "ticker" in df.columns:
                tickers = df["ticker"].dropna().str.strip().str.upper().tolist()
                return set(t for t in tickers if t)  # Filter empty strings

            return set()

        except Exception as e:
            # Log warning but don't fail - blacklist is optional
            print(f"Warning: Failed to load blacklist: {e}")
            return set()

    def is_blacklisted(self, ticker: str) -> bool:
        """Check if a ticker is blacklisted.

        Args:
            ticker: Ticker symbol to check

        Returns:
            True if ticker is blacklisted, False otherwise
        """
        return ticker.upper() in self.get_tickers()

    def add_ticker(self, ticker: str, reason: str = "User blacklist") -> None:
        """Add a ticker to the blacklist.

        Args:
            ticker: Ticker symbol to blacklist
            reason: Reason for blacklisting
        """
        if not self.exists():
            # Create new blacklist file
            df = pd.DataFrame({
                "ticker": [ticker.upper()],
                "reason": [reason],
                "date_added": [pd.Timestamp.now().date().isoformat()]
            })
        else:
            # Load existing and append
            df = pd.read_csv(self.filepath, keep_default_na=False, na_values=[])
            new_row = pd.DataFrame({
                "ticker": [ticker.upper()],
                "reason": [reason],
                "date_added": [pd.Timestamp.now().date().isoformat()]
            })
            df = pd.concat([df, new_row], ignore_index=True)

        # Save and invalidate cache
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.filepath, index=False)
        self._tickers = None  # Invalidate cache

    def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker from the blacklist.

        Args:
            ticker: Ticker symbol to remove
        """
        if not self.exists():
            return

        df = pd.read_csv(self.filepath, keep_default_na=False, na_values=[])
        df = df[df["ticker"].str.upper() != ticker.upper()]
        df.to_csv(self.filepath, index=False)
        self._tickers = None  # Invalidate cache


# Global singleton instance
_blacklist_instance: Optional[Blacklist] = None


def get_blacklist() -> Blacklist:
    """Get or create blacklist singleton instance."""
    global _blacklist_instance
    if _blacklist_instance is None:
        _blacklist_instance = Blacklist()
    return _blacklist_instance
