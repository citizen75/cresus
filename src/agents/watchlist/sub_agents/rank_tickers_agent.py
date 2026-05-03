"""Agent to rank and sort watchlist tickers by a metric."""

from typing import Any, Dict, Optional
from core.agent import Agent


class RankTickersAgent(Agent):
	"""Rank and sort watchlist tickers by a specified metric.

	Reads tickers from context, sorts by metric if available,
	stores result in context.
	"""

	def __init__(self, name: str = "RankTickersAgent", metric: str = "score"):
		"""Initialize rank tickers agent.

		Args:
			name: Agent name
			metric: Metric to rank by (e.g., 'score', 'momentum', 'strength')
		"""
		super().__init__(name)
		self.metric = metric

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Rank and sort tickers by metric.

		Reads 'tickers' and metric data from context, sorts by metric,
		stores sorted tickers back in context.

		Args:
			input_data: Input data (not used, uses context instead)

		Returns:
			Response with ranking results
		"""
		if input_data is None:
			input_data = {}

		# Get tickers from context
		tickers = self.context.get("tickers")
		if not tickers:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No tickers in context"
			}

		# Get metric data from context
		metric_data = self.context.get(f"{self.metric}_data")

		if not metric_data:
			return {
				"status": "success",
				"input": input_data,
				"output": {
					"ranked_count": len(tickers),
					"metric": self.metric,
					"metric_data_available": False
				}
			}

		# Sort tickers by metric (descending)
		ranked_tickers = sorted(
			tickers,
			key=lambda t: metric_data.get(t, 0),
			reverse=True
		)

		self.context.set("tickers", ranked_tickers)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"ranked_count": len(ranked_tickers),
				"metric": self.metric,
				"metric_data_available": True
			}
		}
