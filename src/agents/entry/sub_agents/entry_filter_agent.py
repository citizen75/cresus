"""Agent to filter entry recommendations based on entry_filter formula."""

from typing import Any, Dict, Optional
from core.agent import Agent
from tools.strategy.strategy import StrategyManager
from tools.formula.calculator import evaluate


class EntryFilterAgent(Agent):
	"""Filter entry recommendations based on entry_filter formula from strategy.

	Applies market regime/condition filtering to entry recommendations.
	Only allows entries when the entry_filter formula evaluates to True.
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Filter recommendations based on entry_filter formula.

		Loads entry_filter formula from strategy config and evaluates it
		against current market data for each recommendation.

		Args:
			input_data: Input data (not used, uses context)

		Returns:
			Response with filtered recommendations count
		"""
		if input_data is None:
			input_data = {}

		# Validate context dependencies
		validation_result = self._validate_context()
		if validation_result:
			return validation_result

		# Get entry recommendations and data from context
		entry_recommendations = self.context.get("entry_recommendations") or []
		data_history = self.context.get("data_history") or {}
		strategy_name = self.context.get("strategy_name")

		if not entry_recommendations:
			self.logger.debug("[ENTRY-FILTER] No recommendations to filter")
			return {
				"status": "success",
				"input": input_data,
				"output": {"filtered_count": 0, "passed_count": 0},
				"message": "No entry recommendations to filter"
			}

		if not strategy_name:
			self.logger.warning("No strategy_name in context, skipping entry filter")
			return {
				"status": "success",
				"input": input_data,
				"output": {"filtered_count": 0, "passed_count": len(entry_recommendations)},
				"message": "No strategy_name in context, skipping filter"
			}

		# Load latest strategy to ensure formula changes are picked up
		try:
			strategy_manager = StrategyManager()
			strategy_result = strategy_manager.load_strategy(strategy_name)
			if strategy_result.get("status") != "success":
				self.logger.warning(f"Could not load strategy {strategy_name}: {strategy_result.get('message')}")
				return {
					"status": "success",
					"input": input_data,
					"output": {"filtered_count": 0, "passed_count": len(entry_recommendations)},
					"message": f"Could not load strategy {strategy_name}"
				}
			strategy_data = strategy_result.get("data", {})
			entry_config = strategy_data.get("entry", {}).get("parameters", {})
			entry_filter_config = entry_config.get("entry_filter")

			if not entry_filter_config:
				self.logger.debug(f"No entry_filter configured for strategy {strategy_name}")
				return {
					"status": "success",
					"input": input_data,
					"output": {"filtered_count": 0, "passed_count": len(entry_recommendations)},
					"message": "No entry_filter configured"
				}

			entry_filter_formula = entry_filter_config.get("formula")
			if not entry_filter_formula:
				self.logger.warning(f"No formula in entry_filter config for strategy {strategy_name}")
				return {
					"status": "success",
					"input": input_data,
					"output": {"filtered_count": 0, "passed_count": len(entry_recommendations)},
					"message": "No formula in entry_filter config"
				}

			self.logger.info(f"[ENTRY-FILTER] Applying filter to {len(entry_recommendations)} recommendations")
			self.logger.debug(f"[ENTRY-FILTER] Formula: {entry_filter_formula}")

			# Apply filter to recommendations
			filtered_recommendations = []
			blocked_count = 0
			error_tickers = []
			passed_tickers = []
			no_data_tickers = []

			for rec in entry_recommendations:
				ticker = rec.get("ticker")

				# If no data for ticker, pass through
				if ticker not in data_history:
					no_data_tickers.append(ticker)
					self.logger.debug(f"[ENTRY-FILTER] {ticker}: no data (pass-through)")
					filtered_recommendations.append(rec)
					continue

				df = data_history[ticker]
				if df.empty:
					no_data_tickers.append(ticker)
					self.logger.debug(f"[ENTRY-FILTER] {ticker}: empty data (pass-through)")
					filtered_recommendations.append(rec)
					continue

				# Get last 5 days of data for evaluation (supports shift notation like [-1], [-2])
				# Data is sorted newest-first, so [:5] gets the most recent 5 days
				last_5_days = df.iloc[:5].copy() if len(df) >= 5 else df.copy()

				# Debug: Show available columns and values for first few rows
				if len(last_5_days) > 0:
					available_cols = list(last_5_days.columns)
					self.logger.debug(f"[ENTRY-FILTER] {ticker}: Available columns: {available_cols}")
					if 'sha_10_red' in available_cols and 'sha_10_green' in available_cols:
						for i in range(min(3, len(last_5_days))):
							row = last_5_days.iloc[i]
							self.logger.debug(f"[ENTRY-FILTER] {ticker}[{i}]: sha_10_red={row.get('sha_10_red')}, sha_10_green={row.get('sha_10_green')}")

				# Evaluate entry_filter formula
				try:
					passes_filter = evaluate(entry_filter_formula, last_5_days)
					if passes_filter:
						self.logger.debug(f"[ENTRY-FILTER] {ticker}: PASS")
						passed_tickers.append(ticker)
						filtered_recommendations.append(rec)
					else:
						self.logger.debug(f"[ENTRY-FILTER] {ticker}: BLOCKED")
						blocked_count += 1
				except Exception as e:
					error_msg = str(e)
					# Check if this is a syntax error in the formula
					if "unexpected token" in error_msg.lower() or "syntax error" in error_msg.lower():
						# Could be syntax error OR missing column - check if it's a known column
						import re
						token_match = re.search(r"Token\(INDICATOR, '([a-z_][a-z0-9_]*)\[(-?\d+)\]'\)", error_msg)
						if token_match:
							indicator_name = token_match.group(1)
							available_cols = list(last_5_days.columns)

							# Check if column exists
							if indicator_name in available_cols:
								error_msg = f"Formula syntax error in '{entry_filter_formula}'. Check for missing operators (and, or, &&, ||) between expressions."
							else:
								error_msg = f"Missing indicator '{indicator_name}' in formula '{entry_filter_formula}'. Available columns: {available_cols}"
						else:
							available_cols = list(last_5_days.columns)
							error_msg = f"Formula syntax error: {error_msg}. Available columns: {available_cols}"
					elif "not found" in error_msg.lower():
						# Missing indicator error
						available_cols = list(last_5_days.columns)
						error_msg = f"Formula evaluation error: {error_msg}. Available columns: {available_cols}"
					else:
						# Other errors
						available_cols = list(last_5_days.columns)
						error_msg = f"Formula evaluation failed: {error_msg}. Available columns: {available_cols}"

					self.logger.error(f"Entry filter evaluation error for {ticker}: {error_msg}")
					error_tickers.append(f"{ticker} ({error_msg})")
					# On formula error, block the recommendation (don't pass through)
					blocked_count += 1

			# Update context with filtered recommendations
			self.context.set("entry_recommendations", filtered_recommendations)

			# Log summary
			self.logger.info(f"[ENTRY-FILTER] Results: {len(passed_tickers)} passed, {blocked_count} blocked, {len(no_data_tickers)} no-data")
			if passed_tickers:
				self.logger.debug(f"[ENTRY-FILTER] Passed: {passed_tickers[:5]}{'...' if len(passed_tickers) > 5 else ''}")
			if error_tickers:
				self.logger.warning(f"[ENTRY-FILTER] Evaluation errors ({len(error_tickers)}): {error_tickers[:3]}{'...' if len(error_tickers) > 3 else ''}")

			return {
				"status": "success",
				"input": input_data,
				"output": {
					"filtered_count": blocked_count,
					"passed_count": len(filtered_recommendations),
					"error_tickers": error_tickers,
				},
				"message": f"Filtered {blocked_count} recommendations"
			}

		except Exception as e:
			self.logger.error(f"Unexpected error in entry_filter: {str(e)}", exc_info=True)
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"Entry filter error: {str(e)}"
			}

	def _validate_context(self) -> Optional[Dict[str, Any]]:
		"""Validate that required context fields are available.

		Returns:
			Error response if validation fails, None if valid
		"""
		# Check if data_history exists (can be empty dict but must exist)
		if self.context.get("data_history") is None:
			self.logger.warning("data_history not found in context")
			return {
				"status": "error",
				"input": {},
				"output": {},
				"message": "Missing data_history in context"
			}

		# Check if entry_recommendations exists (can be empty list but must exist)
		if self.context.get("entry_recommendations") is None:
			self.logger.warning("entry_recommendations not found in context")
			return {
				"status": "error",
				"input": {},
				"output": {},
				"message": "Missing entry_recommendations in context"
			}

		return None
