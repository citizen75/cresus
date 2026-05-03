"""Agent to filter watchlist by minimum trading volume."""

from typing import Any, Dict, Optional
from core.agent import Agent


class FilterVolumeAgent(Agent):
	"""Filter watchlist by minimum trading volume.

	Reads tickers from context, filters by minimum volume requirement,
	stores result in context.
	"""

	def __init__(self, name: str = "FilterVolumeAgent", min_volume: int = 1000000):
		"""Initialize filter volume agent.

		Args:
			name: Agent name
			min_volume: Minimum trading volume to keep ticker
		"""
		super().__init__(name)
		self.min_volume = min_volume

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Filter tickers by volume.

		Reads 'tickers' and 'volume_data' from context, filters by min_volume,
		stores filtered tickers back in context.

		Args:
			input_data: Input data (not used, uses context instead)

		Returns:
			Response with volume filtering results
		"""
		if input_data is None:
			input_data = {}

		# Get tickers and volume data from context
		tickers = self.context.get("tickers")
		volume_data = self.context.get("volume_data")

		if not tickers:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No tickers in context"
			}

		# If no volume data, skip filtering and return all tickers
		if not volume_data:
			return {
				"status": "success",
				"input": input_data,
				"output": {
					"filtered_count": len(tickers),
					"removed_count": 0,
					"volume_data_available": False
				}
			}

		# Filter tickers by volume
		filtered_tickers = [
			t for t in tickers
			if volume_data.get(t, 0) >= self.min_volume
		]

		removed_count = len(tickers) - len(filtered_tickers)
		self.context.set("tickers", filtered_tickers)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"filtered_count": len(filtered_tickers),
				"removed_count": removed_count,
				"volume_data_available": True
			}
		}
