"""Data quality sub-agent for filtering stale ticker data."""

from typing import Any, Dict, Optional
import pandas as pd
from core.agent import Agent


class DataQualityAgent(Agent):
	"""Filter out tickers with stale data.

	Removes tickers whose most recent date is older than the most recent
	date across all tickers in the dataset. This ensures all tickers are
	up-to-date with consistent recency.

	Example:
		- ticker1: last date = 2026-03-03
		- ticker2: last date = 2026-03-01 (stale, removed)
	"""

	def __init__(self, name: str = "DataQualityAgent"):
		"""Initialize data quality agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Filter data_history to remove stale tickers.

		Args:
			input_data: Input data (optional)

		Returns:
			Response with filtered tickers and removed count
		"""
		if input_data is None:
			input_data = {}

		data_history = self.context.get("data_history") if self.context else None
		if not data_history:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No data_history in context",
			}

		# Find the most recent date across all tickers
		max_date = None
		ticker_dates = {}

		for ticker, ticker_data in data_history.items():
			if ticker_data.empty:
				ticker_dates[ticker] = None
				continue

			if "timestamp" in ticker_data.columns:
				last_date = ticker_data["timestamp"].max()
			else:
				last_date = ticker_data.index.max()

			ticker_dates[ticker] = last_date

			if max_date is None or (last_date is not None and last_date > max_date):
				max_date = last_date

		# Remove tickers with stale data
		removed_tickers = []
		filtered_data_history = {}

		for ticker, last_date in ticker_dates.items():
			if last_date is None:
				removed_tickers.append((ticker, "empty"))
			elif last_date < max_date:
				removed_tickers.append((ticker, pd.to_datetime(last_date).strftime("%Y-%m-%d")))
			else:
				filtered_data_history[ticker] = data_history[ticker]

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
				"removed_tickers": removed_tickers,
				"max_date": pd.to_datetime(max_date).strftime("%Y-%m-%d") if max_date else None,
			},
		}
