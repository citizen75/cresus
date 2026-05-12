"""Data quantity sub-agent for filtering tickers with insufficient history."""

from typing import Any, Dict, Optional
import pandas as pd
from core.agent import Agent


class DataQuantityAgent(Agent):
	"""Filter out tickers with insufficient historical data.

	Removes tickers that have less than the minimum required days of history.
	This ensures analysis agents have enough data for reliable indicator
	calculation and pattern recognition.
	"""

	def __init__(self, name: str = "DataQuantityAgent", min_days: int = 90):
		"""Initialize data quantity agent.

		Args:
			name: Agent name
			min_days: Minimum required days of history (default: 90, covers MACD_12_26 and lookback)
		"""
		super().__init__(name)
		self.min_days = min_days

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Filter data_history to remove tickers with insufficient data.

		Args:
			input_data: Input data (optional), can override min_days via "min_days" key

		Returns:
			Response with filtered tickers and removed count
		"""
		if input_data is None:
			input_data = {}

		# Allow overriding min_days via input
		min_days = input_data.get("min_days", self.min_days)

		data_history = self.context.get("data_history") if self.context else None
		if not data_history:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No data_history in context",
			}

		# Check data quantity for each ticker
		removed_tickers = []
		filtered_data_history = {}

		for ticker, ticker_data in data_history.items():
			if ticker_data.empty:
				removed_tickers.append((ticker, "empty", 0))
				continue

			# Get date range
			if "timestamp" in ticker_data.columns:
				first_date = ticker_data["timestamp"].min()
				last_date = ticker_data["timestamp"].max()
			else:
				first_date = ticker_data.index.min()
				last_date = ticker_data.index.max()

			# Calculate days of history
			days_of_data = (pd.to_datetime(last_date) - pd.to_datetime(first_date)).days

			if days_of_data < min_days:
				removed_tickers.append((ticker, pd.to_datetime(first_date).strftime("%Y-%m-%d"), days_of_data))
			else:
				filtered_data_history[ticker] = ticker_data

		# Update context with filtered data
		self.context.set("data_history", filtered_data_history)

		# Update tickers list if in context
		tickers = self.context.get("tickers")
		if tickers:
			filtered_tickers = [t for t in tickers if t in filtered_data_history]
			self.context.set("tickers", filtered_tickers)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"original_count": len(data_history),
				"filtered_count": len(filtered_data_history),
				"removed_count": len(removed_tickers),
				"min_days_required": min_days,
				"removed_tickers": removed_tickers,
			},
		}
