"""BacktestAgent for orchestrating multi-phase backtesting flows."""

import time
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Union

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
from agents.research.agent import ResearchAgent
from tools.portfolio.journal import Journal
from tools.portfolio.orders import Orders
from tools.backtest.manager import BacktestManager
from tools.portfolio.metrics import PortfolioMetrics
from gateway.websockets.manager import get_websocket_manager

# Each backtest phase is now a plain Agent (MarketPrepAgent/MarketProcessAgent/
# MarketCloseAgent) rather than a Flow, but both expose a duck-type-compatible
# .context attribute and .process(input_data) method, so either is accepted here.
PhasePipeline = Union[Flow, Agent]


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

	Fully self-sufficient: process() loads/validates the strategy, auto-wires the
	three phase agents (unless overridden via set_premarket_flow/set_market_flow/
	set_postmarket_flow, e.g. for tests), runs the day loop, then computes final
	metrics, runs ResearchAgent, and saves results to the backtest directory.

	Implements a structured backtesting framework with three phases per trading day:
	1. Pre-market (MarketPrepAgent by default): generate signals/decisions using data up to current_date
	2. Market (MarketProcessAgent by default): execute trades on next trading day at next_date prices
	3. Post-market (MarketCloseAgent by default): expire stale orders and update metrics after close

	Phases can be overridden via set_premarket_flow/set_market_flow/set_postmarket_flow
	(e.g. for tests, or alternate engines) - both Agent and Flow instances are accepted.
	"""

	def __init__(self, name: str = "backtest", context: Optional[AgentContext] = None, websocket: bool = True):
		"""Initialize BacktestAgent.

		Args:
			name: Agent identifier
			context: Optional shared AgentContext
			websocket: Enable WebSocket broadcasts and real-time metrics (default: True)
		"""
		super().__init__(name, context)
		self.pre_market_flow: Optional[PhasePipeline] = None
		self.market_flow: Optional[PhasePipeline] = None
		self.post_market_flow: Optional[PhasePipeline] = None
		self.websocket_enabled = websocket

	def set_premarket_flow(self, flow: PhasePipeline) -> None:
		"""Set the pre-market phase (typically a MarketPrepAgent).

		Args:
			flow: Agent or Flow to execute in pre-market phase
		"""
		self.pre_market_flow = flow

	def set_market_flow(self, flow: PhasePipeline) -> None:
		"""Set the market phase (typically a MarketProcessAgent).

		Args:
			flow: Agent or Flow to execute in market phase
		"""
		self.market_flow = flow

	def set_postmarket_flow(self, flow: PhasePipeline) -> None:
		"""Set the post-market phase (typically a MarketCloseAgent).

		Args:
			flow: Agent or Flow to execute in post-market phase
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
				"return_pct": 0.0,
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

			if not portfolio_name:
				self.logger.error(f"portfolio_name is None or empty for date {current_date}")
				return result

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
				# Calculate PnL from buy/sell pairs (matching PortfolioMetrics logic)
				trade_pnl_list = []
				winning_trades_list = []
				losing_trades_list = []

				# Group by ticker
				for ticker in completed['ticker'].unique():
					ticker_trades = completed[completed['ticker'] == ticker].copy()
					ticker_trades = ticker_trades.sort_values('created_at')

					buys = ticker_trades[ticker_trades['operation'].str.upper() == 'BUY']
					sells = ticker_trades[ticker_trades['operation'].str.upper() == 'SELL']

					# Pair buys with sells
					for _, buy in buys.iterrows():
						# Find next sell
						next_sells = sells[sells['created_at'] > buy['created_at']]
						if not next_sells.empty:
							sell = next_sells.iloc[0]
							buy_price = float(buy.get('price', 0))
							sell_price = float(sell.get('price', 0))
							quantity = float(buy.get('quantity', 0))

							if buy_price > 0 and quantity > 0:
								# Calculate P&L
								pnl = (sell_price - buy_price) * quantity
								pnl_pct = ((sell_price - buy_price) / buy_price * 100)

								trade_pnl_list.append(pnl_pct)

								if pnl_pct > 0:
									winning_trades_list.append(pnl_pct)
								else:
									losing_trades_list.append(pnl_pct)

				# Calculate metrics from paired trades
				if trade_pnl_list:
					total_closed = len(trade_pnl_list)
					win_count = len(winning_trades_list)

					# Win rate
					result["win_rate_pct"] = float((win_count / total_closed * 100) if total_closed > 0 else 0.0)

					# Best and worst trades
					result["best_trade_pct"] = float(max(trade_pnl_list) if trade_pnl_list else 0.0)
					result["worst_trade_pct"] = float(min(trade_pnl_list) if trade_pnl_list else 0.0)

					# Average winning and losing trades
					if winning_trades_list:
						result["avg_winning_trade_pct"] = float(sum(winning_trades_list) / len(winning_trades_list))
					if losing_trades_list:
						result["avg_losing_trade_pct"] = float(sum(losing_trades_list) / len(losing_trades_list))

					# Profit factor
					gross_profit = sum(winning_trades_list) if winning_trades_list else 0
					gross_loss = abs(sum(losing_trades_list)) if losing_trades_list else 0
					if gross_loss > 0:
						result["profit_factor"] = float(gross_profit / gross_loss)
					elif gross_profit > 0:
						# No losing trades yet: matches the no-losses convention in
						# tools/portfolio/metrics.py. float('inf') would serialize to
						# non-standard JSON ("Infinity") and break WebSocket consumers.
						result["profit_factor"] = 1.0

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
							result["return_pct"] = float((current_value - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0.0
			except Exception as e:
				self.logger.debug(f"Could not calculate portfolio history: {str(e)}")
				# Fallback: estimate from trades PnL
				if len(completed) > 0:
					total_pnl = pd.to_numeric(completed.get('pnl', pd.Series()), errors='coerce').fillna(0).sum()
					result["portfolio_value"] = initial_capital + total_pnl
					result["return_pct"] = float((total_pnl / initial_capital * 100) if initial_capital > 0 else 0.0)

			return result
		except Exception as e:
			self.logger.exception(f"Failed to calculate daily metrics for {portfolio_name} on {current_date}: {str(e)}")
			return {"date": current_date.isoformat()}

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Execute backtest loop over trading days.

		Args:
			input_data: Dict with keys:
				- strategy_name (required): Name of strategy to backtest
				- start_date (optional): Start date as string YYYY-MM-DD or date object
				- end_date (optional): End date as string YYYY-MM-DD or date object (default: today)
				- lookback_days (optional): Days back from end_date if start_date not provided (default: 365)
				- portfolio_name (optional): Portfolio to run against (default: strategy_name)
				- backtest_id (optional): Pre-generated backtest ID (e.g. for WebSocket registration
				  before this call starts)

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
		# Use backtest_id from input if provided (e.g., pre-generated by an API caller)
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

		# Invalidate blacklist cache to ensure fresh ticker filtering for this run
		from tools.universe.blacklist import invalidate_blacklist_cache
		invalidate_blacklist_cache()

		# Load tickers via StrategyAgent
		strategy_agent = StrategyAgent(f"strategy[{strategy_name}]", self.context)
		strategy_result = strategy_agent.run(input_data)
		self.agents_executed.append(strategy_agent.name)
		if strategy_result.get("status") == "error":
			return strategy_result

		# Load data history via DataAgent
		data_agent = DataAgent(f"data[{strategy_name}]", self.context)
		data_result = data_agent.run({})
		self.agents_executed.append(data_agent.name)
		if data_result.get("status") == "error":
			return data_result

		# Calculate alphas via WatchlistAlphasAgent
		alphas_agent = WatchlistAlphasAgent(f"alphas[{strategy_name}]", self.context)
		alphas_result = alphas_agent.run({})
		self.agents_executed.append(alphas_agent.name)
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
		# Derive portfolio name from strategy if not provided (matches portfolio naming convention)
		portfolio_name = input_data.get("portfolio_name") or self.context.get("portfolio_name") or strategy_name
		self.context.set("portfolio_name", portfolio_name)

		# Auto-wire default phase agents if the caller didn't inject their own via
		# set_premarket_flow/set_market_flow/set_postmarket_flow (e.g. for tests)
		if self.pre_market_flow is None:
			from agents.market_prep.agent import MarketPrepAgent
			self.pre_market_flow = MarketPrepAgent(strategy_name, context=self.context)
		if self.market_flow is None:
			from agents.market_process.agent import MarketProcessAgent
			self.market_flow = MarketProcessAgent(context=self.context)
		if self.post_market_flow is None:
			from agents.market_close.agent import MarketCloseAgent
			self.post_market_flow = MarketCloseAgent(strategy_name, context=self.context)

		# Wait for at least one WebSocket connection before starting, so the frontend
		# has time to connect and receive real-time progress updates.
		if self.websocket_enabled:
			ws_manager = get_websocket_manager()
			wait_start = time.time()
			while time.time() - wait_start < 10:
				if ws_manager.get_connection_count(backtest_id) > 0:
					self.logger.info("WebSocket client connected, starting backtest")
					break
				time.sleep(0.1)
			else:
				self.logger.info("No WebSocket client connected after 10s, starting backtest anyway")

		# Include last trading day if we have data for the next day to execute trades:
		# check for any data after the last trading day and, if found, append it as a
		# synthetic next_date before computing trading_days_to_process/total_trading_days
		# below, so both reflect the actual (possibly extended) list exactly once.
		if trading_days:
			last_day = trading_days[-1]
			future_dates = [d for d in day_data_cache.keys() if d > last_day]
			if future_dates:
				next_available_date = min(future_dates)
				trading_days.append(next_available_date)
				self.logger.info(f"Including final trading day {last_day} (using {next_available_date} for execution)")

		trading_days_to_process = trading_days[:-1]
		backtest["total_trading_days"] = len(trading_days)

		# Get initial capital/currency from strategy config
		strategy_config = self.context.get("strategy_config") or {}
		initial_capital = strategy_config.get("backtest", {}).get("initial_capital", 100000.0)
		currency = strategy_config.get("backtest", {}).get("currency") or strategy_config.get("currency", "EUR")
		self.logger.info(f"Using initial capital: ${initial_capital:.2f} {currency}")

		# Initialize portfolio with correct initial_capital before backtest loop
		from tools.portfolio import PortfolioManager
		try:
			pm = PortfolioManager(context=self.context.__dict__)
			# Check if portfolio already exists
			portfolio_path = pm.portfolios_dir / pm._normalize_portfolio_name(portfolio_name)
			if not portfolio_path.exists():
				# Create portfolio with correct initial_capital
				create_result = pm.create_portfolio(
					name=portfolio_name,
					portfolio_type="paper",
					currency=currency,
					description=f"Backtest for {strategy_name}",
					initial_capital=initial_capital
				)
				self.logger.info(f"Created portfolio '{portfolio_name}' with initial capital ${initial_capital:.2f}")
			else:
				# Portfolio exists - update initial_capital if different
				metadata = pm._get_portfolio_metadata(portfolio_name)
				if metadata.get("initial_capital") != initial_capital:
					metadata["initial_capital"] = initial_capital
					pm._save_portfolio_metadata(portfolio_name, metadata)
					self.logger.info(f"Updated portfolio '{portfolio_name}' initial capital to ${initial_capital:.2f}")
		except Exception as e:
			self.logger.warning(f"Could not initialize portfolio metadata: {e}")

		# Use progress bar if tqdm is available
		iterator = tqdm(enumerate(trading_days_to_process), total=len(trading_days_to_process), desc="Backtest Progress") if HAS_TQDM else enumerate(trading_days_to_process)

		for i, current_date in iterator:
			next_date = trading_days[i + 1]

			# Pre-market phase: signals based on data up to current_date
			self.context.set("current_date", current_date)
			# Slice data_history to current_date so watchlist changes daily
			self._set_data_history_for_date(data_history, current_date)
			self._run_phase(self.pre_market_flow, "Pre-market", {
				"date": current_date.isoformat(),
				"strategy_name": strategy_name,
				"portfolio_name": portfolio_name,
			}, current_date)

			# Increment to next trading day
			self.context.set("current_date", next_date)

			# Pass next_date OHLCV data to market flow (use cached data, not stale previous day data)
			next_day_data = day_data_cache.get(next_date, {})
			self.logger.debug(f"BacktestAgent: next_date={next_date}, next_day_data has {len(next_day_data)} tickers")
			self.context.set("next_day_data", next_day_data)

			# Market phase: execute on next_date prices with pre-loaded data
			self._run_phase(self.market_flow, "Market", {
				"date": next_date.isoformat(),
				"strategy_name": strategy_name,
				"portfolio_name": portfolio_name,
			}, next_date)

			# Post-market phase: update after close
			self._run_phase(self.post_market_flow, "Post-market", {
				"date": next_date.isoformat(),
				"strategy_name": strategy_name,
				"portfolio_name": portfolio_name,
			}, next_date)

			# Flush journal and orders to disk at end of day
			try:
				journal = Journal(portfolio_name, context=self.context.__dict__)
				journal.flush()
				orders = Orders(portfolio_name, context=self.context.__dict__)
				orders.flush()
			except Exception as e:
				self.logger.warning(f"Failed to flush journal/orders for {portfolio_name}: {str(e)}")

			# Calculate daily metrics for this date (skip if websocket disabled to improve performance)
			if self.websocket_enabled:
				daily_result = self._calculate_daily_metrics(portfolio_name, next_date, start_date, initial_capital=initial_capital)
			else:
				daily_result = {"date": next_date.isoformat()}

			backtest["daily_results"].append(daily_result)

			# Broadcast daily progress to WebSocket clients (only if enabled)
			if self.websocket_enabled:
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
					self.logger.exception(f"WebSocket broadcast failed: {str(e)}")

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

		# Flush journal and orders one final time (each day already flushes, this is a safety net)
		try:
			journal = Journal(portfolio_name, context=self.context.__dict__)
			journal.flush()
			orders = Orders(portfolio_name, context=self.context.__dict__)
			orders.flush()
		except Exception as e:
			self.logger.warning(f"Failed to flush journal/orders for {portfolio_name}: {str(e)}")

		# Calculate and save metrics
		# Saved under both "metrics" and "portfolio_metrics" - the latter is what the CLI
		# and the disk-persisted backtest result (read back via BacktestManager.get_backtest)
		# read from.
		metrics_result = {}
		try:
			metrics = PortfolioMetrics(context=self.context.__dict__)
			metrics_result = metrics.calculate_backtest_metrics(
				portfolio_name,
				start_date,
				end_date,
				initial_capital
			)

			if metrics_result:
				backtest["metrics"] = metrics_result
				backtest["portfolio_metrics"] = metrics_result
				save_metrics_result = backtest_manager.save_metrics(strategy_name, backtest_id, metrics_result)
				if save_metrics_result.get("status") == "success":
					self.logger.info(f"Saved metrics to {save_metrics_result.get('file')}")
				else:
					self.logger.warning(f"Failed to save metrics: {save_metrics_result.get('message')}")
		except Exception as e:
			self.logger.warning(f"Could not calculate metrics: {str(e)}")

		# Final portfolio snapshot
		try:
			from tools.portfolio import PortfolioManager
			pm = PortfolioManager(context=self.context.__dict__)
			final_portfolio = pm.get_portfolio_summary(portfolio_name)
			if final_portfolio:
				backtest["final_portfolio"] = final_portfolio
		except Exception as e:
			self.logger.warning(f"Could not get final portfolio summary: {str(e)}")

		# Research agent: identify issues in the resulting journal/orders
		try:
			research_agent = ResearchAgent()
			research_agent.context = self.context
			research_result = research_agent.process()
			research_output = research_result.get("output", {})
			backtest["research"] = {
				"journal_analysis": research_output.get("journal_analysis", {}),
				"order_analysis": research_output.get("order_analysis", {}),
				"identified_issues": research_output.get("identified_issues", []),
				"severity_level": research_output.get("severity_level", "none"),
				"issue_count": research_output.get("total_issues", 0),
			}
		except Exception as e:
			self.logger.warning(f"Could not run research agent: {str(e)}")

		# Save execution context (metrics, ticker counts) for debugging/audit
		try:
			import json
			from pathlib import Path
			context_data = {
				"backtest_id": backtest_id,
				"strategy": strategy_name,
				"start_date": str(start_date),
				"end_date": str(end_date),
				"metadata": self.context.get("metadata") or {},
				"execution_history": self.context.get("execution_history") or [],
			}
			context_file = Path(backtest_dir) / "context.json"
			with open(context_file, 'w') as f:
				json.dump(context_data, f, indent=2, default=str)
			self.logger.debug(f"Saved execution context to {context_file}")
		except Exception as e:
			self.logger.warning(f"Could not save context.json: {e}")

		# Broadcast completion to WebSocket clients
		if self.websocket_enabled:
			try:
				import asyncio
				ws_manager = get_websocket_manager()

				async def send_completion():
					await ws_manager.broadcast_backtest_complete(
						backtest_id=backtest_id,
						strategy_name=strategy_name,
						metrics=metrics_result or {},
						days_processed=backtest.get("days_processed", 0)
					)

				asyncio.run(send_completion())
			except Exception as e:
				self.logger.warning(f"Could not send WebSocket completion message: {e}")

		return {
			"status": "success",
			"input": input_data,
			"output": backtest,
			"message": f"Backtest {backtest_id} completed for {strategy_name}",
		}

	def _run_phase(
		self,
		phase: Optional[PhasePipeline],
		label: str,
		payload: Dict[str, Any],
		current_date: date,
	) -> Dict[str, Any]:
		"""Run one backtest phase, converting any raised exception into an error dict.

		Phases are called via .process() directly (not .run()), bypassing Agent.run()'s
		own exception safety net - and not every phase agent guards its own fatal
		sub-agent failures (MarketPrepAgent does; MarketCloseAgent/MarketProcessAgent
		don't). Without this, a single bad trading day could raise an uncaught
		exception here and crash the entire multi-day backtest with no partial
		results saved.

		Args:
			phase: The phase agent/flow to run (no-op if None)
			label: Human-readable phase name for log messages (e.g. "Pre-market")
			payload: Input dict passed to phase.process()
			current_date: The trading date this phase is running for (for logging)

		Returns:
			The phase's response dict, or a synthetic error dict if it raised
		"""
		if not phase:
			return {"status": "success"}

		phase.context = self.context
		try:
			result = phase.process(payload)
		except Exception as e:
			self.logger.exception(f"{label} phase raised on {current_date}: {e}")
			return {"status": "error", "message": str(e)}

		if result.get("status") not in (None, "success"):
			self.logger.warning(f"{label} phase returned non-success on {current_date}: {result.get('message')}")
		return result

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
		self.logger.debug(f"Sliced data_history to {current_date} for MarketPrepAgent")