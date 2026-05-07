"""Portfolio cache manager - stores latest metrics in ~/.cresus/db/portfolios.json"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import os
from loguru import logger

from utils.env import get_db_root


class PortfolioCache:
    """Manage cached portfolio metrics."""

    def __init__(self, cache_path: Optional[Path] = None, context: Optional[Dict[str, Any]] = None):
        # Check if running in backtest context
        backtest_dir = None
        if context:
            backtest_dir = context.get("backtest_dir")

        if backtest_dir:
            # Use sandboxed backtest directory
            self.cache_path = Path(backtest_dir) / "portfolios.json"
        else:
            # Use normal directory
            self.cache_path = Path(cache_path or get_db_root() / "portfolios.json")

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from file."""
        if not self.cache_path.exists():
            return {"portfolios": {}, "updated_at": None}

        try:
            with open(self.cache_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            return {"portfolios": {}, "updated_at": None}

    def _save_cache(self, cache: Dict[str, Any]) -> None:
        """Save cache to file."""
        try:
            with open(self.cache_path, "w") as f:
                json.dump(cache, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def update_portfolio(self, name: str, data: Dict[str, Any]) -> None:
        """Update portfolio metrics in cache."""
        cache = self._load_cache()

        # Ensure portfolios key exists
        if "portfolios" not in cache:
            cache["portfolios"] = {}

        # Update portfolio data with timestamp
        cache["portfolios"][name] = {
            **data,
            "updated_at": datetime.now().isoformat(),
        }

        # Update global timestamp
        cache["updated_at"] = datetime.now().isoformat()

        self._save_cache(cache)
        logger.debug(f"Updated cache for portfolio '{name}'")

    def get_portfolio(self, name: str) -> Optional[Dict[str, Any]]:
        """Get cached portfolio data."""
        cache = self._load_cache()
        return cache.get("portfolios", {}).get(name)

    def get_all_portfolios(self) -> Dict[str, Any]:
        """Get all cached portfolios."""
        cache = self._load_cache()
        return cache.get("portfolios", {})

    def delete_portfolio(self, name: str) -> None:
        """Remove portfolio from cache."""
        cache = self._load_cache()
        if "portfolios" in cache and name in cache["portfolios"]:
            del cache["portfolios"][name]
            cache["updated_at"] = datetime.now().isoformat()
            self._save_cache(cache)
            logger.debug(f"Removed '{name}' from cache")

    def clear_cache(self) -> None:
        """Clear entire cache."""
        self._save_cache({"portfolios": {}, "updated_at": datetime.now().isoformat()})
        logger.info("Cleared portfolio cache")
