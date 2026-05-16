"""Agent to filter out tickers with stale trading data."""

from typing import Any, Dict, Optional
import pandas as pd
from core.agent import Agent


class FilterStaleDataAgent(Agent):
	"""Filter watchlist to remove tickers with outdated last trading date.

	Compares the last trading date for each ticker against the most recent
	trading date across all tickers, removing any with stale data.
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Filter tickers with stale trading data.

		Reads 'watchlist' and 'data_history' from context, identifies the most
		recent trading date, removes tickers not trading on that date, updates context.

		Args:
			input_data: Input data (not used, uses context instead)

		Returns:
			Response with filtered ticker list
		"""
		if input_data is None:
			input_data = {}

		# Get watchlist and data_history from context
		watchlist = self.context.get("watchlist")
		data_history = self.context.get("data_history")

		if not watchlist:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No watchlist in context"
			}

		if not data_history:
			return {
				"status": "success",
				"input": input_data,
				"output": {
					"tickers_count": len(watchlist),
					"removed_count": 0,
					"reason": "No data history available"
				}
			}

		# Find most recent trading date across all tickers
		most_recent_date = None
		for ticker in list(watchlist.keys()):
			if ticker not in data_history:
				continue

			df = data_history[ticker]
			if df.empty:
				continue

			# Get the last date from the DataFrame
			if "timestamp" in df.columns:
				last_date = pd.to_datetime(df["timestamp"]).max()
			elif "date" in df.columns:
				last_date = pd.to_datetime(df["date"]).max()
			else:
				# Try to use index if it's a date index
				try:
					last_date = pd.to_datetime(df.index).max()
				except:
					continue

			# Normalize to UTC and extract date only to avoid timezone issues
			if hasattr(last_date, 'tz_localize'):
				last_date = last_date.tz_convert('UTC').normalize()
			elif hasattr(last_date, 'tz_convert'):
				last_date = last_date.tz_convert('UTC').normalize()
			else:
				last_date = pd.Timestamp(last_date.date())

			if most_recent_date is None or last_date > most_recent_date:
				most_recent_date = last_date

		# If no recent date found, return unchanged watchlist
		if most_recent_date is None:
			return {
				"status": "success",
				"input": input_data,
				"output": {
					"tickers_count": len(watchlist),
					"removed_count": 0,
					"reason": "No valid trading dates found"
				}
			}

		# Filter watchlist to keep only tickers with recent data
		filtered_watchlist = {}
		removed_count = 0

		for ticker in list(watchlist.keys()):
			if ticker not in data_history:
				removed_count += 1
				continue

			df = data_history[ticker]
			if df.empty:
				removed_count += 1
				continue

			# Get the last date for this ticker
			if "timestamp" in df.columns:
				ticker_last_date = pd.to_datetime(df["timestamp"]).max()
			elif "date" in df.columns:
				ticker_last_date = pd.to_datetime(df["date"]).max()
			else:
				try:
					ticker_last_date = pd.to_datetime(df.index).max()
				except:
					removed_count += 1
					continue

			# Normalize to UTC and extract date only to avoid timezone issues
			if hasattr(ticker_last_date, 'tz_localize'):
				ticker_last_date = ticker_last_date.tz_convert('UTC').normalize()
			elif hasattr(ticker_last_date, 'tz_convert'):
				ticker_last_date = ticker_last_date.tz_convert('UTC').normalize()
			else:
				ticker_last_date = pd.Timestamp(ticker_last_date.date())

			# Keep ticker if its last date matches the most recent date
			if ticker_last_date == most_recent_date:
				filtered_watchlist[ticker] = watchlist[ticker]
			else:
				removed_count += 1
				self.logger.debug(f"Filtering out {ticker}: last_date={ticker_last_date}, most_recent={most_recent_date}")

		# Update watchlist in context
		self.context.set("watchlist", filtered_watchlist)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"tickers_count": len(filtered_watchlist),
				"original_count": len(watchlist),
				"removed_count": removed_count,
				"most_recent_date": str(most_recent_date)
			}
		}
