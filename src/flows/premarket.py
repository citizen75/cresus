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
			# Live: Signals on all tickers first, then Watchlist
			signals_agent = SignalsAgent("SignalsAgent", self.context)
			self.add_step(signals_agent, step_name="signals", required=True)

			# Watchlist step - filter tickers based on strategy criteria and signal scores
			watchlist_agent = WatchListAgent("WatchListAgent", self.context)
			self.add_step(watchlist_agent, step_name="watchlist", required=True)

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

		# Store target date in context for DataAgent to filter data
		target_date = flow_input.get("date")
		if target_date:
			self.context.set("target_date", target_date)

		# Execute parent flow logic
		result = super().process(flow_input)

		# After all steps complete, slice data to target_date if provided
		# Then re-run entry and downstream agents with sliced data
		# This ensures entry_filter evaluates on correct historical rows
		if target_date:
			self._set_data_history_for_date(self.context, target_date)
			self.logger.info(f"Sliced data_history to {target_date}")

			# Re-run entry step with sliced data
			entry_step = self.get_step("entry")
			if entry_step:
				self.logger.debug("Re-running entry step with sliced data")
				entry_result = entry_step.get("agent").process({})
				entry_step["result"] = entry_result
				self.context.set("entry_recommendations", entry_result.get("output", {}).get("top_opportunities", []))

				# Re-run entry_order step with updated entry_recommendations
				entry_order_step = self.get_step("entry_order")
				if entry_order_step:
					self.logger.debug("Re-running entry_order step with updated recommendations")
					eo_result = entry_order_step.get("agent").process({})
					entry_order_step["result"] = eo_result

		# === FINAL OUTPUT: Keep only watchlist and orders ===

		# Extract final watchlist
		watchlist = self.context.get("watchlist") or []
		result["watchlist"] = watchlist

		# Extract final orders
		entry_order_step = self.get_step("entry_order")
		if entry_order_step:
			entry_order_result = entry_order_step.get("result")
			if entry_order_result and entry_order_result.get("status") == "success":
				output = entry_order_result.get("output", {})
				orders = output.get("orders") or []
				result["orders"] = orders
		else:
			result["orders"] = []

		# === CLEANUP: Remove all intermediate context variables ===
		# Keep only: watchlist, data_history, strategy_config (needed for other flows)
		# Remove: signals, ticker_scores, entry_scores, timing_scores, rr_metrics, etc.
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

		Removes: signals, ticker_scores, entry_scores, timing_scores, rr_metrics,
		entry_recommendations, filtered_duplicate_items, sorted_tickers, etc.

		Keeps: watchlist, data_history, strategy_config, portfolio_name, strategy_name
		"""
		# Variables to remove (intermediate calculations)
		to_remove = [
			"signals",
			"ticker_scores",
			"entry_scores",
			"timing_scores",
			"rr_metrics",
			"entry_recommendations",
			"filtered_duplicate_items",
			"sorted_tickers",
			"top_ticker",
			"top_score",
			"_data_sliced_for_entry",
		]

		for var in to_remove:
			if hasattr(self.context, var):
				delattr(self.context, var)
				self.logger.debug(f"Removed context variable: {var}")

	def _strategy_to_portfolio_name(self, strategy_name: str) -> str:
		"""Convert strategy name to portfolio name format.

		Examples:
			momentum_cac → Momentum cac
			default_strategy → Default strategy

		Args:
			strategy_name: Strategy name to convert

		Returns:
			Portfolio name with first letter capitalized and spaces instead of underscores
		"""
		# Replace underscores with spaces
		name = strategy_name.replace("_", " ")
		# Capitalize only the first letter
		return name[0].upper() + name[1:] if name else name

	def __repr__(self) -> str:
		"""String representation of the flow."""
		return f"PreMarketFlow(strategy='{self.strategy_name}', steps={len(self.steps)})"
