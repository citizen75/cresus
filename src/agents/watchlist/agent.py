"""Watchlist agent for managing stock watchlists."""

from typing import Any, Dict, Optional
from ..core.agent import Agent


class WatchListAgent(Agent):
	"""Agent for managing a watchlist of stocks."""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process the input data and return a watchlist response.

		This method should be overridden by subclasses to implement specific
		watchlist logic. Base implementation returns empty watchlist.

		Args:
			input_data: Input data for watchlist generation

		Returns:
			Response dictionary with watchlist in output
		"""
		if input_data is None:
			input_data = {}

		# Base implementation returns empty watchlist
		watchlist = []

		# Store in context if strategy data exists
		strategy_result = self.context.get("strategy_result")
		if strategy_result:
			output = strategy_result.get("output") if isinstance(strategy_result, dict) else {}
			watchlist = output.get("tickers", []) if isinstance(output, dict) else []

		self.context.set("watchlist", watchlist)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"watchlist": watchlist,
				"count": len(watchlist),
			},
		}
