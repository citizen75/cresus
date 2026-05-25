"""Formula analysis flow for debugging DSL expressions across dates and tickers.

Evaluates a formula on historical data for specified tickers and date range,
showing results for each day to understand formula behavior.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import pandas as pd
from datetime import datetime, timedelta

# Ensure src is in path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from core.flow import Flow
from core.context import AgentContext
from tools.formula.indicator_extractor import extract_indicators
from tools.formula.dsl_parser import evaluate_dsl_vectorized
from agents.data.agent import DataAgent


class AnalyzeFlow(Flow):
	"""Flow for analyzing formula evaluation across dates and tickers.

	1. Extracts required indicators from formula
	2. Loads data and calculates indicators using DataAgent
	3. Evaluates formula on each day for all tickers
	4. Displays results to help debug DSL expressions
	"""

	def __init__(self, context: Optional[AgentContext] = None):
		"""Initialize analysis flow.

		Args:
			context: Optional AgentContext for shared state
		"""
		super().__init__("AnalyzeFlow", context=context)

	def process(
		self,
		formula: str,
		tickers: List[str],
		start_date: str,
		end_date: Optional[str] = None,
	) -> Dict[str, Any]:
		"""Analyze formula evaluation across dates and tickers.

		Args:
			formula: DSL formula to evaluate (e.g., "close[0] > ema_5[0]")
			tickers: List of ticker symbols
			start_date: Start date as string (YYYY-MM-DD)
			end_date: End date as string (optional, defaults to today)

		Returns:
			Dict with analysis results including pass/fail counts and detailed results
		"""
		# Parse dates
		try:
			start = pd.to_datetime(start_date).date()
			end = pd.to_datetime(end_date).date() if end_date else datetime.now().date()
		except Exception as e:
			return {
				"status": "error",
				"message": f"Invalid date format: {str(e)}",
				"output": {}
			}

		self.logger.info(f"[ANALYZE] Formula: {formula}")
		self.logger.info(f"[ANALYZE] Tickers: {tickers}")
		self.logger.info(f"[ANALYZE] Date range: {start} to {end}")

		# Extract required indicators from formula
		required_indicators = extract_indicators(formula)
		self.logger.info(f"[ANALYZE] Required indicators: {sorted(required_indicators)}")

		# Use DataAgent to load data and calculate indicators
		self.context.set("tickers", tickers)
		data_agent = DataAgent("DataAgent", self.context)

		# Pass required indicators to DataAgent
		input_data = {
			"tickers": tickers,
			"indicators": list(required_indicators)
		}

		result = data_agent.process(input_data)
		if result.get("status") != "success":
			return {
				"status": "error",
				"message": f"DataAgent failed: {result.get('message')}",
				"output": {}
			}

		# Get enriched data_history from context
		data_history = self.context.get("data_history") or {}
		if not data_history:
			return {
				"status": "error",
				"message": "No data loaded by DataAgent",
				"output": {}
			}

		# Evaluate formula for each date and ticker
		results = []
		pass_count = 0
		fail_count = 0
		error_count = 0

		# Date range for iteration
		current_date = start
		while current_date <= end:
			for ticker, df in data_history.items():
				if df is None or df.empty:
					continue

				# Convert timestamps to date for filtering
				if "timestamp" in df.columns:
					date_series = pd.to_datetime(df["timestamp"]).dt.date
				else:
					date_series = pd.to_datetime(df.index).date

				# Get data up to and including current date (for shift support)
				# This allows formulas like [-1] to access previous bars
				df_up_to_date = df[date_series <= current_date].copy()

				if df_up_to_date.empty:
					continue

				# Ensure data is sorted for vectorized evaluation
				# evaluate_dsl_vectorized requires ascending order for proper shift handling
				df_up_to_date = df_up_to_date.sort_values('timestamp', ascending=True).reset_index(drop=True)

				# Use only the last row (current date), but keep full context
				row_data = df_up_to_date.iloc[-1:].copy()

				try:
					# Evaluate formula using vectorized evaluation
					# Pass full context for shifts, but evaluate on current row
					result_series = evaluate_dsl_vectorized(formula, df_up_to_date)
					result_value = bool(result_series.iloc[-1]) if len(result_series) > 0 else False

					if result_value:
						pass_count += 1
						status = "PASS"
					else:
						fail_count += 1
						status = "FAIL"

					results.append({
						"date": str(current_date),
						"ticker": ticker,
						"status": status
					})

				except Exception as e:
					error_count += 1
					results.append({
						"date": str(current_date),
						"ticker": ticker,
						"status": f"ERROR: {str(e)[:40]}"
					})
					self.logger.debug(f"[ANALYZE] Error on {current_date} {ticker}: {str(e)}")

			current_date += timedelta(days=1)

		# Summary
		total = pass_count + fail_count + error_count
		pass_pct = (pass_count / total * 100) if total > 0 else 0

		self.logger.info(f"[ANALYZE] Complete: {pass_count} pass, {fail_count} fail, {error_count} errors out of {total} evaluations ({pass_pct:.1f}% pass)")

		return {
			"status": "success",
			"output": {
				"formula": formula,
				"indicators": sorted(list(required_indicators)),
				"tickers": tickers,
				"date_range": f"{start} to {end}",
				"results": results,
				"summary": {
					"total": total,
					"pass": pass_count,
					"fail": fail_count,
					"error": error_count,
					"pass_pct": float(round(pass_pct, 1))
				}
			},
			"message": f"Formula evaluation: {pass_count} pass ({pass_pct:.1f}%), {fail_count} fail, {error_count} errors"
		}
