"""Agent to limit watchlist to maximum number of tickers."""

from typing import Any, Dict, Optional
from core.agent import Agent
from core.context import AgentContext


class MaxTickersAgent(Agent):
	"""Limit watchlist to maximum number of tickers.

	Reads tickers from context, keeps top N tickers, stores result in context.
	"""

	def __init__(self, name: str = "MaxTickersAgent", max_tickers: int = 10):
		"""Initialize max tickers agent.

		Args:
			name: Agent name
			max_tickers: Maximum number of tickers to keep
		"""
		super().__init__(name)
		self.max_tickers = max_tickers

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Limit tickers to maximum count.

		Reads 'tickers' from context, limits to max_tickers, stores back in context.

		Args:
			input_data: Input data (not used, uses context instead)

		Returns:
			Response with limited ticker list
		"""
		if input_data is None:
			input_data = {}

		# Get watchlist from context
		watchlist = self.context.get("watchlist")
		if not watchlist:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No watchlist in context"
			}

		# Limit to max tickers
		limited_watchlist = watchlist[:self.max_tickers] if isinstance(watchlist, list) else []
		self.context.set("watchlist", limited_watchlist)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"tickers_count": len(limited_watchlist),
				"original_count": len(watchlist),
				"limited": len(watchlist) > self.max_tickers
			}
		}
