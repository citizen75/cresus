"""Screener agent for screening stocks against criteria."""

from typing import Any, Dict, Optional
import warnings
import sys
from io import StringIO
import pandas as pd

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

			# Pre-fetch fundamentals for all tickers to avoid per-ticker yfinance calls
			fundamentals = {}
			prefetch_start = time.time()
			try:
				from tools.data.core import Fundamental
				self.logger.debug(f"Pre-fetching fundamentals for {len(tickers)} tickers")
				for ticker in tickers:
					try:
						fundamental = Fundamental(ticker)
						# Try cache first, then fetch if needed
						cached = fundamental.load()
						if cached:
							fundamentals[ticker] = cached.get("data", {}).get("company", {}).get("name", ticker)
						else:
							info = fundamental.get_company_info()
							fundamentals[ticker] = info.get("company_name", ticker)
					except Exception as e:
						self.logger.debug(f"Could not fetch fundamental for {ticker}: {e}")
						fundamentals[ticker] = ticker
			except Exception as e:
				self.logger.warning(f"Error pre-fetching fundamentals: {e}")
			prefetch_time = time.time() - prefetch_start
			print(f"⏱️  Pre-fetch fundamentals: {prefetch_time:.2f}s")

			# Collect all results
			all_results = []
			ticker_count = 0
			skip_count = 0

			# Apply ticker limit if specified (for preview/testing, 0 = no limit)
			tickers_to_process = tickers[:max_tickers] if max_tickers and max_tickers > 0 else tickers
			if max_tickers and max_tickers > 0:
				self.logger.info(f"Limiting screening to {len(tickers_to_process)} of {len(tickers)} tickers")

			# Process each ticker
			ticker_times = {}
			for ticker in tickers_to_process:
				ticker_start = time.time()
				try:
					# Get historical data from cache or load directly
					load_start = time.time()
					if data_history and ticker in data_history:
						history_df = data_history[ticker].copy()
					else:
						# Load historical data if not in cache
						dh = DataHistory(ticker)
						history_df = dh.get_all()
					ticker_times[ticker] = {'load': time.time() - load_start}

					if history_df is None or history_df.empty:
						skip_count += 1
						continue

					# Determine date column
					date_col = 'timestamp' if 'timestamp' in history_df.columns else 'date'

					# Sort by date to ensure proper ordering (required for indicators)
					history_df = history_df.sort_values(date_col).reset_index(drop=True)

					# Limit to last 60 days for performance (recent data is sufficient for indicators)
					# This dramatically speeds up screening without affecting screening date results
					if len(history_df) > 60:
						history_df = history_df.iloc[-60:].reset_index(drop=True)

					# Calculate required indicators
					try:
						calc_start = time.time()
						# Check which indicators are missing
						missing_indicators = [ind for ind in screener_config.indicators
											 if ind.lower() not in history_df.columns]

						if missing_indicators:
							self.logger.debug(f"Calculating missing indicators for {ticker}: {missing_indicators}")
							indicator_results = calculate(missing_indicators, history_df)

							# Clear stale indicator columns (Option B: avoid mixing data ages)
							# Get list of known indicator base names (sha_*, rsi_*, ema_*, etc)
							base_indicators = {ind.split('_')[0] for ind in screener_config.indicators}
							stale_columns = [col for col in history_df.columns
											if any(col.lower().startswith(base + '_') for base in base_indicators)
											and col.lower() not in [ind.lower() for ind in missing_indicators]]
							if stale_columns:
								self.logger.debug(f"Clearing stale indicator columns for {ticker}: {stale_columns}")
								history_df = history_df.drop(columns=stale_columns)

							# Add fresh indicators to dataframe (use lowercase column names for consistency)
							for indicator_name, indicator_series in indicator_results.items():
								history_df[indicator_name.lower()] = indicator_series
						else:
							self.logger.debug(f"All indicators already cached for {ticker}")
						ticker_times[ticker]['calc'] = time.time() - calc_start
					except Exception as e:
						self.logger.debug(f"Indicator calculation failed for {ticker}: {e}")
						skip_count += 1
						continue

					# Evaluate formula on full history first (so shift notation works)
					try:
						eval_start = time.time()
						all_matches = evaluate_dsl_vectorized(screener_config.formula, history_df)
						# Filter to screening date
						screening_mask = history_df[date_col] == most_recent_date
						matches = all_matches[screening_mask]
						ticker_times[ticker]['eval'] = time.time() - eval_start
					except Exception as e:
						self.logger.debug(f"Formula evaluation failed for {ticker}: {e}")
						skip_count += 1
						continue

					# Get screening data
					screening_df = history_df[screening_mask]
					if screening_df.empty:
						skip_count += 1
						continue

					# Get company name from pre-fetched fundamentals
					info_start = time.time()
					company_name = fundamentals.get(ticker, ticker)
					ticker_times[ticker]['info'] = time.time() - info_start

					# Collect matching rows
					match_count = 0
					for idx, (is_match, row) in enumerate(zip(matches, screening_df.itertuples(index=False))):
						if is_match:
							# Add matching row to results
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
								# Try both lowercase and original case
								value = row_dict.get(indicator_name.lower()) or row_dict.get(indicator_name)
								result_row[indicator_name] = float(value) if pd.notna(value) else None

							all_results.append(result_row)
							match_count += 1

					if match_count > 0:
						ticker_count += 1
						self.logger.debug(f"{ticker}: {match_count} matches")

				except Exception as e:
					self.logger.debug(f"Error processing {ticker}: {e}")
					skip_count += 1
					continue

			# Calculate timing breakdown
			total_load = sum(t.get('load', 0) for t in ticker_times.values())
			total_calc = sum(t.get('calc', 0) for t in ticker_times.values())
			total_eval = sum(t.get('eval', 0) for t in ticker_times.values())
			total_info = sum(t.get('info', 0) for t in ticker_times.values())
			total_ticker_time = total_load + total_calc + total_eval + total_info

			self.logger.info(f"Timing breakdown: load={total_load:.2f}s, calc={total_calc:.2f}s, eval={total_eval:.2f}s, info={total_info:.2f}s, total={total_ticker_time:.2f}s")
			print(f"\n⏱️  Timing Breakdown (per ticker):")
			print(f"  Load:  {total_load:.2f}s ({total_load/len(tickers_to_process):.3f}s/ticker)")
			print(f"  Calc:  {total_calc:.2f}s ({total_calc/len(tickers_to_process):.3f}s/ticker)")
			print(f"  Eval:  {total_eval:.2f}s ({total_eval/len(tickers_to_process):.3f}s/ticker)")
			print(f"  Info:  {total_info:.2f}s ({total_info/len(tickers_to_process):.3f}s/ticker)")
			print(f"  Total: {total_ticker_time:.2f}s ({total_ticker_time/len(tickers_to_process):.3f}s/ticker)")

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
						"load": round(total_load, 2),
						"calc": round(total_calc, 2),
						"eval": round(total_eval, 2),
						"info": round(total_info, 2),
						"total": round(total_ticker_time, 2),
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
