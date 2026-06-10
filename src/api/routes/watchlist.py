"""Watchlist API endpoints."""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import pandas as pd
from datetime import datetime, timedelta

from tools.watchlist.watchlist_manager import WatchlistManager
from tools.strategy import StrategyManager
from pathlib import Path
import os


def _get_project_root() -> Path:
	"""Get project root from environment."""
	return Path(os.environ.get("CRESUS_PROJECT_ROOT", "."))


router = APIRouter(prefix="/watchlists", tags=["watchlists"])


class TickerRequest(BaseModel):
	"""Request model for adding a ticker to watchlist."""
	ticker: str


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

		# Return empty watchlist if not found instead of error
		if df is None or df.empty:
			return {
				"strategy": strategy_name,
				"watchlist": [],
				"count": 0,
				"total_score": 0,
			}

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

	except HTTPException:
		raise
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
async def get_ticker_historical(
	strategy_name: str,
	ticker: str,
	period: str = "1Y",
	days: Optional[int] = None
):
	"""Get historical OHLCV data with EMA indicators for a ticker in a watchlist.

	Verifies ticker is in the watchlist, then returns historical price data.
	Period mapping: 1W=7, 1M=30, 3M=90, YTD=year-to-date, 1Y=365, All=all available
	Includes EMA_20 and EMA_50 calculations.
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

		# Load historical data
		history = DataHistory(ticker)
		df = history.load_all()

		if df.empty:
			raise HTTPException(404, f"No historical data for {ticker}")

		# Map period to days if not explicitly provided
		if days is None:
			period_map = {
				"1W": 7,
				"1M": 30,
				"3M": 90,
				"6M": 180,
				"YTD": _get_ytd_days(),
				"1Y": 365,
				"All": None
			}
			days = period_map.get(period, 365)

		# Filter to last N days
		if days is not None:
			df = df.tail(days)

		# Normalize column names to lowercase for consistency
		df.columns = df.columns.str.lower()

		# Calculate indicators using centralized indicators module
		if 'close' in df.columns:
			from tools.indicators.indicators import calculate

			try:
				# Calculate EMA_20 and EMA_50 using indicators module
				indicators_result = calculate(['ema_20', 'ema_50'], df)
				for ind_name, ind_series in indicators_result.items():
					df[ind_name] = ind_series.values
			except Exception as e:
				# Fall back to direct calculation if indicators fail
				from loguru import logger
				logger.warning(f"Indicator calculation failed for {ticker}: {e}, using fallback")
				close = pd.to_numeric(df['close'], errors='coerce')
				df['ema_20'] = close.ewm(span=20, adjust=False).mean()
				df['ema_50'] = close.ewm(span=50, adjust=False).mean()

		# Convert to list of dicts
		records = []
		for idx, row in df.iterrows():
			record = {}
			for col in df.columns:
				value = row[col]
				if pd.isna(value):
					record[col] = None
				elif col == 'volume':
					record[col] = int(value)
				elif col in ['open', 'high', 'low', 'close', 'ema_20', 'ema_50']:
					record[col] = float(value)
				else:
					record[col] = str(value)

			# Add date field formatted as YYYY-MM-DD from timestamp
			if 'timestamp' in record and record['timestamp']:
				try:
					ts = pd.Timestamp(record['timestamp'])
					record['date'] = ts.strftime('%Y-%m-%d')
				except:
					record['date'] = record['timestamp']

			records.append(record)

		return {
			"ticker": ticker,
			"strategy": strategy_name,
			"period": period,
			"data": records,
			"count": len(records),
		}

	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(500, f"Error loading historical data: {str(e)}")


@router.post("/{strategy_name}/add")
async def add_ticker_to_watchlist(strategy_name: str, body: TickerRequest = Body(...)):
	"""Add a ticker to a watchlist."""
	try:
		ticker = body.ticker
		manager = WatchlistManager(strategy_name)

		# Load current watchlist
		df = manager.load()

		# Create new row with just ticker
		if df is not None and not df.empty:
			# If watchlist exists, check columns
			new_row = {col: None for col in df.columns}
		else:
			# Create minimal row with just ticker
			new_row = {'ticker': ticker}

		new_row['ticker'] = ticker

		# Add to watchlist
		if df is None or df.empty:
			# Create new watchlist
			df = pd.DataFrame([new_row])
		else:
			# Check if ticker already exists
			if ticker not in df['ticker'].values:
				# Add new row to existing watchlist
				df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
			else:
				# Ticker already exists
				return {"success": False, "message": f"Ticker {ticker} already in {strategy_name} watchlist"}

		# Save watchlist directly to CSV (bypass WatchlistManager.save which needs complex params)
		watchlist_dir = _get_project_root() / "db" / "local" / "watchlist"
		print(f"[Watchlist] Project root: {_get_project_root()}")
		print(f"[Watchlist] Watchlist dir: {watchlist_dir}")
		print(f"[Watchlist] Creating directory...")
		watchlist_dir.mkdir(parents=True, exist_ok=True)
		print(f"[Watchlist] Directory created")
		filepath = watchlist_dir / f"{strategy_name}.csv"
		print(f"[Watchlist] File path: {filepath}")
		print(f"[Watchlist] DataFrame shape: {df.shape}")
		print(f"[Watchlist] Saving CSV...")
		df.to_csv(filepath, index=False)
		print(f"[Watchlist] CSV saved successfully")
		print(f"[Watchlist] File exists: {filepath.exists()}")

		return {"success": True, "message": f"Added {ticker} to {strategy_name} watchlist"}
	except Exception as e:
		raise HTTPException(500, f"Error adding ticker to watchlist: {str(e)}")


@router.delete("/{strategy_name}/{ticker}")
async def remove_ticker_from_watchlist(strategy_name: str, ticker: str):
	"""Remove a ticker from a watchlist."""
	try:
		manager = WatchlistManager(strategy_name)
		df = manager.load()

		if df is None or df.empty:
			raise HTTPException(404, f"Watchlist '{strategy_name}' not found")

		# Check if ticker exists
		if ticker not in df['ticker'].values:
			raise HTTPException(404, f"Ticker '{ticker}' not found in watchlist '{strategy_name}'")

		# Remove ticker
		df = df[df['ticker'] != ticker]

		# Save watchlist directly to CSV
		watchlist_dir = _get_project_root() / "db" / "local" / "watchlist"
		filepath = watchlist_dir / f"{strategy_name}.csv"

		if df.empty:
			# Delete watchlist file if no tickers left
			if filepath.exists():
				filepath.unlink()
		else:
			df.to_csv(filepath, index=False)

		return {"success": True, "message": f"Removed {ticker} from {strategy_name} watchlist"}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(500, f"Error removing ticker from watchlist: {str(e)}")


def _get_ytd_days() -> int:
	"""Calculate days from start of year to today."""
	today = datetime.now().date()
	year_start = datetime(today.year, 1, 1).date()
	return (today - year_start).days
