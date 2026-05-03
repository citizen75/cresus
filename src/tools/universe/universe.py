"""Universe management for ticker lists."""

from pathlib import Path
from typing import List, Optional, Dict, Any
import pandas as pd
import os


class Universe:
    """Load and manage ticker universes (market lists)."""

    def __init__(self, universe_name: str):
        """Initialize Universe loader.

        Args:
            universe_name: Name of the universe (e.g., 'cac40', 'nasdaq_100')
        """
        self.universe_name = universe_name.lower()
        project_root = Path(os.environ.get("CRESUS_PROJECT_ROOT", os.getcwd()))
        self.filepath = project_root / "db" / "global" / "list" / f"{self.universe_name}.csv"

    def exists(self) -> bool:
        """Check if universe file exists."""
        return self.filepath.exists()

    def get_tickers(self) -> List[str]:
        """Get list of ticker symbols from universe.

        Returns:
            List of ticker symbols (TickerYahoo column)
        """
        if not self.exists():
            raise FileNotFoundError(f"Universe '{self.universe_name}' not found")

        try:
            df = pd.read_csv(self.filepath)
            if "TickerYahoo" not in df.columns:
                raise ValueError(f"Universe file missing 'TickerYahoo' column")

            tickers = df["TickerYahoo"].dropna().str.strip().tolist()
            return [t for t in tickers if t]  # Filter empty strings
        except Exception as e:
            raise ValueError(f"Error reading universe '{self.universe_name}': {e}")

    def load_df(self) -> pd.DataFrame:
        """Load universe as DataFrame."""
        if not self.exists():
            raise FileNotFoundError(f"Universe '{self.universe_name}' not found")
        return pd.read_csv(self.filepath)

    @staticmethod
    def list_universes() -> List[str]:
        """List all available universes."""
        project_root = Path(os.environ.get("CRESUS_PROJECT_ROOT", os.getcwd()))
        list_dir = project_root / "db" / "global" / "list"

        if not list_dir.exists():
            return []

        universes = [f.stem for f in list_dir.glob("*.csv")]
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
