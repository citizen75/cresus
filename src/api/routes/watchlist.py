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


@router.get("/{strategy_name}/historical/{ticker}")
async def get_ticker_historical(strategy_name: str, ticker: str, days: int = 365):
	"""Get historical OHLCV data for a ticker.

	Returns historical price data (1 year by default) for a ticker in a watchlist.
	"""
	try:
		from tools.data import DataHistory

		# Verify ticker is in the watchlist
		manager = WatchlistManager(strategy_name)
		watchlist_tickers = manager.list_tickers()

		if not watchlist_tickers:
			raise HTTPException(404, f"Watchlist '{strategy_name}' not found")

		if ticker not in watchlist_tickers:
			raise HTTPException(404, f"Ticker '{ticker}' not in watchlist '{strategy_name}'")

		# Fetch historical data
		history = DataHistory(ticker)
		df = history.load_all()

		if df.empty:
			raise HTTPException(404, f"No historical data for {ticker}")

		# Filter to last N days
		df = df.tail(days)

		# Convert to list of dicts
		records = []
		for _, row in df.iterrows():
			date = row.get('timestamp', row.name)
			if pd.notna(date):
				records.append({
					'date': str(date).split(' ')[0],  # Just the date part
					'open': float(row['open']) if pd.notna(row.get('open')) else None,
					'high': float(row['high']) if pd.notna(row.get('high')) else None,
					'low': float(row['low']) if pd.notna(row.get('low')) else None,
					'close': float(row['close']) if pd.notna(row.get('close')) else None,
					'volume': int(row['volume']) if pd.notna(row.get('volume')) else None,
				})

		if not records:
			raise HTTPException(404, f"No historical data available for {ticker}")

		return {
			"ticker": ticker,
			"strategy": strategy_name,
			"historical_data": records,
			"count": len(records),
			"days": days,
		}

	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(500, f"Error loading historical data: {str(e)}")
