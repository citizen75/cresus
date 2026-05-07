"""Watchlist manager for saving and loading trading watchlists.

Manages watchlist persistence with OHLCV data and signal information.
Watches are stored as CSV files in db/local/watchlist/<strategy_name>.csv
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import os

import pandas as pd
from loguru import logger


def _get_project_root() -> Path:
	"""Get project root from CRESUS_PROJECT_ROOT env var or current working directory."""
	return Path(os.environ.get("CRESUS_PROJECT_ROOT", os.getcwd()))


class WatchlistManager:
	"""Manager for persisting and loading trading watchlists.

	Saves watchlist data with OHLCV (Open, High, Low, Close, Volume) and
	signal information (score and triggered signals) for each ticker.

	Files are stored as CSV in db/local/watchlist/<strategy_name>.csv
	"""

	def __init__(self, strategy_name: str, backtest_dir: Optional[str] = None):
		"""Initialize watchlist manager for a strategy.

		Args:
			strategy_name: Name of the strategy
			backtest_dir: Optional backtest directory for sandboxed backtesting
		"""
		self.strategy_name = strategy_name
		project_root = _get_project_root()

		if backtest_dir:
			# Use sandboxed backtest directory
			self.watchlist_dir = Path(backtest_dir) / "watchlist"
		else:
			# Use normal directory
			self.watchlist_dir = project_root / "db" / "local" / "watchlist"

		self.watchlist_dir.mkdir(parents=True, exist_ok=True)
		self.filepath = self.watchlist_dir / f"{strategy_name}.csv"

	def process(
		self,
		watchlist: List[str],
		ticker_scores: Dict[str, Dict[str, Any]],
		data_history: Dict[str, pd.DataFrame],
		sorted_tickers: Optional[List[Dict[str, Any]]] = None,
		strategy_config: Optional[Dict[str, Any]] = None,
		save_enabled: bool = True,
		orders: Optional[Dict[str, Any]] = None,
		indicators: Optional[Dict[str, Dict[str, Any]]] = None,
	) -> Dict[str, Any]:
		"""Process and save watchlist with intelligent ticker selection.

		Handles full watchlist processing including:
		- Determining which tickers to save (from sorted_tickers or watchlist)
		- Limiting by max_count from strategy config
		- Adding technical indicators and order information
		- Optionally saving to disk based on save_enabled toggle

		Args:
			watchlist: List of all watchlist tickers
			ticker_scores: Dict mapping ticker -> {score, raw_score, triggered_signals, signal_count}
			data_history: Dict mapping ticker -> DataFrame with OHLCV data
			sorted_tickers: Optional list of pre-sorted tickers from signals (with rank info)
			strategy_config: Optional strategy config dict (for max_count)
			save_enabled: Toggle to enable/disable saving to disk (default: True)
			orders: Optional dict of order data by ticker
			indicators: Optional dict of technical indicators by ticker

		Returns:
			Dict with status and watchlist save details
		"""
		if not save_enabled:
			return {
				"status": "success",
				"message": "Watchlist saving is disabled",
				"save_enabled": False,
				"ticker_count": 0,
			}

		# Determine tickers to save
		tickers_to_save = []
		if sorted_tickers:
			# Limit to max_count from strategy config (default 20)
			max_count = 20
			if strategy_config:
				max_count = strategy_config.get("watchlist", {}).get("parameters", {}).get("tickers", {}).get("max_count", 20)
			top_tickers = sorted_tickers[:max_count]
			tickers_to_save = [t["ticker"] if isinstance(t, dict) else t for t in top_tickers]
		elif watchlist:
			tickers_to_save = watchlist

		if not tickers_to_save:
			return {
				"status": "warning",
				"message": "No tickers to save",
				"save_enabled": True,
				"ticker_count": 0,
			}

		# Save to disk
		return self.save(tickers_to_save, ticker_scores, data_history, orders=orders, indicators=indicators)

	def save(
		self,
		watchlist: List[str],
		ticker_scores: Dict[str, Dict[str, Any]],
		data_history: Dict[str, pd.DataFrame],
		orders: Optional[Dict[str, Any]] = None,
		indicators: Optional[Dict[str, Dict[str, Any]]] = None,
	) -> Dict[str, Any]:
		"""Save watchlist with OHLCV, signal data, indicators, and order info.

		Merges watchlist tickers with their latest OHLCV data, signal scores,
		technical indicators, and pending order information.

		Args:
			watchlist: List of ticker symbols in watchlist
			ticker_scores: Dict mapping ticker -> {score, raw_score, triggered_signals, signal_count}
			data_history: Dict mapping ticker -> DataFrame with OHLCV data
			orders: Optional dict mapping ticker -> order info
			indicators: Optional dict mapping ticker -> technical indicators

		Returns:
			Dict with status and details about saved watchlist
		"""
		try:
			rows = []

			for ticker in watchlist:
				# Get signal info for this ticker
				score_info = ticker_scores.get(ticker, {})
				signal_score = score_info.get("score", 0.0)
				triggered_signals = score_info.get("triggered_signals", [])
				signals_str = ",".join(triggered_signals) if triggered_signals else ""

				# Get OHLCV data for this ticker
				if ticker in data_history:
					ticker_data = data_history[ticker]

					# Handle both DataFrame and empty cases
					if isinstance(ticker_data, pd.DataFrame) and not ticker_data.empty:
						# Get latest row
						latest = ticker_data.iloc[-1]

						# Extract OHLCV columns (handle both cases)
						date = latest.get("timestamp", latest.name) if hasattr(latest, "get") else latest.get("timestamp", latest.index)

						row = {
							"ticker": ticker,
							"date": date,
							"open": latest.get("open") if hasattr(latest, "get") else latest.get("open"),
							"high": latest.get("high") if hasattr(latest, "get") else latest.get("high"),
							"low": latest.get("low") if hasattr(latest, "get") else latest.get("low"),
							"close": latest.get("close") if hasattr(latest, "get") else latest.get("close"),
							"volume": latest.get("volume") if hasattr(latest, "get") else latest.get("volume"),
							"signal_score": signal_score,
							"signals": signals_str,
						}
						rows.append(row)
					else:
						# No data for this ticker, still add watchlist entry
						row = {
							"ticker": ticker,
							"date": None,
							"open": None,
							"high": None,
							"low": None,
							"close": None,
							"volume": None,
							"signal_score": signal_score,
							"signals": signals_str,
						}
						rows.append(row)
				else:
					# Ticker not in data_history
					row = {
						"ticker": ticker,
						"date": None,
						"open": None,
						"high": None,
						"low": None,
						"close": None,
						"volume": None,
						"signal_score": signal_score,
						"signals": signals_str,
					}
					rows.append(row)

			# Add indicators if provided
			if indicators:
				for i, row in enumerate(rows):
					ticker = row["ticker"]
					if ticker in indicators:
						ticker_indicators = indicators[ticker]
						# Add all indicators with their parameter-based names
						for indicator_name, indicator_value in ticker_indicators.items():
							row[indicator_name] = indicator_value
					rows[i] = row

			# Add order info if provided
			if orders:
				for i, row in enumerate(rows):
					ticker = row["ticker"]
					if ticker in orders:
						order_info = orders[ticker]
						row["order_qty"] = order_info.get("quantity")
						row["order_entry"] = order_info.get("entry_price")
						row["order_stop"] = order_info.get("stop_loss")
						row["order_target"] = order_info.get("take_profit")
						row["order_method"] = order_info.get("execution_method")
						row["order_status"] = order_info.get("status")
					rows[i] = row

			# Create DataFrame and save to CSV
			if rows:
				df = pd.DataFrame(rows)
				df.to_csv(self.filepath, index=False)
				logger.info(f"Saved watchlist '{self.strategy_name}' with {len(rows)} tickers to {self.filepath}")

				return {
					"status": "success",
					"message": f"Watchlist saved successfully",
					"file": str(self.filepath),
					"ticker_count": len(rows),
					"size": self.filepath.stat().st_size,
				}
			else:
				return {
					"status": "warning",
					"message": "No tickers in watchlist to save",
					"file": str(self.filepath),
					"ticker_count": 0,
				}

		except Exception as e:
			logger.error(f"Error saving watchlist '{self.strategy_name}': {e}")
			return {
				"status": "error",
				"message": f"Failed to save watchlist: {str(e)}",
				"error_type": type(e).__name__,
			}

	def load(self) -> Optional[pd.DataFrame]:
		"""Load watchlist from CSV.

		Returns:
			DataFrame with watchlist data, or None if file doesn't exist
		"""
		try:
			if self.filepath.exists():
				df = pd.read_csv(self.filepath)
				logger.info(f"Loaded watchlist '{self.strategy_name}' with {len(df)} tickers from {self.filepath}")
				return df
			else:
				logger.warning(f"Watchlist file not found: {self.filepath}")
				return None

		except Exception as e:
			logger.error(f"Error loading watchlist '{self.strategy_name}': {e}")
			return None

	def list_tickers(self) -> Optional[List[str]]:
		"""Get list of tickers from saved watchlist.

		Returns:
			List of ticker symbols, or None if watchlist doesn't exist
		"""
		df = self.load()
		if df is not None:
			return df["ticker"].tolist()
		return None

	def get_top_tickers(self, n: int = 10) -> Optional[List[Dict[str, Any]]]:
		"""Get top N tickers by signal score.

		Args:
			n: Number of top tickers to return

		Returns:
			List of dicts with ticker info, or None if watchlist doesn't exist
		"""
		df = self.load()
		if df is not None:
			top = df.nlargest(n, "signal_score")
			return top[["ticker", "close", "signal_score", "signals"]].to_dict("records")
		return None

	def delete(self) -> Dict[str, Any]:
		"""Delete saved watchlist file.

		Returns:
			Dict with status of deletion
		"""
		try:
			if self.filepath.exists():
				self.filepath.unlink()
				logger.info(f"Deleted watchlist '{self.strategy_name}' from {self.filepath}")
				return {
					"status": "success",
					"message": f"Watchlist deleted successfully",
				}
			else:
				return {
					"status": "warning",
					"message": f"Watchlist file not found: {self.filepath}",
				}

		except Exception as e:
			logger.error(f"Error deleting watchlist '{self.strategy_name}': {e}")
			return {
				"status": "error",
				"message": f"Failed to delete watchlist: {str(e)}",
			}
