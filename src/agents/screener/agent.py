"""Screener agent for screening stocks against criteria."""

from typing import Any, Dict, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
import sys
from io import StringIO
import pandas as pd
import time

from core.agent import Agent
from core.context import AgentContext

# Suppress all warnings from external libraries
warnings.filterwarnings("ignore")


class ScreenerAgent(Agent):
	"""Agent for running screeners on historical data.

	Loads tickers from universes or explicit lists, calculates indicators,
	evaluates DSL formulas, and returns matching results.
	"""

	def __init__(self, name: str = "ScreenerAgent", context: Optional[AgentContext] = None):
		"""Initialize screener agent.

		Args:
			name: Agent name
			context: Shared agent context
		"""
		super().__init__(name, context)
		self._fundamental_cache: Dict[str, str] = {}  # Cache for company names

	def _get_fundamental(self, ticker: str) -> str:
		"""Get company name with caching. Returns ticker if name can't be found."""
		if ticker in self._fundamental_cache:
			return self._fundamental_cache[ticker]

		try:
			from tools.data.core import Fundamental
			fundamental = Fundamental(ticker)
			# Try cache first, then fetch if needed
			cached = fundamental.load()
			if cached:
				name = cached.get("data", {}).get("company", {}).get("name", ticker)
			else:
				info = fundamental.get_company_info()
				name = info.get("company_name", ticker)
			self._fundamental_cache[ticker] = name
			return name
		except Exception as e:
			self.logger.debug(f"Could not fetch fundamental for {ticker}: {e}")
			self._fundamental_cache[ticker] = ticker
			return ticker

	def _process_ticker(
		self,
		ticker: str,
		data_history: Optional[Dict[str, pd.DataFrame]],
		screener_config: Any,
		most_recent_date: Any,
	) -> Tuple[List[Dict[str, Any]], int, float]:
		"""Process a single ticker and return matching results.

		Returns:
			Tuple of (results, skip_count, processing_time)
		"""
		ticker_start = time.time()
		skip_count = 0
		results = []

		try:
			from tools.data.core import DataHistory
			from tools.indicators import calculate
			from tools.formula.dsl_parser import evaluate_dsl_vectorized

			# Get historical data from cache or load directly
			load_start = time.time()
			if data_history and ticker in data_history:
				history_df = data_history[ticker].copy()
			else:
				dh = DataHistory(ticker)
				history_df = dh.get_all()
			load_time = time.time() - load_start

			if history_df is None or history_df.empty:
				return [], 1, time.time() - ticker_start

			# Determine date column
			date_col = 'timestamp' if 'timestamp' in history_df.columns else 'date'

			# Sort by date to ensure proper ordering
			history_df = history_df.sort_values(date_col).reset_index(drop=True)

			# Limit to last 60 days for performance
			if len(history_df) > 60:
				history_df = history_df.iloc[-60:].reset_index(drop=True)

			# Calculate required indicators
			try:
				calc_start = time.time()
				missing_indicators = [ind for ind in screener_config.indicators
									  if ind.lower() not in history_df.columns]

				if missing_indicators:
					self.logger.debug(f"Calculating missing indicators for {ticker}: {missing_indicators}")

					# Delete any existing indicator columns
					ohlcv_cols = {'timestamp', 'open', 'high', 'low', 'close', 'volume', 'ticker', 'date'}
					indicator_cols = [col for col in history_df.columns if col.lower() not in ohlcv_cols]
					if indicator_cols:
						history_df = history_df.drop(columns=indicator_cols)

					# Calculate fresh indicators
					indicator_results = calculate(missing_indicators, history_df)

					# Add fresh indicators to dataframe
					for indicator_name, indicator_series in indicator_results.items():
						history_df[indicator_name.lower()] = indicator_series
				calc_time = time.time() - calc_start
			except Exception as e:
				self.logger.debug(f"Indicator calculation failed for {ticker}: {e}")
				return [], 1, time.time() - ticker_start

			# Evaluate formula on full history
			try:
				eval_start = time.time()
				all_matches = evaluate_dsl_vectorized(screener_config.formula, history_df)
				screening_mask = history_df[date_col] == most_recent_date
				matches = all_matches[screening_mask]
				eval_time = time.time() - eval_start
			except Exception as e:
				self.logger.debug(f"Formula evaluation failed for {ticker}: {e}")
				return [], 1, time.time() - ticker_start

			# Get screening data
			screening_df = history_df[screening_mask]
			if screening_df.empty:
				return [], 1, time.time() - ticker_start

			# Get company name from cache
			company_name = self._get_fundamental(ticker)

			# Collect matching rows
			for idx, (is_match, row) in enumerate(zip(matches, screening_df.itertuples(index=False))):
				if is_match:
					row_dict = row._asdict() if hasattr(row, '_asdict') else dict(row)
					result_row = {
						'date': str(row_dict.get('timestamp', row_dict.get('date', ''))),
						'ticker': ticker,
						'name': company_name,
						'open': float(row_dict.get('open', 0)) if pd.notna(row_dict.get('open')) else None,
						'high': float(row_dict.get('high', 0)) if pd.notna(row_dict.get('high')) else None,
						'low': float(row_dict.get('low', 0)) if pd.notna(row_dict.get('low')) else None,
						'close': float(row_dict.get('close', 0)) if pd.notna(row_dict.get('close')) else None,
						'volume': float(row_dict.get('volume', 0)) if pd.notna(row_dict.get('volume')) else None,
					}

					# Add all calculated indicators
					for indicator_name in screener_config.indicators:
						value = row_dict.get(indicator_name.lower()) or row_dict.get(indicator_name)
						result_row[indicator_name] = float(value) if pd.notna(value) else None

					results.append(result_row)

		except Exception as e:
			self.logger.debug(f"Error processing {ticker}: {e}")
			skip_count = 1

		return results, skip_count, time.time() - ticker_start

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Run a screener on a specific date (defaults to most recent date).

		Input data should contain:
			screener_name (str): Name of screener to run
			OR
			screener_config (ScreenerConfig): Screener configuration object
			date (optional): Date to screen (format: YYYY-MM-DD or timestamp)

		Uses data_history from context if available (from DataAgent), otherwise loads directly.

		Returns:
			Dict with keys:
				status: "success" or "error"
				message: Human-readable message
				result_id: ID of saved results (if success)
				match_count: Number of matching rows
				matches: List of matching rows (up to 100)
		"""
		if input_data is None:
			input_data = {}

		screener_name = input_data.get("screener_name")
		screener_config = input_data.get("screener_config")
		target_date = input_data.get("date")  # Optional date parameter
		use_cached_data = input_data.get("use_cached_data", True)  # Use DataAgent cache if available
		max_tickers = input_data.get("max_tickers", None)  # Optional limit for preview/testing

		# Get screener config if only name provided
		if screener_name and not screener_config:
			from tools.screener import ScreenerManager
			manager = ScreenerManager()
			screener_config = manager.get_screener(screener_name)
			if not screener_config:
				return {
					"status": "error",
					"message": f"Screener '{screener_name}' not found",
				}

		if not screener_config:
			return {
				"status": "error",
				"message": "screener_name or screener_config required",
			}

		try:
			import time
			from tools.universe.universe import Universe
			from tools.data.core import DataHistory
			from tools.indicators import calculate
			from tools.formula.dsl_parser import evaluate_dsl_vectorized
			from tools.screener import ScreenerManager

			# Try to use cached data from DataAgent first
			data_history = None
			if use_cached_data:
				data_history = self.context.get("data_history")
				if data_history:
					self.logger.info(f"Using cached data_history from context ({len(data_history)} tickers)")
					tickers = list(data_history.keys())
				else:
					data_history = None

			# If no cached data, load tickers from source or explicit list
			if not data_history:
				tickers = []
				if screener_config.source:
					universe = Universe(screener_config.source.lower())
					if universe.exists():
						tickers = universe.get_tickers()
					else:
						return {
							"status": "error",
							"message": f"Universe '{screener_config.source}' not found",
						}
				elif screener_config.tickers:
					tickers = screener_config.tickers
				else:
					return {
						"status": "error",
						"message": "No tickers or source specified in screener configuration",
					}

				if not tickers:
					return {
						"status": "error",
						"message": "No tickers found in source or configuration",
					}

				self.logger.info(f"Loading data for {len(tickers)} tickers with formula: {screener_config.formula}")
			else:
				self.logger.info(f"Screening {len(tickers)} tickers (using cached data) with formula: {screener_config.formula}")

			# Determine most recent date if not specified
			most_recent_date = target_date
			if not most_recent_date:
				# When screening multiple tickers (portfolios), find the minimum of max dates
				# so all tickers have data for the screening date
				max_dates = []

				# Get date from cached data if available
				if data_history:
					# Find most recent date for each ticker
					for ticker_df in data_history.values():
						if ticker_df is not None and not ticker_df.empty:
							date_col = 'timestamp' if 'timestamp' in ticker_df.columns else 'date'
							ticker_max_date = ticker_df[date_col].max()
							if ticker_max_date is not None:
								max_dates.append(ticker_max_date)
				else:
					# Load date from individual tickers if no cache
					for ticker in tickers:
						try:
							dh = DataHistory(ticker)
							history_df = dh.get_all()
							if history_df is not None and not history_df.empty:
								date_col = 'timestamp' if 'timestamp' in history_df.columns else 'date'
								ticker_max_date = history_df[date_col].max()
								if ticker_max_date is not None:
									max_dates.append(ticker_max_date)
						except Exception:
							pass

				if max_dates:
					# Use the minimum of the max dates (common date for all tickers)
					most_recent_date = min(max_dates)
				else:
					return {
						"status": "error",
						"message": "Could not determine screening date from historical data",
					}

			self.logger.info(f"Screening date: {most_recent_date}")

			# Collect all results
			all_results = []
			ticker_count = 0
			skip_count = 0

			# Apply ticker limit if specified (for preview/testing, 0 = no limit)
			tickers_to_process = tickers[:max_tickers] if max_tickers and max_tickers > 0 else tickers
			if max_tickers and max_tickers > 0:
				self.logger.info(f"Limiting screening to {len(tickers_to_process)} of {len(tickers)} tickers")

			# Process tickers in parallel using thread pool (4-8 workers)
			max_workers = min(8, len(tickers_to_process))
			parallel_start = time.time()
			ticker_times = {}
			results_by_ticker = {}

			self.logger.info(f"Processing {len(tickers_to_process)} tickers in parallel with {max_workers} workers")

			with ThreadPoolExecutor(max_workers=max_workers) as executor:
				# Submit all ticker processing tasks
				futures = {
					executor.submit(
						self._process_ticker,
						ticker,
						data_history,
						screener_config,
						most_recent_date
					): ticker for ticker in tickers_to_process
				}

				# Collect results as they complete
				for future in as_completed(futures):
					ticker = futures[future]
					try:
						results, ticker_skip, proc_time = future.result()
						all_results.extend(results)
						skip_count += ticker_skip
						if results:
							ticker_count += 1
							self.logger.debug(f"{ticker}: {len(results)} matches ({proc_time:.3f}s)")
						ticker_times[ticker] = proc_time
					except Exception as e:
						self.logger.error(f"Failed to process {ticker}: {e}")
						skip_count += 1

			parallel_time = time.time() - parallel_start

			# Calculate timing
			total_ticker_time = sum(ticker_times.values())
			avg_ticker_time = total_ticker_time / len(tickers_to_process) if tickers_to_process else 0
			speedup = total_ticker_time / parallel_time if parallel_time > 0 else 1

			self.logger.info(f"Parallel screening: {len(tickers_to_process)} tickers in {parallel_time:.2f}s ({max_workers} workers, {speedup:.1f}x speedup)")
			print(f"\n⏱️  Parallel Processing Summary:")
			print(f"  Total time:    {parallel_time:.2f}s")
			print(f"  Per ticker:    {avg_ticker_time:.3f}s")
			print(f"  Speedup:       {speedup:.1f}x (vs sequential)")
			print(f"  Workers:       {max_workers}")

			# Save results using manager (skip if screener name starts with "_")
			skip_save = screener_config.name.startswith("_") or not screener_config.name

			if skip_save:
				total_tickers = len(tickers_to_process)
				self.logger.info(f"Screening complete: {len(all_results)} matches from {ticker_count} tickers ({total_tickers} screened, {skip_count} skipped) on {most_recent_date}")
				return {
					"status": "success",
					"message": f"Screening complete: {len(all_results)} matches",
					"result_id": None,
					"match_count": len(all_results),
					"tickers_processed": ticker_count,
					"tickers_skipped": skip_count,
					"matches": all_results[:100],  # Return first 100 matches
					"screening_date": str(most_recent_date),
					"timing": {
						"total": round(parallel_time, 2),
						"per_ticker": round(avg_ticker_time, 3),
						"workers": max_workers,
						"speedup": round(speedup, 1),
					}
				}

			manager = ScreenerManager()
			success, message, result_id = manager.save_result(
				screener_config.name,
				all_results
			)

			if success:
				self.logger.info(f"Screening complete: {len(all_results)} matches from {ticker_count} tickers on {most_recent_date}")
				return {
					"status": "success",
					"message": message,
					"result_id": result_id,
					"match_count": len(all_results),
					"tickers_processed": ticker_count,
					"tickers_skipped": skip_count,
					"matches": all_results[:100],  # Return first 100 matches
					"screening_date": str(most_recent_date),
				}
			else:
				return {
					"status": "error",
					"message": f"Failed to save results: {message}",
				}

		except Exception as e:
			self.logger.exception(f"Error running screener: {e}")
			return {
				"status": "error",
				"message": f"Error running screener: {str(e)}",
			}
