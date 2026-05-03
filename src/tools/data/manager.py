"""Data management commands for historical and fundamental data."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.data.core import DataHistory, Fundamental
from tools.universe.universe import Universe


class DataManager:
    """Manage historical and fundamental data cache."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        os.environ["CRESUS_PROJECT_ROOT"] = str(project_root)
        self.cache_dir = project_root / "db" / "local" / "cache"
        self.history_dir = self.cache_dir / "history"
        self.fundamentals_dir = self.cache_dir / "fundamentals"

    def fetch_history(self, ticker: str, start_date: Optional[str] = None) -> Dict[str, Any]:
        """Fetch historical data for a ticker from yfinance."""
        try:
            dh = DataHistory(ticker.upper())
            result = dh.fetch(start_date=start_date, incremental=True)
            if result.get("status") == "success":
                df = dh.get_all()
                return {
                    "status": "success",
                    "ticker": ticker.upper(),
                    "rows": len(df),
                    "message": f"Fetched {len(df)} rows for {ticker.upper()}",
                }
            else:
                return {
                    "status": "error",
                    "ticker": ticker.upper(),
                    "message": result.get("message", "Unknown error"),
                }
        except Exception as e:
            return {
                "status": "error",
                "ticker": ticker.upper(),
                "message": str(e),
            }

    def fetch_fundamental(self, ticker: str) -> Dict[str, Any]:
        """Fetch fundamental data for a ticker from yfinance."""
        try:
            fd = Fundamental(ticker.upper())
            result = fd.fetch()
            if result.get("status") == "success":
                return {
                    "status": "success",
                    "ticker": ticker.upper(),
                    "message": f"Fetched fundamental data for {ticker.upper()}",
                    "data": result.get("data"),
                }
            else:
                return {
                    "status": "error",
                    "ticker": ticker.upper(),
                    "message": result.get("message", "Unknown error"),
                }
        except Exception as e:
            return {
                "status": "error",
                "ticker": ticker.upper(),
                "message": str(e),
            }

    def fetch_universe(self, universe_name: str, start_date: str = None) -> Dict[str, Any]:
        """Fetch historical data for all tickers in a universe."""
        try:
            universe = Universe(universe_name)
            if not universe.exists():
                return {
                    "status": "error",
                    "message": f"Universe '{universe_name}' not found",
                    "available": Universe.list_universes(),
                }

            tickers = universe.get_tickers()
            if not tickers:
                return {
                    "status": "error",
                    "message": f"No tickers found in universe '{universe_name}'",
                }

            results = {
                "status": "success",
                "universe": universe_name,
                "total": len(tickers),
                "fetched": 0,
                "failed": 0,
                "details": [],
            }

            for ticker in tickers:
                result = self.fetch_history(ticker, start_date)
                if result.get("status") == "success":
                    results["fetched"] += 1
                else:
                    results["failed"] += 1
                results["details"].append({
                    "ticker": ticker,
                    "status": result.get("status"),
                    "rows": result.get("rows", 0),
                })

            results["message"] = f"Fetched {results['fetched']}/{results['total']} tickers from {universe_name}"
            return results
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
            }

    def list_cached(self, data_type: str = "all") -> Dict[str, Any]:
        """List cached data files."""
        try:
            result = {"status": "success", "history": [], "fundamentals": []}

            if data_type in ("history", "all"):
                if self.history_dir.exists():
                    files = list(self.history_dir.glob("*.parquet"))
                    result["history"] = [
                        {
                            "ticker": f.stem,
                            "size_kb": f.stat().st_size / 1024,
                            "modified": f.stat().st_mtime,
                        }
                        for f in files
                    ]

            if data_type in ("fundamentals", "all"):
                if self.fundamentals_dir.exists():
                    files = list(self.fundamentals_dir.glob("*.json"))
                    result["fundamentals"] = [
                        {
                            "ticker": f.stem,
                            "size_kb": f.stat().st_size / 1024,
                            "modified": f.stat().st_mtime,
                        }
                        for f in files
                    ]

            result["total_history"] = len(result["history"])
            result["total_fundamentals"] = len(result["fundamentals"])
            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def clear_cache(self, data_type: str = "all", ticker: Optional[str] = None) -> Dict[str, Any]:
        """Clear cached data."""
        try:
            cleared = {"history": 0, "fundamentals": 0}

            if ticker:
                ticker = ticker.upper()
                if data_type in ("history", "all"):
                    f = self.history_dir / f"{ticker}.parquet"
                    if f.exists():
                        f.unlink()
                        cleared["history"] = 1
                if data_type in ("fundamentals", "all"):
                    f = self.fundamentals_dir / f"{ticker}.json"
                    if f.exists():
                        f.unlink()
                        cleared["fundamentals"] = 1
                return {
                    "status": "success",
                    "message": f"Cleared cache for {ticker}",
                    "cleared": cleared,
                }
            else:
                # Clear all
                if data_type in ("history", "all"):
                    if self.history_dir.exists():
                        for f in self.history_dir.glob("*.parquet"):
                            f.unlink()
                            cleared["history"] += 1
                if data_type in ("fundamentals", "all"):
                    if self.fundamentals_dir.exists():
                        for f in self.fundamentals_dir.glob("*.json"):
                            f.unlink()
                            cleared["fundamentals"] += 1
                return {
                    "status": "success",
                    "message": f"Cleared {data_type} cache",
                    "cleared": cleared,
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def cache_stats(self) -> Dict[str, Any]:
        """Show cache statistics."""
        try:
            history_count = 0
            history_size = 0
            fundamentals_count = 0
            fundamentals_size = 0

            if self.history_dir.exists():
                for f in self.history_dir.glob("*.parquet"):
                    history_count += 1
                    history_size += f.stat().st_size

            if self.fundamentals_dir.exists():
                for f in self.fundamentals_dir.glob("*.json"):
                    fundamentals_count += 1
                    fundamentals_size += f.stat().st_size

            return {
                "status": "success",
                "history": {
                    "count": history_count,
                    "size_mb": round(history_size / (1024 * 1024), 2),
                    "path": str(self.history_dir),
                },
                "fundamentals": {
                    "count": fundamentals_count,
                    "size_mb": round(fundamentals_size / (1024 * 1024), 2),
                    "path": str(self.fundamentals_dir),
                },
                "total_size_mb": round((history_size + fundamentals_size) / (1024 * 1024), 2),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
