"""BacktestAgent for orchestrating multi-phase backtesting flows."""

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

try:
	from tqdm import tqdm
	HAS_TQDM = True
except ImportError:
	HAS_TQDM = False

from core.agent import Agent
from core.context import AgentContext
from core.flow import Flow
from agents.strategy.agent import StrategyAgent
from agents.data.agent import DataAgent
from tools.portfolio.journal import Journal
from tools.portfolio.orders import Orders


def _parse_date(value: Any) -> Optional[date]:
	"""Parse date from various formats.

	Args:
		value: Date as string, date object, or None

	Returns:
		date object or None
	"""
	if value is None:
		return None
	if isinstance(value, date):
		return value
	return date.fromisoformat(str(value))


def _get_trading_days(data_history: Dict, start_date: date, end_date: date) -> List[date]:
	"""Extract sorted trading days from data history within date range.

	Args:
		data_history: Dict of {ticker: DataFrame} where each DataFrame has 'timestamp' column
		start_date: Filter start (inclusive)
		end_date: Filter end (inclusive)

	Returns:
		Sorted list of trading dates in range
	"""
	if not data_history:
		return []

	ref_ticker = max(data_history, key=lambda t: len(data_history[t]))
	df = data_history[ref_ticker]
	dates = df["timestamp"].dt.date.unique()
	return sorted(d for d in dates if start_date <= d <= end_date)


