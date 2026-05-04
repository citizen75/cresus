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
from agents.data.agent import DataAgent
from agents.signals.agent import SignalsAgent
from tools.watchlist import WatchlistManager


class PreMarketFlow(Flow):
	"""Flow for pre-market analysis with watchlist and signals.

	Generates a watchlist from strategy criteria, then analyzes signals
	on the watchlist tickers for pre-market decision making.
	"""

	def __init__(self, strategy: str):
		"""Initialize pre-market flow with strategy.

		Args:
			strategy: Strategy name to use for watchlist and signals
		"""
		super().__init__(f"PreMarketFlow[{strategy}]")
		self.strategy_name = strategy
		self._setup_default_steps()

	def _setup_default_steps(self) -> None:
		"""Set up default steps for pre-market flow."""
		# Strategy step - load tickers and strategy config
		strategy_agent = StrategyAgent(f"StrategyAgent[{self.strategy_name}]", self.context)
		self.add_step(strategy_agent, step_name="strategy", required=True)

		# Data step - fetch data and calculate indicators for all tickers
		data_agent = DataAgent(f"DataAgent[{self.strategy_name}]", self.context)
		self.add_step(data_agent, step_name="data", required=True)

		# Watchlist step - filter tickers based on strategy criteria (uses data from previous step)
		watchlist_agent = WatchListAgent("WatchListAgent", self.context)
		self.add_step(watchlist_agent, step_name="watchlist", required=True)

		# Signals step - generate trading signals on watchlist tickers
		signals_agent = SignalsAgent("SignalsAgent", self.context)
		self.add_step(signals_agent, step_name="signals", required=True)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process input data through the pre-market flow.

		Executes strategy, watchlist, data, and signals agents sequentially.
		Generates a watchlist first, then analyzes signals on watchlist tickers.
		Saves watchlist with OHLCV and signal data to CSV.

		Args:
			input_data: Input dictionary for the flow

		Returns:
			Final flow result with watchlist and signals
		"""
		# Execute parent flow logic
		result = super().process(input_data or {})

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

		# Save watchlist with OHLCV and signal data
		if ticker_scores:
			data_history = self.context.get("data_history") or {}
			watchlist_manager = WatchlistManager(self.strategy_name)
			# Use sorted_tickers from signals if available, limited by max_count
			tickers_to_save = []
			if result.get("sorted_tickers"):
				# Limit to max_count from strategy config (default 20)
				strategy_config = self.context.get("strategy_config") or {}
				max_count = strategy_config.get("watchlist", {}).get("parameters", {}).get("tickers", {}).get("max_count", 20)
				top_tickers = result["sorted_tickers"][:max_count]
				tickers_to_save = [t["ticker"] for t in top_tickers]
			elif watchlist:
				tickers_to_save = watchlist

			if tickers_to_save:
				save_result = watchlist_manager.save(tickers_to_save, ticker_scores, data_history)
				result["watchlist_saved"] = save_result

		# Add strategy-specific fields to response
		result["strategy"] = self.strategy_name

		return result

	def __repr__(self) -> str:
		"""String representation of the flow."""
		return f"PreMarketFlow(strategy='{self.strategy_name}', steps={len(self.steps)})"
