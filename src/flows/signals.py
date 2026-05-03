"""Signals flow for generating trading signals.

Extends Flow for strategy-specific signal generation workflow.
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
from agents.data.agent import DataAgent
from agents.signals.agent import SignalsAgent
from tools.watchlist import WatchlistManager


class SignalsFlow(Flow):
	"""Flow for orchestrating signal generation workflows.

	Inherits from Flow and specializes for strategy-based signal generation.
	Combines DataAgent (data fetching and indicator calculation) with SignalsAgent
	(signal generation) using shared context.
	"""

	def __init__(self, strategy: str):
		"""Initialize signals flow with strategy.

		Args:
			strategy: Strategy name to use for signal generation
		"""
		super().__init__(f"SignalsFlow[{strategy}]")
		self.strategy_name = strategy
		self._setup_default_steps()

	def _setup_default_steps(self) -> None:
		"""Set up default steps for signals flow."""
		# Strategy step - load tickers and strategy config
		strategy_agent = StrategyAgent(f"StrategyAgent[{self.strategy_name}]", self.context)
		self.add_step(strategy_agent, step_name="strategy", required=True)

		# Data step - fetch data and calculate indicators
		data_agent = DataAgent(f"DataAgent[{self.strategy_name}]", self.context)
		self.add_step(data_agent, step_name="data", required=True)

		# Signals step - generate trading signals
		signals_agent = SignalsAgent("SignalsAgent", self.context)
		self.add_step(signals_agent, step_name="signals", required=True)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process input data through the signals flow.

		Executes strategy, data, and signals agents sequentially with shared context.
		StrategyAgent loads tickers and strategy config for downstream agents.
		Saves signals data with OHLCV to CSV.

		Args:
			input_data: Input dictionary for the flow

		Returns:
			Final flow result with signals
		"""
		# Execute parent flow logic (StrategyAgent loads config, DataAgent fetches data, SignalsAgent generates signals)
		result = super().process(input_data or {})

		# Store strategy result in context if data was successful
		data_step = self.get_step("data")
		if data_step:
			data_result = data_step.get("result")
			if data_result and data_result.get("status") == "success":
				self.context.set("data_result", data_result)

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

		# Save signals data with OHLCV
		tickers = self.context.get("tickers") or []
		if tickers and ticker_scores:
			data_history = self.context.get("data_history") or {}
			watchlist_manager = WatchlistManager(f"{self.strategy_name}_signals")
			save_result = watchlist_manager.save(tickers, ticker_scores, data_history)
			result["signals_saved"] = save_result

		# Add strategy-specific fields to response
		result["strategy"] = self.strategy_name

		return result

	def __repr__(self) -> str:
		"""String representation of the flow."""
		return f"SignalsFlow(strategy='{self.strategy_name}', steps={len(self.steps)})"
