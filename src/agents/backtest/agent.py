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
from agents.watchlist_alphas.agent import WatchlistAlphasAgent
from tools.portfolio.journal import Journal
from tools.portfolio.orders import Orders
from tools.backtest.manager import BacktestManager
from tools.portfolio.metrics import PortfolioMetrics
from gateway.websockets.manager import get_websocket_manager


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


def _get_data_date_range(data_history: Dict) -> Optional[tuple]:
	"""Get the date range of available data.

	Args:
		data_history: Dict of {ticker: DataFrame} where each DataFrame has 'timestamp' column

	Returns:
		Tuple of (min_date, max_date) or None if no data
	"""
	if not data_history:
		return None

	all_dates = []
	for ticker_data in data_history.values():
		if not ticker_data.empty and "timestamp" in ticker_data.columns:
			all_dates.extend(ticker_data["timestamp"].dt.date.unique())

	if not all_dates:
		return None

	return (min(all_dates), max(all_dates))


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

	def _calculate_daily_metrics(self, portfolio_name: str, current_date: date, start_date: date, initial_capital: float = 100000.0) -> Dict[str, Any]:
		"""Calculate daily metrics snapshot for WebSocket broadcast.

		Extracts quick metrics from journal without expensive portfolio history replay.

		Args:
			portfolio_name: Portfolio name
			current_date: Current date for metrics calculation
			start_date: Start date of backtest
			initial_capital: Initial capital amount

		Returns:
			Dict with daily metrics (trade count, simple returns, etc.)
		"""
		try:
			from tools.portfolio.journal import Journal
			import pandas as pd
			import numpy as np

			result = {
				"date": current_date.isoformat(),
				"total_return_pct": 0.0,
				"portfolio_value": initial_capital,
				"total_trades": 0,
				"closed_trades": 0,
				"win_rate_pct": 0.0,
				"profit_factor": 0.0,
				"avg_winning_trade_pct": 0.0,
				"avg_losing_trade_pct": 0.0,
				"best_trade_pct": 0.0,
				"worst_trade_pct": 0.0,
			}

			# Load journal and count trades up to current date
			journal = Journal(portfolio_name, context=self.context.__dict__)
			df = journal.load_df()
			if df.empty:
				return result

			# Convert dates
			df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
			current_date_ts = pd.Timestamp(current_date)

			# Count completed trades by current date
			completed = df[(df['status'] == 'completed') & (df['created_at'] <= current_date_ts)]
			result["closed_trades"] = len(completed)

			# Count all trades (buy + sell operations)
			all_trades = df[(df['created_at'] <= current_date_ts) & (df['operation'].isin(['BUY', 'SELL']))]
			result["total_trades"] = len(all_trades)

			# Calculate trade-level metrics from completed trades
			if len(completed) > 0:
				pnl_pct = pd.to_numeric(completed['pnl_pct'], errors='coerce').fillna(0)
				pnl = pd.to_numeric(completed['pnl'], errors='coerce').fillna(0)

				# Win rate
				winning = (pnl_pct > 0).sum()
				result["win_rate_pct"] = float((winning / len(completed) * 100) if len(completed) > 0 else 0.0)

				# Best and worst trades
				if len(pnl_pct) > 0:
					result["best_trade_pct"] = float(pnl_pct.max())
					result["worst_trade_pct"] = float(pnl_pct.min())

				# Average winning and losing trades
				winning_trades = pnl_pct[pnl_pct > 0]
				losing_trades = pnl_pct[pnl_pct < 0]

				if len(winning_trades) > 0:
					result["avg_winning_trade_pct"] = float(winning_trades.mean())
				if len(losing_trades) > 0:
					result["avg_losing_trade_pct"] = float(losing_trades.mean())

				# Profit factor (sum of wins / absolute value of losses)
				sum_wins = pnl[pnl > 0].sum()
				sum_losses = pnl[pnl < 0].sum()
				if sum_losses != 0:
					result["profit_factor"] = float(sum_wins / abs(sum_losses))
				elif sum_wins > 0:
					result["profit_factor"] = float('inf')

			# Try to calculate portfolio value from history (with error handling)
			try:
				from tools.portfolio.portfolio_history import PortfolioHistory
				history = PortfolioHistory(portfolio_name, initial_capital=initial_capital, context=self.context.__dict__)
				history_result = history.calculate(recalculate=False, use_cache_only=True)

				if history_result.get("status") == "success":
					history_list = history_result.get("history", [])
					if history_list:
						history_df = pd.DataFrame(history_list)
						history_df['date'] = pd.to_datetime(history_df['date']).dt.date
						history_up_to_date = history_df[history_df['date'] <= current_date]

						if len(history_up_to_date) > 0:
							current_value = history_up_to_date.iloc[-1].get('value', initial_capital)
							result["portfolio_value"] = float(current_value)
							result["total_return_pct"] = float((current_value - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0.0
			except Exception as e:
				self.logger.debug(f"Could not calculate portfolio history: {str(e)}")
				# Fallback: estimate from trades PnL
				if len(completed) > 0:
					total_pnl = pd.to_numeric(completed.get('pnl', pd.Series()), errors='coerce').fillna(0).sum()
					result["portfolio_value"] = initial_capital + total_pnl
					result["total_return_pct"] = float((total_pnl / initial_capital * 100) if initial_capital > 0 else 0.0)

			return result
		except Exception as e:
			self.logger.debug(f"Failed to calculate daily metrics: {str(e)}")
			return {"date": current_date.isoformat()}

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

		# Initialize backtest using BacktestManager
		# Use backtest_id from input if provided (e.g., from BacktestFlow)
		backtest_id_input = input_data.get("backtest_id")
		backtest_manager = BacktestManager()
		init_result = backtest_manager.initialize_backtest(strategy_name, start_date, end_date, lookback_days, backtest_id_input)

		if init_result.get("status") != "success":
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": init_result.get("message"),
			}

		backtest_id = init_result.get("backtest_id")
		backtest_dir = init_result.get("backtest_dir")
		backtest = init_result.get("backtest")

		self.logger.info(f"Created backtest directory: {backtest_dir}")
		self.context.set("backtest_id", backtest_id)
		self.context.set("backtest", backtest)
		self.context.set("backtest_dir", backtest_dir)

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

		# Calculate alphas via WatchlistAlphasAgent
		alphas_agent = WatchlistAlphasAgent(f"alphas[{strategy_name}]", self.context)
		alphas_result = alphas_agent.run({})
		if alphas_result.get("status") == "error":
			self.logger.warning(f"Alphas calculation failed: {alphas_result.get('message')}")
			# Continue anyway - alphas are optional

		# Extract trading days from context
		data_history = self.context.get("data_history") or {}

		# Check if requested date range overlaps with available data
		data_range = _get_data_date_range(data_history)
		if not data_range:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No historical data available for any tickers",
			}
		
		data_min_date, data_max_date = data_range
		
		# Validate requested date range
		if start_date > data_max_date:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"Start date {start_date.isoformat()} is after available data (ends {data_max_date.isoformat()})",
			}
		
		if end_date < data_min_date:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"End date {end_date.isoformat()} is before available data (starts {data_min_date.isoformat()})",
			}
		
		# Adjust dates to available range if needed
		if start_date < data_min_date:
			self.logger.warning(f"Start date {start_date.isoformat()} adjusted to first available date {data_min_date.isoformat()}")
			start_date = data_min_date
		
		if end_date > data_max_date:
			self.logger.warning(f"End date {end_date.isoformat()} adjusted to last available date {data_max_date.isoformat()}")
			end_date = data_max_date
		
		trading_days = _get_trading_days(data_history, start_date, end_date)

		if not trading_days:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"No trading days found between {start_date.isoformat()} and {end_date.isoformat()}. Available data: {data_min_date.isoformat()} to {data_max_date.isoformat()}",
			}

		self.logger.info(f"Found {len(trading_days)} trading days")
		backtest["total_trading_days"] = len(trading_days)

		# Pre-slice data by date for efficient access (avoid filtering on each iteration)
		day_data_cache = self._create_day_data_cache(data_history)
		self.logger.debug(f"BacktestAgent: day_data_cache has {len(day_data_cache)} dates")
		if day_data_cache:
			cache_dates = sorted(day_data_cache.keys())
			self.logger.debug(f"BacktestAgent: Cache dates: {cache_dates[0]} to {cache_dates[-1]}")
			first_date = cache_dates[0]
			if first_date in day_data_cache:
				self.logger.debug(f"BacktestAgent: First date {first_date} has {len(day_data_cache[first_date])} tickers")

		# Main backtest loop: pre_market → [increment] → market → post_market
		portfolio_name = self.context.get("portfolio_name") or "default"

		# Include last trading day if we have data for the next day to execute trades
		trading_days_to_process = trading_days[:-1]

		# Check if we can process the final day (need data for next day)
		if len(trading_days) > 0:
			last_day = trading_days[-1]
			# Look for any data after the last day
			future_dates = [d for d in day_data_cache.keys() if d > last_day]
			if future_dates:
				# Add the first future date as a synthetic next_date
				next_available_date = min(future_dates)
				trading_days.append(next_available_date)
				trading_days_to_process = trading_days[:-1]
				self.logger.info(f"Including final trading day {last_day} (using {next_available_date} for execution)")

		# Get initial capital from strategy config
		strategy_config = self.context.get("strategy_config") or {}
		initial_capital = strategy_config.get("backtest", {}).get("initial_capital", 100000.0)
		self.logger.info(f"Using initial capital: ${initial_capital:.2f}")

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

			# Pass next_date OHLCV data to market flow (use cached data, not stale previous day data)
			next_day_data = day_data_cache.get(next_date, {})
			self.logger.debug(f"BacktestAgent: next_date={next_date}, next_day_data has {len(next_day_data)} tickers")
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
			try:
				journal = Journal(portfolio_name, context=self.context.__dict__)
				journal.flush()
				orders = Orders(portfolio_name, context=self.context.__dict__)
				orders.flush()
			except Exception as e:
				self.logger.warning(f"Failed to flush journal/orders for {portfolio_name}: {str(e)}")

			# Calculate daily metrics for this date
			daily_result = self._calculate_daily_metrics(portfolio_name, next_date, start_date, initial_capital=initial_capital)
			backtest["daily_results"].append(daily_result)

			# Broadcast daily progress to WebSocket clients
			try:
				ws_manager = get_websocket_manager()
				ws_manager.broadcast_daily_results_sync(
					backtest_id=backtest_id,
					strategy_name=strategy_name,
					date=next_date.isoformat(),
					daily_results=daily_result,
					progress={
						"current": i + 1,
						"total": len(trading_days_to_process),
						"percentage": int((i + 1) / len(trading_days_to_process) * 100)
					}
				)
				self.logger.debug(f"Broadcast daily_results for {next_date}: day {i+1}/{len(trading_days_to_process)}")
			except Exception as e:
				self.logger.error(f"WebSocket broadcast failed: {str(e)}", exc_info=True)

		backtest["days_processed"] = len(backtest["daily_results"])
		self.logger.info(f"Backtest completed: {backtest['days_processed']} days processed")

		# Save strategy to backtest directory (already loaded by StrategyAgent)
		strategy_config = self.context.get("strategy_config")
		if strategy_config:
			save_result = backtest_manager.save_strategy(strategy_name, backtest_id, strategy_config)
			if save_result.get("status") == "success":
				self.logger.info(f"Saved strategy to {save_result.get('file')}")
			else:
				self.logger.warning(f"Failed to save strategy: {save_result.get('message')}")
		else:
			self.logger.warning("Strategy config not found in context")

		# Calculate and save metrics
		try:
			portfolio_name = self.context.get("portfolio_name") or "default"
			metrics = PortfolioMetrics()
			metrics_result = metrics.calculate_backtest_metrics(
				portfolio_name,
				start_date,
				end_date,
				initial_capital
			)

			if metrics_result:
				backtest["metrics"] = metrics_result
				save_metrics_result = backtest_manager.save_metrics(strategy_name, backtest_id, metrics_result)
				if save_metrics_result.get("status") == "success":
					self.logger.info(f"Saved metrics to {save_metrics_result.get('file')}")
				else:
					self.logger.warning(f"Failed to save metrics: {save_metrics_result.get('message')}")
		except Exception as e:
			self.logger.warning(f"Could not calculate metrics: {str(e)}")

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