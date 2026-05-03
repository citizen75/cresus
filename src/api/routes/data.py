"""Data API endpoints for historical OHLCV data."""

from fastapi import APIRouter, HTTPException
from typing import Optional
import pandas as pd

from tools.data import DataHistory

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/history/{ticker}")
async def get_ticker_history(
    ticker: str,
    days: Optional[int] = 365,
    columns: Optional[str] = None
):
	"""Get historical OHLCV data for a ticker.

	Returns historical price data from cache.

	Args:
		ticker: Stock ticker symbol (e.g., AAPL, STMPA.PA)
		days: Number of days of history to return (default 365)
		columns: Comma-separated list of columns to return (default: all)
				 Available: timestamp, open, high, low, close, volume

	Returns:
		Historical data with OHLCV values
	"""
	try:
		# Load historical data
		history = DataHistory(ticker)
		df = history.load_all()

		if df.empty:
			raise HTTPException(404, f"No historical data for {ticker}")

		# Filter to last N days
		if days and days > 0:
			df = df.tail(days)

		# Select specific columns if requested
		if columns:
			requested_cols = [col.strip().lower() for col in columns.split(',')]
			available_cols = [col for col in requested_cols if col in df.columns]
			if available_cols:
				df = df[available_cols]

		# Convert to list of dicts, handling NaN values
		records = []
		for _, row in df.iterrows():
			record = {}
			for col in df.columns:
				value = row[col]
				if pd.isna(value):
					record[col] = None
				elif col == 'volume':
					record[col] = int(value)
				elif col in ['open', 'high', 'low', 'close']:
					record[col] = float(value)
				else:
					record[col] = str(value)
			records.append(record)

		return {
			"ticker": ticker,
			"count": len(records),
			"days": days,
			"data": records,
		}

	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(500, f"Error loading historical data: {str(e)}")


@router.get("/history/{ticker}/latest")
async def get_ticker_latest(ticker: str):
	"""Get the latest OHLCV data point for a ticker."""
	try:
		history = DataHistory(ticker)
		df = history.load_all()

		if df.empty:
			raise HTTPException(404, f"No historical data for {ticker}")

		latest = df.iloc[-1]

		record = {}
		for col in df.columns:
			value = latest[col]
			if pd.isna(value):
				record[col] = None
			elif col == 'volume':
				record[col] = int(value)
			elif col in ['open', 'high', 'low', 'close']:
				record[col] = float(value)
			else:
				record[col] = str(value)

		return {
			"ticker": ticker,
			"latest": record,
		}

	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(500, f"Error loading historical data: {str(e)}")
