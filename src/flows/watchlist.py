"""Watchlist flow for managing stock watchlists.

Extends Flow for strategy-specific workflow orchestration.
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


class WatchlistFlow(Flow):
	"""Flow for orchestrating multi-agent watchlist workflows.

	Inherits from Flow and specializes for strategy-based watchlist generation.
	Combines StrategyAgent and WatchListAgent with shared context.
	"""

	def __init__(self, strategy: str):
		"""Initialize watchlist flow with strategy.

		Args:
			strategy: Strategy name to use for watchlist generation
		"""
		super().__init__(f"WatchlistFlow[{strategy}]")
		self.strategy_name = strategy
		self._setup_default_steps()

	def _setup_default_steps(self) -> None:
		"""Set up default steps for watchlist flow."""
		# Strategy step
		strategy_agent = StrategyAgent(f"StrategyAgent[{self.strategy_name}]", self.context)
		self.add_step(strategy_agent, step_name="strategy", required=True)

		# Watchlist step
		watchlist_agent = WatchListAgent("WatchListAgent", self.context)
		self.add_step(watchlist_agent, step_name="watchlist", required=True)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process input data through the watchlist flow.

		Executes strategy and watchlist agents sequentially with shared context.
		Stores strategy results in context for downstream agents.

		Args:
			input_data: Input dictionary for the flow

		Returns:
			Final flow result with watchlist
		"""
		# Execute parent flow logic
		result = super().process(input_data)

		# Store strategy result in context for watchlist agent if strategy was successful
		strategy_step = self.get_step("strategy")
		if strategy_step:
			strategy_result = strategy_step.get("result")
			if strategy_result and strategy_result.get("status") == "success":
				self.context.set("strategy_result", strategy_result)

		# Add strategy-specific fields to response
		result["strategy"] = self.strategy_name

		# Extract and include watchlist data
		watchlist = self.context.get("watchlist") or []
		result["watchlist"] = watchlist

		return result

	def __repr__(self) -> str:
		"""String representation of the flow."""
		return f"WatchlistFlow(strategy='{self.strategy_name}', steps={len(self.steps)})"
