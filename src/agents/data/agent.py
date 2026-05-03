"""Data agent for managing and processing data-related tasks."""

from typing import Any, Dict, Optional
from core.agent import Agent


class DataAgent(Agent):
	"""Agent for managing and processing data-related tasks."""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process the input data and return a response.

		This method should be overridden by subclasses to implement specific
		data processing logic.

		Args:
			input_data: Input data for processing

		Returns:
			Response dictionary with status and data
		"""
		if input_data is None:
			input_data = {}

		# Check for tickers in input or context
		tickers = input_data.get("tickers") or self.context.get("tickers")

		if not tickers:
			self.logger.error("No tickers found in input or context")
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No tickers found in input or context",
			}

		# Store tickers in context for downstream agents
		self.context.set("tickers", tickers)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"tickers": tickers,
				"count": len(tickers) if isinstance(tickers, list) else 0,
			},
		}