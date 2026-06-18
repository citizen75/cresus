"""Agent to limit watchlist to a maximum number of tickers."""

from typing import Any, Dict, Optional
from core.agent import Agent
from core.context import AgentContext


class MaxTickersAgent(Agent):
	"""Limit watchlist to a maximum number of tickers.

	Reads 'watchlist' from context, keeps the first max_tickers entries
	(preserving existing sort order), and writes the result back.
	"""

	def __init__(self, name: str = "MaxTickersAgent", max_tickers: int = 10, context: Optional[AgentContext] = None):
		super().__init__(name, context)
		self.max_tickers = max_tickers

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		if input_data is None:
			input_data = {}

		watchlist = self.context.get("watchlist")
		if not watchlist:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No watchlist in context",
			}

		original_count = len(watchlist)
		limited = dict(list(watchlist.items())[: self.max_tickers])
		self.context.set("watchlist", limited)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"tickers_count": len(limited),
				"original_count": original_count,
				"limited": original_count > self.max_tickers,
			},
		}
