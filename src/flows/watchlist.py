"""Watchlist flow for managing stock watchlists."""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure src is in path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from agents.core.context import AgentContext
from agents.strategy.agent import StrategyAgent
from agents.watchlist.agent import WatchListAgent


class WatchlistFlow:
	"""Orchestrates a workflow for building and processing watchlists.

	Combines StrategyAgent and WatchListAgent to create a watchlist based on
	strategy configuration and input data.
	"""

	def __init__(self, strategy: str):
		"""Initialize watchlist flow with strategy.

		Args:
			strategy: Strategy name to use for watchlist generation
		"""
		self.strategy_name = strategy
		self.context = AgentContext()
		self.strategy_agent = StrategyAgent(f"StrategyAgent[{strategy}]", self.context)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process input data through watchlist workflow.

		Executes the strategy agent and watchlist agent in sequence, sharing
		context to pass data between them.

		Args:
			input_data: Input dictionary for strategy processing

		Returns:
			Response dictionary with status and watchlist result
		"""
		if input_data is None:
			input_data = {}

		# Execute strategy agent
		strategy_result = self.strategy_agent.run(input_data)
		if strategy_result.get("status") == "error":
			return {
				"status": "error",
				"message": f"Strategy failed: {strategy_result.get('message')}",
			}

		# Pass strategy result to context for watchlist agent
		self.context.set("strategy_result", strategy_result)

		# Execute watchlist agent
		watchlist_agent = WatchListAgent("WatchListAgent", self.context)
		watchlist_result = watchlist_agent.run(input_data)

		if watchlist_result.get("status") == "error":
			return {
				"status": "error",
				"message": f"Watchlist failed: {watchlist_result.get('message')}",
			}

		# Extract watchlist from context
		watchlist = self.context.get("watchlist") or watchlist_result.get("output", {})

		return {
			"status": "success",
			"watchlist": watchlist,
			"strategy": self.strategy_name,
		}