class BacktestAgent(Agent):
	"""Agent for orchestrating multi-phase backtest loops.

	Implements a structured backtesting framework with three phases per trading day:
	1. Pre-market: generate signals/decisions using data up to current_date
	2. Market: execute trades on next trading day at next_date prices
	3. Post-market: update portfolio and metrics after close

	Flows are optional - the agent continues if flows are not set.
	"""

	def __init__(self, name: str = "backtest", context: Optional[AgentContext] = None):
		"""Initialize BacktestAgent.

		Args:
			name: Agent identifier
			context: Optional shared AgentContext
		"""
		super().__init__(name, context)
		self.pre_market_flow: Optional[Flow] = None
		self.market_flow: Optional[Flow] = None
		self.post_market_flow: Optional[Flow] = None

	def set_premarket_flow(self, flow: Flow) -> None:
		"""Set the pre-market flow.

		Args:
			flow: Flow to execute in pre-market phase
		"""
		self.pre_market_flow = flow

	def set_market_flow(self, flow: Flow) -> None:
		"""Set the market flow.

		Args:
			flow: Flow to execute in market phase
		"""
		self.market_flow = flow

	def set_postmarket_flow(self, flow: Flow) -> None:
		"""Set the post-market flow.

		Args:
			flow: Flow to execute in post-market phase
		"""
		self.post_market_flow = flow

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Execute backtest loop over trading days.

		Args:
			input_data: Dict with keys:
				- strategy_name (required): Name of strategy to backtest
				- start_date (optional): Start date as string YYYY-MM-DD or date object
				- end_date (optional): End date as string YYYY-MM-DD or date object (default: today)
				- lookback_days (optional): Days back from end_date if start_date not provided (default: 365)

		Returns:
			Response dict with status, input, and output containing backtest summary
		"""
		if input_data is None:
			input_data = {}

		strategy_name = input_data.get("strategy_name")
		if not strategy_name:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "strategy_name is required",
			}

		# Resolve dates
		end_date = _parse_date(input_data.get("end_date")) or date.today()
		lookback_days = input_data.get("lookback_days", 365)
		start_date = _parse_date(input_data.get("start_date")) or (end_date - timedelta(days=lookback_days))

		self.logger.info(f"Backtest {strategy_name} from {start_date} to {end_date}")

		# Initialize backtest context
		backtest = {
			"strategy_name": strategy_name,
			"start_date": start_date.isoformat(),
			"end_date": end_date.isoformat(),
			"lookback_days": lookback_days,
			"daily_results": [],
			"metrics": {},
		}
		self.context.set("backtest", backtest)

		# Load tickers via StrategyAgent
		strategy_agent = StrategyAgent(f"strategy[{strategy_name}]", self.context)
		strategy_result = strategy_agent.run(input_data)
		if strategy_result.get("status") == "error":
			return strategy_result

		# Load data history via DataAgent
		data_agent = DataAgent(f"data[{strategy_name}]", self.context)
		data_result = data_agent.run({})
		if data_result.get("status") == "error":
			return data_result

		# Extract trading days from context
		data_history = self.context.get("data_history") or {}
		trading_days = _get_trading_days(data_history, start_date, end_date)

		if not trading_days:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No trading days found in date range",
			}

		self.logger.info(f"Found {len(trading_days)} trading days")
		backtest["total_trading_days"] = len(trading_days)

		# Pre-slice data by date for efficient access (avoid filtering on each iteration)
		day_data_cache = self._create_day_data_cache(data_history)

		# Main backtest loop: pre_market → [increment] → market → post_market
		portfolio_name = self.context.get("portfolio_name") or "default"
		trading_days_to_process = trading_days[:-1]

		# Use progress bar if tqdm is available
		iterator = tqdm(enumerate(trading_days_to_process), total=len(trading_days_to_process), desc="Backtest Progress") if HAS_TQDM else enumerate(trading_days_to_process)

		for i, current_date in iterator:
			next_date = trading_days[i + 1]

			# Pre-market phase: signals based on data up to current_date
			self.context.set("current_date", current_date)
			# Slice data_history to current_date so watchlist changes daily
			self._set_data_history_for_date(data_history, current_date)
			if self.pre_market_flow:
				self.pre_market_flow.context = self.context
				self.pre_market_flow.process({
					"date": current_date.isoformat(),
					"strategy_name": strategy_name,
					"portfolio_name": portfolio_name,
				})

			# Increment to next trading day
			self.context.set("current_date", next_date)

			# Pass next_date OHLCV data to market flow (no reloading)
			next_day_data = day_data_cache.get(next_date, {})
			self.context.set("next_day_data", next_day_data)

			# Market phase: execute on next_date prices with pre-loaded data
			if self.market_flow:
				self.market_flow.context = self.context
				self.market_flow.process({
					"date": next_date.isoformat(),
					"strategy_name": strategy_name,
					"portfolio_name": portfolio_name,
				})

			# Post-market phase: update after close
			if self.post_market_flow:
				self.post_market_flow.context = self.context
				self.post_market_flow.process({
					"date": next_date.isoformat(),
					"strategy_name": strategy_name,
					"portfolio_name": portfolio_name,
				})

			# Flush journal and orders to disk at end of day
			journal = Journal(portfolio_name, context=self.context.__dict__)
			journal.flush()
			orders = Orders(portfolio_name, context=self.context.__dict__)
			orders.flush()

			backtest["daily_results"].append({"date": next_date.isoformat()})

		backtest["days_processed"] = len(backtest["daily_results"])
		self.logger.info(f"Backtest completed: {backtest['days_processed']} days processed")

		return {
			"status": "success",
			"input": input_data,
			"output": backtest,
		}

	def _create_day_data_cache(self, data_history: Dict) -> Dict[date, Dict[str, Any]]:
		"""Create a cache of OHLCV data organized by trading date for fast lookup.

		Transforms data_history from {ticker: DataFrame} to {date: {ticker: row}}.
		This avoids filtering data on every loop iteration.

		Args:
			data_history: Dict mapping {ticker: DataFrame with timestamp column}

		Returns:
			Dict mapping {date: {ticker: latest_row_for_date}}
		"""
		day_cache = {}

		for ticker, df in data_history.items():
			if df.empty:
				continue

			# Get timestamp column (handle both column and index)
			if "timestamp" in df.columns:
				timestamps = df["timestamp"]
			else:
				timestamps = df.index

			# Group by date
			if hasattr(timestamps, 'dt'):
				# pandas datetime index/series
				dates = timestamps.dt.date
			else:
				# convert to date if needed
				dates = [ts.date() if hasattr(ts, 'date') else ts for ts in timestamps]

			# For each date, store the latest row for this ticker
			for idx, trading_date in enumerate(dates):
				if trading_date not in day_cache:
					day_cache[trading_date] = {}

				# Store the row for this ticker on this date
				day_cache[trading_date][ticker] = df.iloc[idx]

		return day_cache

	def _set_data_history_for_date(self, data_history: Dict, current_date: date) -> None:
		"""Slice data_history to include only data up to current_date.

		This ensures watchlist calculations use only data available on the current
		trading day, making the watchlist change day-to-day as new data appears.

		Args:
			data_history: Dict mapping {ticker: DataFrame}
			current_date: Current trading date
		"""
		import pandas as pd

		if not data_history:
			return

		# Slice each ticker's data to current_date and earlier
		sliced_history = {}
		for ticker, df in data_history.items():
			if df.empty:
				sliced_history[ticker] = df
				continue

			# Get timestamp column
			if "timestamp" in df.columns:
				timestamps = pd.to_datetime(df["timestamp"])
			else:
				timestamps = pd.to_datetime(df.index)

			# Extract dates and filter to current_date and earlier
			dates = timestamps.dt.date
			mask = dates <= current_date
			sliced_history[ticker] = df[mask].copy()

		self.context.set("data_history", sliced_history)
		self.logger.debug(f"Sliced data_history to {current_date} for PreMarketFlow")