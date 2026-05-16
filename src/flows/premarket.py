"""Pre-market flow for generating pre-market signals on watchlist.

Extends Flow to combine watchlist generation with signal analysis.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure src is in path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from core.flow import Flow
from agents.strategy.agent import StrategyAgent
from agents.watchlist.agent import WatchListAgent
from agents.watchlist.save_agent import SaveWatchlistAgent
from agents.data.agent import DataAgent
from agents.signals.agent import SignalsAgent
from agents.entry.agent import EntryAgent
from agents.entry_order.agent import EntryOrderAgent
from agents.exit.agent import ExitAgent


class PreMarketFlow(Flow):
	"""Flow for pre-market analysis with watchlist and signals.

	Generates a watchlist from strategy criteria, then analyzes signals
	on the watchlist tickers for pre-market decision making.
	"""

	def __init__(self, strategy: str, context: Optional[Any] = None):
		"""Initialize pre-market flow with strategy.

		Args:
			strategy: Strategy name to use for watchlist and signals
			context: Optional AgentContext for shared state
		"""
		super().__init__(f"PreMarketFlow[{strategy}]", context=context)
		self.strategy_name = strategy
		self._setup_default_steps()

	def _setup_default_steps(self) -> None:
		"""Set up default steps for pre-market flow.

		Flow order:
		1. Strategy - load config and tickers
		2. Data - fetch data and calculate indicators
		3. Signals - generate trading signals (backtest: on watchlist; live: on all)
		4. Watchlist - filter and sort tickers for trading
		5. Entry - apply entry_filter to watchlist tickers
		6. Entry_order - create executable orders
		"""
		# Strategy step - load tickers and strategy config
		strategy_agent = StrategyAgent(f"StrategyAgent[{self.strategy_name}]", self.context)
		self.add_step(strategy_agent, step_name="strategy", required=True)

		# Data step - fetch data and calculate indicators for all tickers
		# Skip if already in context (backtest mode - data loaded by BacktestAgent)
		data_agent = DataAgent(f"DataAgent[{self.strategy_name}]", self.context)
		self.add_step(data_agent, step_name="data", required=True)

		# In backtest mode, filter watchlist BEFORE signals to reduce computation
		# This significantly speeds up backtests (filters 258 → ~20 before signal analysis)
		is_backtest = self.context.get("backtest_id") is not None

		if is_backtest:
			# Backtest: Watchlist BEFORE Signals (for speed optimization)
			watchlist_agent = WatchListAgent("WatchListAgent", self.context)
			self.add_step(watchlist_agent, step_name="watchlist", required=True)

			# Signals step - generate trading signals on filtered watchlist only
			signals_agent = SignalsAgent("SignalsAgent", self.context)
			self.add_step(signals_agent, step_name="signals", required=True)
		else:
			# Watchlist step - filter tickers based on strategy criteria and signal scores
			watchlist_agent = WatchListAgent("WatchListAgent", self.context)
			self.add_step(watchlist_agent, step_name="watchlist", required=True)
			# Live: Signals on all tickers first, then Watchlist
			signals_agent = SignalsAgent("SignalsAgent", self.context)
			self.add_step(signals_agent, step_name="signals", required=True)

		# Note: Data slicing to target_date must happen BEFORE entry analysis
		# so that entry_filter evaluates on the correct date's data
		# This is handled explicitly in process() method

		# Entry step - apply entry_filter to watchlist tickers
		entry_agent = EntryAgent("EntryAgent", self.context)
		self.add_step(entry_agent, step_name="entry", required=False)

		# Entry order step - convert entry signals to executable orders
		entry_order_agent = EntryOrderAgent("EntryOrderAgent", self.context)
		self.add_step(entry_order_agent, step_name="entry_order", required=False)

		# Save watchlist step - persist watchlist to disk with OHLCV and signal data
		save_agent = SaveWatchlistAgent("SaveWatchlistAgent", self.strategy_name, context=self.context)
		self.add_step(save_agent, step_name="save_watchlist", required=False)

		# Exit analysis step - evaluate exit conditions and generate SELL orders
		# Runs after entry orders are created
		exit_agent = ExitAgent("ExitAgent", self.context)
		self.add_step(exit_agent, step_name="exit", required=False)

	def process(self, input_data: Optional[Dict[str, Any]] = None, save: bool = True) -> Dict[str, Any]:
		"""Process input data through the pre-market flow.

		Executes strategy, watchlist, data, signals, and save agents sequentially.
		Generates a watchlist, analyzes signals, and optionally persists to disk.

		Args:
			input_data: Input dictionary for the flow
			save: Toggle to enable/disable watchlist saving (default: True)

		Returns:
			Final flow result with watchlist and signals
		"""
		# Prepare input data with save toggle for SaveWatchlistAgent
		flow_input = input_data or {}
		flow_input["save_enabled"] = save

		# Set portfolio name from strategy if not already set
		# This allows EntryOrderAgent to execute orders in the correct portfolio
		if "portfolio_name" not in flow_input:
			# Transform strategy name to portfolio name format (e.g., momentum_cac → Momentum cac)
			portfolio_name = self._strategy_to_portfolio_name(self.strategy_name)
			flow_input["portfolio_name"] = portfolio_name

		# Ensure portfolio_name is set in context for sub-agents
		self.context.set("portfolio_name", flow_input["portfolio_name"])
		self.context.set("strategy_name", self.strategy_name)

		# Store target date in context for DataAgent and pre-slicing
		target_date = flow_input.get("date")
		is_backtest = self.context.get("backtest_id") is not None

		if target_date:
			self.context.set("target_date", target_date)

		# Execute parent flow logic
		result = super().process(flow_input)

		# PRE-SLICE DATA IN LIVE MODE (after data loads, before other agents use it)
		# Note: This check is here as safety, but slicing should happen in DataAgent for live mode
		# In backtest mode, BacktestAgent already pre-slices before calling premarket
		if target_date and not is_backtest:
			# Verify data is sliced to target_date
			data_history = self.context.get("data_history") or {}
			if data_history and not self.context.get("_data_sliced_for_entry"):
				# Data wasn't pre-sliced (shouldn't happen with fix), do it now
				self._set_data_history_for_date(self.context, target_date)
				self.logger.warning(f"Pre-slicing data to {target_date} post-execution (should pre-slice earlier)")
				self.context.set("_data_sliced_for_entry", True)

		# === FINAL OUTPUT: Watchlist and Orders ===
		# Plus display-essential data for CLI output

		# Extract final watchlist
		watchlist = self.context.get("watchlist") or []
		result["watchlist"] = watchlist

		# Extract strategy name (needed for CLI display header)
		result["strategy"] = self.strategy_name

		# Extract ticker scores (needed for CLI display table)
		ticker_scores = self.context.get("ticker_scores") or {}
		result["ticker_scores"] = ticker_scores

		# Extract indicators (needed for CLI display header and columns)
		strategy_config = self.context.get("strategy_config") or {}
		result["indicators"] = strategy_config.get("indicators", [])

		# Extract data_history (needed for CLI display indicator values)
		data_history = self.context.get("data_history") or {}
		result["data_history"] = data_history

		# Extract target date (needed for CLI display header)
		if target_date:
			result["target_date"] = target_date

		# Extract final orders - renamed from executable_orders for clarity
		entry_order_step = self.get_step("entry_order")
		if entry_order_step:
			entry_order_result = entry_order_step.get("result")
			if entry_order_result and entry_order_result.get("status") == "success":
				output = entry_order_result.get("output", {})
				orders = output.get("orders") or []
				result["orders"] = orders
				# Also keep executable_orders for backward compatibility with CLI
				result["executable_orders"] = orders
				result["orders_count"] = len(orders)
		else:
			result["orders"] = []
			result["executable_orders"] = []
			result["orders_count"] = 0

		# === CLEANUP: Remove unnecessary intermediate context variables ===
		# Remove: signals, entry_scores, timing_scores, rr_metrics, etc.
		# Keep: data_history, strategy_config, watchlist (needed for other flows)
		self._cleanup_context()

		return result

	def _set_data_history_for_date(self, context: Any, date_str: str) -> None:
		"""Slice data_history to include only data up to a specific date.

		This allows viewing the watchlist as it was on a specific trading date.

		Args:
			context: AgentContext containing data_history
			date_str: Date string in YYYY-MM-DD format
		"""
		import pandas as pd
		from datetime import date as date_type

		# Parse date string
		try:
			target_date = date_type.fromisoformat(date_str)
		except (ValueError, TypeError):
			self.logger.warning(f"Invalid date format: {date_str}, using all available data")
			return

		data_history = context.get("data_history")
		if not data_history:
			return

		# Slice each ticker's data to target_date and earlier
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

			# Extract dates and filter to target_date and earlier
			dates = timestamps.dt.date
			mask = dates <= target_date
			sliced_history[ticker] = df[mask].copy()

		context.set("data_history", sliced_history)
		self.logger.info(f"Sliced data_history to {date_str} for watchlist analysis")

	def _cleanup_context(self) -> None:
		"""Remove intermediate context variables, keeping only essential ones.

		Removes: signals, entry_scores, timing_scores, rr_metrics,
		filtered_duplicate_items, sorted_tickers, etc.

		Keeps: watchlist, data_history, strategy_config, ticker_scores
		(needed for CLI display and downstream flows)

		Note: entry_recommendations is no longer created (watchlist dict now contains all data)
		"""
		# Variables to remove (intermediate calculations not needed in final output)
		to_remove = [
			"signals",  # Signal details (not needed for display)
			"entry_scores",  # Entry signal scores (intermediate)
			"timing_scores",  # Timing analysis scores (intermediate)
			"rr_metrics",  # Risk/reward metrics (intermediate)
			"filtered_duplicate_items",  # Duplicate filter details (intermediate)
			"sorted_tickers",  # Sorted ticker details (superseded by watchlist)
			"top_ticker",  # Top ticker (not critical for final output)
			"top_score",  # Top score (not critical for final output)
			"_data_sliced_for_entry",  # Internal flag
		]

		for var in to_remove:
			if hasattr(self.context, var):
				delattr(self.context, var)
				self.logger.debug(f"Cleaned up context variable: {var}")

	def _strategy_to_portfolio_name(self, strategy_name: str) -> str:
		"""Convert strategy name to portfolio name.

		Uses strategy name directly as portfolio name for consistency with
		portfolio naming conventions (e.g., etf_pea_trend).

		Args:
			strategy_name: Strategy name to convert

		Returns:
			Portfolio name (same as strategy name)
		"""
		return strategy_name

	def __repr__(self) -> str:
		"""String representation of the flow."""
		return f"PreMarketFlow(strategy='{self.strategy_name}', steps={len(self.steps)})"
