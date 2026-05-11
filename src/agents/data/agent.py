"""Data agent for managing and processing data-related tasks."""

from typing import Any, Dict, Optional, List
from core.agent import Agent
from tools.indicators.indicators import calculate as calculate_indicators, register_indicators_for_formulas
from tools.data.core import DataHistory
from agents.data.sub_agents import DataQualityAgent, DataQuantityAgent


class DataAgent(Agent):
	"""Agent for managing and processing data-related tasks."""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Fetch data for tickers and calculate indicators.

		Args:
			input_data: Input data containing:
				- tickers: List of ticker symbols
				- indicators: Optional list of indicator formulas (e.g., ["rsi_14", "ema_20"])

		Returns:
			Response dictionary with status and data
		"""
		if input_data is None:
			input_data = {}

		# Check if data_history already exists in context (backtest mode)
		# If so, skip loading and just return success
		existing_data_history = self.context.get("data_history")
		if existing_data_history:
			self.logger.debug("data_history already in context (backtest mode), skipping DataAgent load")
			tickers = list(existing_data_history.keys())
			# Store tickers in context for downstream agents
			self.context.set("tickers", tickers)
			return {
				"status": "success",
				"input": input_data,
				"output": {
					"tickers": tickers,
					"count": len(existing_data_history),
					"data_fetched": len(existing_data_history),
					"indicators": [],
					"indicators_count": 0,
				},
			}

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

		# Get indicators from strategy config or input
		indicators = input_data.get("indicators", [])
		if not indicators:
			strategy_config = self.context.get("strategy_config")
			if strategy_config:
				indicators = strategy_config.get("indicators", [])

		# Register only the indicators needed for this strategy
		if indicators:
			register_indicators_for_formulas(indicators)

		# Load cached price history for all tickers
		# Note: Load all data - filtering by current_date happens in analysis agents
		data_history = {}
		indicators_calculated = {}
		self.logger.info(f"Loading data for {len(tickers)} tickers")
		for ticker in tickers:
			try:
				# Load cached data using DataHistory
				dh = DataHistory(ticker)
				ticker_data = dh.get_all()

				if ticker_data.empty:
					self.logger.warning(f"No cached data available for {ticker}")
					continue

				# Remove deprecated volume_20ma column if present (replaced by volume_sma_20)
				if 'volume_20ma' in ticker_data.columns:
					ticker_data = ticker_data.drop(columns=['volume_20ma'])

				# Sort data in descending order (newest first) for historical analysis
				# This enables shift notation: [-1] = most recent, [-2] = yesterday, etc.
				ticker_data = ticker_data.iloc[::-1].reset_index(drop=True)

				# Calculate indicators if specified
				if indicators:
					try:
						calculated = calculate_indicators(indicators, ticker_data)
						indicators_calculated[ticker] = calculated

						# Add calculated indicators as columns to the data
						for indicator_name, series in calculated.items():
							ticker_data[indicator_name] = series

						# Save updated data back to cache
						dh.filepath.parent.mkdir(parents=True, exist_ok=True)
						ticker_data.to_parquet(dh.filepath, index=False)
					except Exception as e:
						self.logger.warning(f"Failed to calculate indicators for {ticker}: {e}")

				data_history[ticker] = ticker_data
			except Exception as e:
				self.logger.error(f"Failed to fetch data for {ticker}: {e}")

		# Store data_history in context
		self.context.set("data_history", data_history)
		if indicators_calculated:
			self.context.set("indicators_calculated", indicators_calculated)

		# Run data quality filtering
		quality_agent = DataQualityAgent()
		quality_agent.context = self.context
		quality_result = quality_agent.process()
		if quality_result.get("status") == "success":
			removed_quality = quality_result["output"].get("removed_count", 0)
			if removed_quality > 0:
				self.logger.info(f"DataQualityAgent removed {removed_quality} stale tickers: {quality_result['output'].get('removed_tickers', [])}")
		else:
			self.logger.warning(f"DataQualityAgent failed: {quality_result.get('message', 'unknown error')}")

		# Run data quantity filtering
		quantity_agent = DataQuantityAgent()
		quantity_agent.context = self.context
		quantity_result = quantity_agent.process()
		if quantity_result.get("status") == "success":
			removed_quantity = quantity_result["output"].get("removed_count", 0)
			if removed_quantity > 0:
				self.logger.info(f"DataQuantityAgent removed {removed_quantity} tickers with insufficient data: {quantity_result['output'].get('removed_tickers', [])}")
		else:
			self.logger.warning(f"DataQuantityAgent failed: {quantity_result.get('message', 'unknown error')}")

		# Get updated data_history and tickers from context after filtering
		final_data_history = self.context.get("data_history")
		final_tickers = self.context.get("tickers")
		
		final_ticker_count = len(final_tickers) if final_tickers else 0
		initial_ticker_count = len(data_history)
		removed_count = initial_ticker_count - final_ticker_count
		
		if removed_count > 0:
			self.logger.info(f"DataAgent final: {final_ticker_count} tickers after filtering (removed {removed_count})")
		else:
			self.logger.info(f"DataAgent final: {final_ticker_count} tickers after filtering")

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"tickers": tickers,
				"count": len(tickers) if isinstance(tickers, list) else 0,
				"data_fetched": len(data_history),
				"data_after_quality_filter": quality_result["output"].get("filtered_count", 0) if quality_result.get("status") == "success" else len(data_history),
				"data_after_quantity_filter": len(final_data_history),
				"indicators": indicators,
				"indicators_count": len([k for v in indicators_calculated.values() for k in v]),
			},
		}