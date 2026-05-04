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

		# Save watchlist step - persist watchlist to disk with OHLCV and signal data
		save_agent = SaveWatchlistAgent("SaveWatchlistAgent", self.strategy_name)
		save_agent.context = self.context
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

		# Extract watchlist save result from save_watchlist step
		save_step = self.get_step("save_watchlist")
		if save_step:
			save_step_result = save_step.get("result")
			if save_step_result:
				result["watchlist_saved"] = save_step_result.get("output")

		# Add strategy-specific fields to response
		result["strategy"] = self.strategy_name

		return result

	def __repr__(self) -> str:
		"""String representation of the flow."""
		return f"PreMarketFlow(strategy='{self.strategy_name}', steps={len(self.steps)})"
