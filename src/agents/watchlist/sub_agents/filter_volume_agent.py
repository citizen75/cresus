"""Agent to filter watchlist by minimum trading volume."""

from typing import Any, Dict, Optional
from core.agent import Agent
from core.context import AgentContext


class FilterVolumeAgent(Agent):
	"""Filter watchlist by minimum trading volume.

	Reads tickers and data_history from context, extracts latest volume,
	filters by minimum volume requirement, stores result in context.
	Supports both fixed min_volume and dynamic ratio-based filtering.
	"""

	def __init__(self, name: str = "FilterVolumeAgent"):
		"""Initialize filter volume agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Filter tickers by latest trading volume from data_history.

		Reads 'tickers' and 'data_history' from context, extracts latest volume,
		filters by strategy config volume parameters, stores filtered tickers back in context.

		Args:
			input_data: Input data (not used, uses context instead)

		Returns:
			Response with volume filtering results
		"""
		if input_data is None:
			input_data = {}

		watchlist = self.context.get("watchlist")
		data_history = self.context.get("data_history")
		strategy_config = self.context.get("strategy_config")

		if not watchlist:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No watchlist in context"
			}

		if not data_history:
			self.logger.error("No data history available for volume filtering")
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No data history available for volume filtering"
			}

		# Get volume parameters from strategy config
		min_volume = None
		min_volume_ratio = None
		if strategy_config:
			watchlist_config = strategy_config.get("watchlist", {})
			volume_config = watchlist_config.get("parameters", {}).get("volume", {})
			min_volume = volume_config.get("min_volume")
			min_volume_ratio = volume_config.get("min_volume_ratio", 0.5)

		# Filter watchlist by latest volume from data_history
		filtered_watchlist = []
		for ticker in watchlist:
			if ticker in data_history:
				ticker_data = data_history[ticker]
				# Get latest volume value
				try:
					if hasattr(ticker_data, 'iloc') and len(ticker_data) > 0:
						latest_volume = ticker_data["volume"].iloc[0].item()  # [0] is most recent (newest-first)

						# Determine minimum volume threshold
						threshold = None
						if min_volume is not None:
							# Fixed volume threshold
							threshold = min_volume
						elif min_volume_ratio is not None and "volume_ma_20" in ticker_data.columns:
							# Dynamic volume ratio threshold
							volume_ma_20 = ticker_data["volume_ma_20"].iloc[0].item()  # [0] is most recent (newest-first)
							threshold = volume_ma_20 * min_volume_ratio

						# Apply filter if threshold is set
						if threshold is not None and latest_volume >= threshold:
							filtered_watchlist.append(ticker)
						elif threshold is None:
							# No threshold means pass all
							filtered_watchlist.append(ticker)
					else:
						continue
				except (ValueError, TypeError, AttributeError):
					continue

		removed_count = len(watchlist) - len(filtered_watchlist)
		self.context.set("watchlist", filtered_watchlist)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"filtered_count": len(filtered_watchlist),
				"removed_count": removed_count,
				"volume_data_available": True
			}
		}
