"""Watchlist API endpoints."""

from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any
import pandas as pd

from tools.watchlist import WatchlistManager
from tools.strategy import StrategyManager
from pathlib import Path
import os


def _get_project_root() -> Path:
	"""Get project root from environment."""
	return Path(os.environ.get("CRESUS_PROJECT_ROOT", "."))


router = APIRouter(prefix="/watchlists", tags=["watchlists"])


@router.get("")
async def list_watchlists():
	"""List all saved watchlists."""
	project_root = _get_project_root()
	watchlist_dir = project_root / "db" / "local" / "watchlist"

	if not watchlist_dir.exists():
		return {"watchlists": [], "count": 0}

	watchlists = [f.stem for f in watchlist_dir.glob("*.csv")]
	return {"watchlists": watchlists, "count": len(watchlists)}


@router.get("/{strategy_name}")
async def get_watchlist(strategy_name: str, limit: Optional[int] = None):
	"""Get watchlist data for a strategy.

	Returns watchlist with OHLCV data and signal scores.
	If limit is specified, returns top N tickers by signal score.
	"""
	try:
		manager = WatchlistManager(strategy_name)
		df = manager.load()

		if df is None or df.empty:
			raise HTTPException(404, f"Watchlist '{strategy_name}' not found")

		# Sort by signal_score descending
		df = df.sort_values('signal_score', ascending=False)

		# Apply limit if specified
		if limit and limit > 0:
			df = df.head(limit)

		# Convert to list of dicts for JSON response
		records = df.to_dict('records')

		# Convert NaN to None for JSON serialization
		for record in records:
			for key, value in record.items():
				if pd.isna(value):
					record[key] = None

		return {
			"strategy": strategy_name,
			"watchlist": records,
			"count": len(records),
			"total_score": float(df['signal_score'].sum()) if not df.empty else 0,
		}

	except Exception as e:
		raise HTTPException(500, f"Error loading watchlist: {str(e)}")


@router.get("/{strategy_name}/top")
async def get_top_watchlist_tickers(strategy_name: str, n: int = 10):
	"""Get top N tickers from watchlist by signal score."""
	try:
		manager = WatchlistManager(strategy_name)
		top_tickers = manager.get_top_tickers(n)

		if not top_tickers:
			raise HTTPException(404, f"Watchlist '{strategy_name}' not found")

		return {
			"strategy": strategy_name,
			"top_tickers": top_tickers,
			"count": len(top_tickers),
		}

	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(500, f"Error loading watchlist: {str(e)}")


@router.get("/{strategy_name}/tickers")
async def get_watchlist_tickers(strategy_name: str):
	"""Get list of ticker symbols from watchlist."""
	try:
		manager = WatchlistManager(strategy_name)
		tickers = manager.list_tickers()

		if tickers is None:
			raise HTTPException(404, f"Watchlist '{strategy_name}' not found")

		return {
			"strategy": strategy_name,
			"tickers": tickers,
			"count": len(tickers),
		}

	except Exception as e:
		raise HTTPException(500, f"Error loading watchlist: {str(e)}")
