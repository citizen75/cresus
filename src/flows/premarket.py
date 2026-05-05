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
		"""Set up default steps for pre-market flow."""
		# Strategy step - load tickers and strategy config
		strategy_agent = StrategyAgent(f"StrategyAgent[{self.strategy_name}]", self.context)
		self.add_step(strategy_agent, step_name="strategy", required=True)

		# Data step - fetch data and calculate indicators for all tickers
		# Skip if already in context (backtest mode - data loaded by BacktestAgent)
		data_agent = DataAgent(f"DataAgent[{self.strategy_name}]", self.context)
		self.add_step(data_agent, step_name="data", required=True)

		# Watchlist step - filter tickers based on strategy criteria (uses data from previous step)
		watchlist_agent = WatchListAgent("WatchListAgent", self.context)
		self.add_step(watchlist_agent, step_name="watchlist", required=True)

		# Signals step - generate trading signals on watchlist tickers
		signals_agent = SignalsAgent("SignalsAgent", self.context)
		self.add_step(signals_agent, step_name="signals", required=True)

		# Entry analysis step - analyze trade entry points for watchlist tickers
		entry_agent = EntryAgent("EntryAgent", self.context)
		self.add_step(entry_agent, step_name="entry", required=False)

		# Entry order step - convert entry signals to executable orders
		entry_order_agent = EntryOrderAgent("EntryOrderAgent", self.context)
		self.add_step(entry_order_agent, step_name="entry_order", required=False)

		# Save watchlist step - persist watchlist to disk with OHLCV and signal data
		save_agent = SaveWatchlistAgent("SaveWatchlistAgent", self.strategy_name, context=self.context)
		self.add_step(save_agent, step_name="save_watchlist", required=False)

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

		# Execute parent flow logic
		result = super().process(flow_input)

		# Extract and include watchlist data
		watchlist = self.context.get("watchlist") or []
		result["watchlist"] = watchlist

		# Extract and include signals data and scores
		signals = self.context.get("signals") or {}
		result["signals"] = signals

		ticker_scores = self.context.get("ticker_scores") or {}
		result["ticker_scores"] = ticker_scores

		# Extract sorted tickers from signals agent result
		signals_step = self.get_step("signals")
		if signals_step:
			signals_result = signals_step.get("result")
			if signals_result and signals_result.get("status") == "success":
				output = signals_result.get("output", {})
				sorted_tickers = output.get("sorted_tickers")
				if sorted_tickers:
					result["sorted_tickers"] = sorted_tickers
				top_ticker = output.get("top_ticker")
				top_score = output.get("top_score")
				if top_ticker:
					result["top_ticker"] = top_ticker
					result["top_score"] = top_score

		# Extract entry recommendations from entry step
		entry_step = self.get_step("entry")
		if entry_step:
			entry_step_result = entry_step.get("result")
			if entry_step_result and entry_step_result.get("status") == "success":
				output = entry_step_result.get("output", {})
				entry_recommendations = output.get("top_opportunities")
				if entry_recommendations:
					result["entry_recommendations"] = entry_recommendations

		# Extract executable orders from entry_order step
		entry_order_step = self.get_step("entry_order")
		if entry_order_step:
			entry_order_result = entry_order_step.get("result")
			if entry_order_result and entry_order_result.get("status") == "success":
				output = entry_order_result.get("output", {})
				orders = output.get("orders")
				if orders:
					result["executable_orders"] = orders
					result["orders_count"] = len(orders)
				execution_results = output.get("execution_results")
				if execution_results:
					result["execution_results"] = execution_results

		# Extract watchlist save result from save_watchlist step
		save_step = self.get_step("save_watchlist")
		if save_step:
			save_step_result = save_step.get("result")
			if save_step_result:
				result["watchlist_saved"] = save_step_result.get("output")

		# Add strategy-specific fields to response
		result["strategy"] = self.strategy_name

		return result

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
