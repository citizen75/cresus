"""Data fetching and caching for portfolio management.

Fundamental data (current prices) and historical OHLCV data via yfinance.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
import os

import pandas as pd
import yfinance as yf
from loguru import logger


def _get_project_root() -> Path:
	"""Get project root from CRESUS_PROJECT_ROOT env var or current working directory."""
	return Path(os.environ.get("CRESUS_PROJECT_ROOT", os.getcwd()))


class Fundamental:
	"""Fetch and cache fundamental data via yfinance."""

	def __init__(self, ticker: str):
		self.ticker = ticker.upper()
		project_root = _get_project_root()
		self.cache_dir = project_root / "db" / "local" / "cache" / "fundamentals"
		self.cache_dir.mkdir(parents=True, exist_ok=True)
		self.filepath = self.cache_dir / f"{self.ticker}.json"

	def load(self) -> Optional[Dict[str, Any]]:
		"""Load cached fundamental data if it exists."""
		try:
			if self.filepath.exists():
				with open(self.filepath) as f:
					return json.load(f)
		except Exception as e:
			logger.warning(f"Error loading fundamental cache for {self.ticker}: {e}")
		return None

	def fetch(self) -> Dict[str, Any]:
		"""Fetch latest fundamental data from yfinance and cache it."""
		try:
			logger.info(f"Fetching fundamental data for {self.ticker}")
			ticker_obj = yf.Ticker(self.ticker)
			info = ticker_obj.info or {}

			# Extract current price with fallback chain
			current_price = None
			for key in ["currentPrice", "regularMarketPrice", "previousClose"]:
				price = info.get(key)
				if price and price > 0:
					current_price = float(price)
					break

			if not current_price:
				bid = info.get("bid") or 0
				ask = info.get("ask") or 0
				if bid and ask:
					current_price = (bid + ask) / 2
				elif bid:
					current_price = bid
				elif ask:
					current_price = ask

			# Extract analyst data
			target_price = info.get("targetMeanPrice") or info.get("targetPrice")
			recommendation = info.get("recommendationKey")
			analyst_count = info.get("numberOfAnalystRatings", 0)

			# Map recommendation key to readable format
			recommendation_map = {
				"strong_buy": "Strong Buy",
				"buy": "Buy",
				"hold": "Hold",
				"sell": "Sell",
				"strong_sell": "Strong Sell",
			}

			data = {
				"ticker": self.ticker,
				"status": "success",
				"data": {
					"quotation": {
						"current_price": current_price,
						"previous_close": info.get("previousClose"),
						"bid": info.get("bid"),
						"ask": info.get("ask"),
					},
					"company": {
						"name": info.get("longName") or info.get("shortName") or self.ticker,
						"sector": info.get("sector"),
						"industry": info.get("industry"),
					},
					"analysts": {
						"target_price": target_price,
						"recommendation": recommendation_map.get(recommendation, recommendation),
						"analyst_count": analyst_count,
						"upside_potential": ((target_price - current_price) / current_price * 100) if target_price and current_price else None,
					}
				},
				"timestamp": datetime.now().isoformat(),
			}

			# Cache it
			with open(self.filepath, "w") as f:
				json.dump(data, f)

			logger.info(f"Cached fundamental data for {self.ticker}")
			return data

		except Exception as e:
			logger.error(f"Error fetching fundamental data for {self.ticker}: {e}")
			return {
				"ticker": self.ticker,
				"status": "error",
				"message": str(e),
			}

	def get_current_price(self) -> Optional[float]:
		"""Get current price from cache or fetch."""
		cached = self.load()
		if cached:
			price = cached.get("data", {}).get("quotation", {}).get("current_price")
			if price:
				return price

		fresh = self.fetch()
		return fresh.get("data", {}).get("quotation", {}).get("current_price")

	def get_company_info(self) -> Dict[str, Any]:
		"""Get company information from yfinance."""
		try:
			ticker_obj = yf.Ticker(self.ticker)
			info = ticker_obj.info or {}

			return {
				"ticker": self.ticker,
				"company_name": info.get("longName") or info.get("shortName") or self.ticker,
				"sector": info.get("sector", "Unknown"),
				"industry": info.get("industry", "Unknown"),
				"asset_type": self._get_asset_type(info),
				"market_cap": info.get("marketCap"),
				"currency": info.get("currency", "USD"),
				"description": info.get("description", ""),
				"website": info.get("website", ""),
			}
		except Exception as e:
			logger.warning(f"Error fetching company info for {self.ticker}: {e}")
			return {
				"ticker": self.ticker,
				"company_name": self.ticker,
				"sector": "Unknown",
				"industry": "Unknown",
				"asset_type": "Stock",
			}

	def _get_asset_type(self, info: Dict) -> str:
		"""Determine asset type from yfinance info."""
		quote_type = info.get("quoteType", "EQUITY").upper()
		if quote_type == "ETF":
			return "ETF"
		elif quote_type == "FUTURE":
			return "Future"
		elif quote_type in ["INDEX", "CURRENCY"]:
			return quote_type.title()
		else:
			return "Stock"


class DataHistory:
	"""Fetch and cache historical OHLCV data via yfinance."""

	def __init__(self, ticker: str):
		self.ticker = ticker.upper()
		project_root = _get_project_root()
		self.cache_dir = project_root / "db" / "local" / "cache" / "history"
		self.cache_dir.mkdir(parents=True, exist_ok=True)
		self.filepath = self.cache_dir / f"{self.ticker}.parquet"

	def load_all(self) -> pd.DataFrame:
		"""Load all cached history as DataFrame."""
		try:
			if self.filepath.exists():
				df = pd.read_parquet(self.filepath)
				if "timestamp" in df.columns:
					df["timestamp"] = pd.to_datetime(df["timestamp"])
				return df
		except Exception as e:
			logger.warning(f"Error loading history cache for {self.ticker}: {e}")
		return pd.DataFrame()

	def fetch(
		self,
		start_date: Optional[str] = None,
		incremental: bool = True,
	) -> Dict[str, Any]:
		"""Fetch and cache historical OHLCV data from yfinance."""
		try:
			logger.info(f"Fetching history for {self.ticker}")

			# Check existing data
			df_existing = self.load_all()
			has_data = not df_existing.empty
			last_date = None

			if has_data and "timestamp" in df_existing.columns:
				last_date = df_existing["timestamp"].max()
			elif has_data:
				last_date = df_existing.index.max()

			# Determine fetch range
			if start_date:
				fetch_start = start_date
			elif incremental and has_data and last_date:
				last_date_dt = pd.to_datetime(last_date)
				fetch_start = (last_date_dt - timedelta(days=10)).strftime("%Y-%m-%d")
			elif has_data and last_date:
				last_date_dt = pd.to_datetime(last_date)
				fetch_start = (last_date_dt + timedelta(days=1)).strftime("%Y-%m-%d")
			else:
				fetch_start = "2010-01-01"

			fetch_end = datetime.now().strftime("%Y-%m-%d")

			logger.info(f"  Fetching {self.ticker} from {fetch_start} to {fetch_end}")
			ticker_obj = yf.Ticker(self.ticker)
			df_new = ticker_obj.history(start=fetch_start, end=fetch_end)

			if df_new is None or df_new.empty:
				logger.warning(f"No data for {self.ticker}")
				return {
					"status": "error",
					"ticker": self.ticker,
					"message": f"No data found for {self.ticker}",
				}

			rows_fetched = len(df_new)

			# Prepare new data
			df_new = df_new.reset_index()
			if "Date" not in df_new.columns and "index" in df_new.columns:
				df_new.rename(columns={"index": "Date"}, inplace=True)

			df_new["Date"] = pd.to_datetime(df_new["Date"])
			df_new = df_new.rename(columns={
				"Date": "timestamp",
				"Open": "open",
				"High": "high",
				"Low": "low",
				"Close": "close",
				"Volume": "volume",
			})
			df_new["ticker"] = self.ticker

			# Combine with existing if present
			if has_data:
				df_combined = pd.concat([df_existing, df_new], ignore_index=True)
				df_combined = df_combined.drop_duplicates(subset=["timestamp", "ticker"], keep="last")
				df_combined = df_combined.sort_values("timestamp")
			else:
				df_combined = df_new

			# Cache
			df_combined.to_parquet(self.filepath, index=False)
			logger.info(f"Cached {len(df_combined)} rows for {self.ticker}")

			return {
				"status": "success",
				"ticker": self.ticker,
				"rows_fetched": rows_fetched,
				"total_rows": len(df_combined),
				"message": f"Fetched {rows_fetched} rows",
			}

		except Exception as e:
			logger.error(f"Error fetching history for {self.ticker}: {e}")
			return {
				"status": "error",
				"ticker": self.ticker,
				"message": str(e),
			}

	def get_all(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
		"""Get all or filtered history as DataFrame."""
		df = self.load_all()

		if df.empty:
			return df

		if start_date:
			start_dt = pd.to_datetime(start_date)
			df = df[df["timestamp"] >= start_dt]

		if end_date:
			end_dt = pd.to_datetime(end_date)
			df = df[df["timestamp"] <= end_dt]

		return df.sort_values("timestamp")

	def get_current_price(self) -> Optional[float]:
		"""Get latest close price from cached history."""
		df = self.load_all()
		if df.empty:
			return None

		latest = df.sort_values("timestamp").iloc[-1]
		return latest.get("close")
