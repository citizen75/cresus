"""Market regime data loader - loads and pivots OHLCV data."""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from core.agent import Agent
from tools.data.core import DataHistory
from tools.universe.universe import Universe


class RegimeDataLoaderAgent(Agent):
	"""Load historical OHLCV data for universe tickers, pivot to wide form.

	Reads from context:
		regime_input: dict with universe, lookback_days, session_date, data_path

	Writes to context:
		prices_df: DataFrame(date, tickers) - close prices
		returns_df: DataFrame(date, tickers) - daily pct_change
		volume_df: DataFrame(date, tickers) - volume
		high_df: DataFrame(date, tickers) - high
		low_df: DataFrame(date, tickers) - low
		tickers: List[str] - loaded tickers
		load_end_date: datetime - last date in data
	"""

	def __init__(self, name: str = "RegimeDataLoaderAgent"):
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Load and pivot OHLCV data."""
		if input_data is None:
			input_data = {}

		regime_input = self.context.get("regime_input") or {}
		universe_name = regime_input.get("universe")
		lookback_days = regime_input.get("lookback_days", 1000)
		session_date = regime_input.get("session_date")
		data_path = regime_input.get("data_path")

		if not universe_name:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "universe required in regime_input"
			}

		try:
			# Determine date range
			if session_date:
				end_date = datetime.strptime(session_date, "%Y-%m-%d").date()
			else:
				end_date = datetime.now().date()

			start_date = end_date - timedelta(days=lookback_days)

			self.logger.info(f"Loading {universe_name} data from {start_date} to {end_date}")

			# Load data
			if data_path:
				data_dict = self._load_from_parquet(data_path)
			else:
				data_dict = self._load_universe_data(universe_name, start_date.isoformat(), end_date.isoformat())

			if not data_dict:
				return {
					"status": "error",
					"input": input_data,
					"output": {},
					"message": f"No data loaded for {universe_name}"
				}

			# Pivot to wide form
			prices_df = self._pivot_column(data_dict, "close")
			returns_df = prices_df.pct_change()
			volume_df = self._pivot_column(data_dict, "volume")
			high_df = self._pivot_column(data_dict, "high")
			low_df = self._pivot_column(data_dict, "low")

			tickers = list(prices_df.columns)
			load_end_date = prices_df.index[-1]

			# Store in context
			self.context.set("prices_df", prices_df)
			self.context.set("returns_df", returns_df)
			self.context.set("volume_df", volume_df)
			self.context.set("high_df", high_df)
			self.context.set("low_df", low_df)
			self.context.set("tickers", tickers)
			self.context.set("load_end_date", load_end_date)

			self.logger.info(f"Loaded {len(tickers)} tickers, {len(prices_df)} trading days")

			return {
				"status": "success",
				"input": input_data,
				"output": {
					"n_tickers": len(tickers),
					"n_days": len(prices_df),
					"tickers": tickers,
					"date_range": {
						"start": prices_df.index[0].isoformat(),
						"end": prices_df.index[-1].isoformat()
					}
				},
				"message": f"Loaded {len(tickers)} tickers, {len(prices_df)} trading days"
			}

		except Exception as e:
			self.logger.exception(f"Error loading data: {e}")
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"Data loading failed: {str(e)}"
			}

	def _load_universe_data(self, universe_name: str, start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
		"""Load data for all tickers in universe."""
		try:
			universe = Universe(universe_name)
			tickers = universe.get_tickers()
		except Exception as e:
			self.logger.error(f"Error loading universe {universe_name}: {e}")
			return {}

		data_dict = {}
		for ticker in tickers:
			try:
				df = self._load_ticker(ticker, start_date, end_date)
				if df is not None and not df.empty:
					data_dict[ticker] = df
				else:
					self.logger.warning(f"No data for {ticker}")
			except Exception as e:
				self.logger.warning(f"Error loading {ticker}: {e}")

		return data_dict

	def _load_ticker(self, ticker: str, start_date: str, end_date: Optional[str]) -> Optional[pd.DataFrame]:
		"""Load a single ticker's history."""
		try:
			dh = DataHistory(ticker)
			df = dh.get_all(start_date, end_date)
			if df is not None and not df.empty:
				df["ticker"] = ticker
				return df
		except Exception as e:
			self.logger.debug(f"Error loading {ticker}: {e}")
		return None

	def _load_from_parquet(self, data_path: str) -> Dict[str, pd.DataFrame]:
		"""Load data from parquet file."""
		try:
			path = Path(data_path)
			if not path.exists():
				raise FileNotFoundError(f"Parquet file not found: {data_path}")

			df = pd.read_parquet(path)
			self.logger.info(f"Loaded parquet from {data_path}: shape {df.shape}")

			# Pivot if necessary
			if "ticker" in df.columns:
				data_dict = {}
				for ticker in df["ticker"].unique():
					data_dict[ticker] = df[df["ticker"] == ticker].copy()
				return data_dict
			else:
				# Assume single ticker or wide format
				return {"data": df}

		except Exception as e:
			self.logger.error(f"Error loading parquet: {e}")
			return {}

	def _pivot_column(self, data_dict: Dict[str, pd.DataFrame], column: str) -> pd.DataFrame:
		"""Build wide DataFrame from {ticker: df} dict for a given column."""
		dfs = []

		for ticker, df in data_dict.items():
			if column in df.columns:
				series = df[["timestamp", column]].copy()
				series.set_index("timestamp", inplace=True)
				series.columns = [ticker]
				dfs.append(series)

		if not dfs:
			self.logger.warning(f"No data for column {column}")
			return pd.DataFrame()

		result = pd.concat(dfs, axis=1)
		result = result.sort_index()

		# Forward fill NaN values
		result = result.ffill()

		return result
