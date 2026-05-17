"""Data API endpoints for historical OHLCV data."""

from fastapi import APIRouter, HTTPException
from typing import Optional
import pandas as pd

from tools.data import DataHistory, Fundamental
from tools.universe import Universe
from tools.indicators import calculate as calculate_indicators

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/universes")
async def list_universes():
	"""List all available universes."""
	try:
		universes = Universe.list_universes()
		return {"universes": universes}
	except Exception as e:
		raise HTTPException(500, f"Error listing universes: {str(e)}")


@router.get("/history")
async def get_history_by_query(
    ticker: str,
    days: Optional[int] = 365,
    columns: Optional[str] = None
):
	"""Get historical OHLCV data for a ticker (query parameter version).

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
		records = df.to_dict(orient='records')
		for record in records:
			for col in record:
				value = record[col]
				if pd.isna(value):
					record[col] = None
				elif col == 'volume':
					record[col] = int(value) if not pd.isna(value) else None
				elif col in ['open', 'high', 'low', 'close']:
					record[col] = float(value) if not pd.isna(value) else None

		return {
			"ticker": ticker,
			"count": len(records),
			"days": days,
			"history": records,
		}

	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(500, f"Error loading historical data: {str(e)}")


@router.get("/history/{ticker}")
async def get_ticker_history(
    ticker: str,
    days: Optional[int] = 365,
    columns: Optional[str] = None,
    indicator: Optional[str] = None
):
	"""Get historical OHLCV data for a ticker with optional indicators.

	Returns historical price data from cache, optionally with calculated indicators.

	Args:
		ticker: Stock ticker symbol (e.g., AAPL, STMPA.PA)
		days: Number of days of history to return (default 365)
		columns: Comma-separated list of columns to return (default: all)
				 Available: timestamp, open, high, low, close, volume
		indicator: Indicator to calculate and include (e.g., sha_10, ema_20, rsi_14)

	Returns:
		Historical data with OHLCV values and optional indicator columns
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

		# Calculate indicator if requested
		if indicator:
			try:
				# Sort in ascending order (oldest first) for indicator calculation
				df_for_calc = df.sort_values('timestamp', ascending=True).reset_index(drop=True)

				# Normalize column names to lowercase for indicator calculation
				df_normalized = df_for_calc.copy()
				column_mapping = {}
				for col in df_normalized.columns:
					col_lower = col.lower()
					if col_lower in ['open', 'high', 'low', 'close', 'volume']:
						column_mapping[col] = col_lower
				df_normalized = df_normalized.rename(columns=column_mapping)

				indicator_lower = indicator.lower()

				# Expand multi-component indicators (sha, bb, macd, etc)
				# to include all components needed for candlestick or other visualizations
				indicators_to_calculate = [indicator_lower]

				# For candlestick indicators, include OHLC components
				if indicator_lower.startswith('sha'):
					indicators_to_calculate = [
						f"{indicator_lower}_open",
						f"{indicator_lower}_high",
						f"{indicator_lower}_low",
						f"{indicator_lower}_close",
					]
				elif indicator_lower.startswith('bb'):  # Bollinger Bands
					indicators_to_calculate = [
						f"{indicator_lower}_upper",
						f"{indicator_lower}_middle",
						f"{indicator_lower}_lower",
					]
				elif indicator_lower.startswith('macd'):  # MACD
					indicators_to_calculate = [
						f"{indicator_lower}_line",
						f"{indicator_lower}_signal",
						f"{indicator_lower}_histogram",
					]
				elif indicator_lower.startswith('dmi'):  # DMI
					indicators_to_calculate = [
						f"{indicator_lower}_plus",
						f"{indicator_lower}_minus",
					]

				# Calculate indicator using DSL formula on normalized dataframe
				indicator_results = calculate_indicators(indicators_to_calculate, df_normalized)

				# Create a mapping of timestamp -> indicator values for proper merging
				for col_name, col_data in indicator_results.items():
					# Create a dictionary mapping timestamp to value
					ts_value_map = dict(zip(df_for_calc['timestamp'], col_data))
					# Apply values to original df using timestamp lookup
					df[col_name] = df['timestamp'].map(ts_value_map)
			except Exception as e:
				from loguru import logger
				import traceback
				logger.error(f"Indicator calc failed for {ticker} {indicator}: {str(e)}\n{traceback.format_exc()}")
				raise HTTPException(400, f"Error calculating indicator '{indicator}': {str(e)}")

		# Select specific columns if requested
		if columns:
			requested_cols = [col.strip().lower() for col in columns.split(',')]
			available_cols = [col for col in requested_cols if col in df.columns]
			if available_cols:
				df = df[available_cols]

		# Convert to list of dicts, handling NaN values
		records = df.to_dict(orient='records')
		for record in records:
			for col in record:
				value = record[col]
				if pd.isna(value):
					record[col] = None
				elif col == 'volume':
					record[col] = int(value) if not pd.isna(value) else None
				elif col in ['open', 'high', 'low', 'close']:
					record[col] = float(value) if not pd.isna(value) else None
				elif isinstance(value, (int, float)) and not pd.isna(value):
					record[col] = float(value)

		return {
			"ticker": ticker,
			"count": len(records),
			"days": days,
			"indicator": indicator,
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


@router.get("/fundamental/{ticker}")
async def get_ticker_fundamental(ticker: str):
	"""Get fundamental data for a ticker (current price, bid/ask, etc).

	Fetches latest fundamental data from cache or yfinance.
	Returns quotation data including current price, bid, ask.
	"""
	try:
		fundamental = Fundamental(ticker)
		data = fundamental.fetch()

		if data.get("status") == "error":
			raise HTTPException(500, f"Error fetching fundamental data: {data.get('message')}")

		return data

	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(500, f"Error loading fundamental data: {str(e)}")


@router.post("/cache/refresh")
async def refresh_portfolio_cache():
	"""Manually trigger refresh of fundamental data for all portfolio tickers.

	This endpoint fetches and caches fundamental data for all tickers in real portfolios.
	Useful for manual updates or testing the cron job.

	Returns:
		Cache refresh results
	"""
	try:
		from tools.portfolio.manager import PortfolioManager
		pm = PortfolioManager()
		result = pm.fetch_all_ticker_data(days=365)
		return {
			"status": "success",
			"message": f"Cache refresh complete: {result['tickers_processed']}/{result['tickers_total']} tickers updated",
			**result,
		}
	except Exception as e:
		raise HTTPException(500, f"Error refreshing cache: {str(e)}")
