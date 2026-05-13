"""Data agent for managing and processing data-related tasks."""

from typing import Any, Dict, Optional, List
from core.agent import Agent
from tools.indicators.indicators import calculate as calculate_indicators, register_indicators_for_formulas
from tools.data.core import DataHistory
from agents.data.sub_agents import DataQualityAgent, DataQuantityAgent


class DataAgent(Agent):
	"""Agent for managing and processing data-related tasks."""

	def _find_missing_indicators(self, data_history: dict, required_indicators: list) -> list:
		"""Find which indicators are missing or invalid across all tickers.

		Args:
			data_history: Dict of {ticker: DataFrame}
			required_indicators: List of indicator names to check

		Returns:
			List of missing/invalid indicator names (empty if all present and valid)
		"""
		if not data_history:
			return required_indicators

		# Get columns from first non-empty DataFrame
		existing_columns = set()
		sample_df = None
		for df in data_history.values():
			if not df.empty:
				existing_columns = set(df.columns)
				sample_df = df
				break

		# Find missing indicators AND indicators that are invalid (entirely NaN or NaN in recent rows)
		missing = []
		for ind in required_indicators:
			if ind not in existing_columns:
				missing.append(ind)
			elif sample_df is not None and ind in sample_df.columns:
				col = sample_df[ind]
				# Check if the indicator column is entirely NaN or NaN in the most recent rows
				if col.isna().all():
					# Entirely NaN
					missing.append(ind)
				else:
					# Check if most recent rows (last rows in DataFrame, which are the newest by timestamp) are NaN
					recent_count = min(5, len(col))
					if col.iloc[-recent_count:].isna().sum() > 0:
						# Recent rows have NaN - need to recalculate
						missing.append(ind)

		return missing

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
		# Use it as-is but still ensure indicators are calculated on the full data
		existing_data_history = self.context.get("data_history")
		if existing_data_history:
			self.logger.debug("data_history already in context, ensuring indicators are calculated")
			data_history = existing_data_history
			tickers = list(data_history.keys())
		else:
			data_history = None
			tickers = None

		# If data_history not already provided, load tickers from input/context
		if not tickers:
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

		# Load data if not already in context
		if not data_history:
			data_history = {}
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

					data_history[ticker] = ticker_data
				except Exception as e:
					self.logger.error(f"Failed to fetch data for {ticker}: {e}")
		else:
			self.logger.info(f"Using data_history from context for {len(data_history)} tickers")

		# Calculate indicators on ALL tickers (whether loaded fresh or from context)
		# This ensures complete indicator columns are available for downstream agents
		# Skip recalculation if indicators already exist in all tickers
		indicators_calculated = {}
		if indicators and data_history:
			# Check if all indicators already exist in all tickers
			missing_indicators = self._find_missing_indicators(data_history, indicators)

			if missing_indicators:
				self.logger.info(f"Calculating {len(missing_indicators)} missing indicators for {len(data_history)} tickers: {missing_indicators}")
				for ticker in list(data_history.keys()):
					ticker_data = data_history[ticker]

					try:
						# Sort in ascending order for indicator calculation
						ticker_data_asc = ticker_data.sort_values('timestamp', ascending=True).reset_index(drop=True)
						calculated = calculate_indicators(missing_indicators, ticker_data_asc)
						indicators_calculated[ticker] = calculated

						# Add calculated indicators as columns to the original data
						for indicator_name, series in calculated.items():
							ticker_data[indicator_name] = series

					except Exception as e:
						self.logger.warning(f"Failed to calculate indicators for {ticker}: {e}")
			else:
				self.logger.debug(f"All {len(indicators)} indicators already present in data_history, skipping recalculation")

		# Always sort data in descending order (newest first) for historical analysis
		# This enables shift notation: [-1] = most recent, [-2] = yesterday, etc.
		# Must happen regardless of whether indicators were just calculated
		if data_history:
			for ticker in data_history.keys():
				data_history[ticker] = data_history[ticker].sort_values('timestamp', ascending=False).reset_index(drop=True)

		# PRE-SLICE DATA TO TARGET_DATE IN LIVE MODE (after loading/sorting, before filters)
		# In backtest mode, BacktestAgent pre-slices before calling this agent
		is_backtest = self.context.get("backtest_id") is not None
		target_date = self.context.get("target_date")

		if target_date and not is_backtest and data_history:
			# Live mode: Slice data to target_date immediately after loading
			# This ensures all downstream agents work with consistent date range
			import pandas as pd
			from datetime import date as date_type

			try:
				target_date_obj = date_type.fromisoformat(str(target_date))
				sliced_history = {}
				for ticker, df in data_history.items():
					if df.empty:
						sliced_history[ticker] = df
						continue

					if "timestamp" in df.columns:
						timestamps = pd.to_datetime(df["timestamp"])
					else:
						timestamps = pd.to_datetime(df.index)

					dates = timestamps.dt.date
					mask = dates <= target_date_obj
					sliced_history[ticker] = df[mask].copy()

				data_history = sliced_history
				self.context.set("_data_sliced_for_entry", True)
				self.logger.info(f"Pre-sliced data_history to {target_date} in live mode")
			except Exception as e:
				self.logger.warning(f"Failed to pre-slice data: {e}")

		# Store data_history and indicators in context for downstream agents
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