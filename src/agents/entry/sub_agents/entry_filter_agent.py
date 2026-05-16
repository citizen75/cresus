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

		# Get watchlist and data from context
		watchlist = self.context.get("watchlist") or {}
		data_history = self.context.get("data_history") or {}
		strategy_name = self.context.get("strategy_name")

		#print(f"[ENTRY-FILTER] Starting with {len(watchlist)} tickers in watchlist")
		#watchlist_tickers = watchlist.keys()
		#print(f"[ENTRY-FILTER] Watchlist: {watchlist_tickers}...")

		if not watchlist:
			self.logger.debug("[ENTRY-FILTER] No tickers in watchlist to filter")
			return {
				"status": "success",
				"input": input_data,
				"output": {"filtered_count": 0, "passed_count": 0},
				"message": "No watchlist tickers to filter"
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
			# Check if strategy_config is already in context
			strategy_data = self.context.get("strategy_config")
			entry_config = strategy_data.get("entry", {}).get("parameters", {})
			entry_filter_config = entry_config.get("entry_filter")

			if not entry_filter_config:
				self.logger.debug(f"No entry_filter configured for strategy {strategy_name}")
				return {
					"status": "success",
					"input": input_data,
					"output": {"filtered_count": 0, "passed_count": len(watchlist)},
					"message": "No entry_filter configured"
				}

			entry_filter_formula = entry_filter_config.get("formula")

			if not entry_filter_formula:
				self.logger.warning(f"No formula in entry_filter config for strategy {strategy_name}")
				return {
					"status": "success",
					"input": input_data,
					"output": {"filtered_count": 0, "passed_count": len(watchlist)},
					"message": "No formula in entry_filter config"
				}

			self.logger.info(f"[ENTRY-FILTER] Applying filter to {len(watchlist)} tickers")
			self.logger.info(f"[ENTRY-FILTER] Formula: {entry_filter_formula}")

			# Apply filter to watchlist dict
			filtered_watchlist = {}
			blocked_count = 0
			error_tickers = []
			passed_tickers = []
			no_data_tickers = []

			first_ticker = list(watchlist.keys())[0] if watchlist else None
			self.logger.info(f"[ENTRY-FILTER] First ticker: {first_ticker}")

			for ticker, ticker_data in list(watchlist.items()):
				# If no data for ticker, keep it (pass through)	
				if ticker not in data_history:
					no_data_tickers.append(ticker)
					self.logger.debug(f"[ENTRY-FILTER] {ticker}: no data (pass-through)")
					filtered_watchlist[ticker] = ticker_data
					continue

				df = data_history[ticker]
				if df.empty:
					no_data_tickers.append(ticker)
					self.logger.debug(f"[ENTRY-FILTER] {ticker}: empty data (pass-through)")
					filtered_watchlist[ticker] = ticker_data
					continue

				# Get last 5 days of data for evaluation (supports shift notation like [-1], [-2])
				# Data is sorted newest-first, so [:5] gets the most recent 5 days
				last_5_days = df.iloc[:5].copy() if len(df) >= 5 else df.copy()

				#print(f"[ENTRY-FILTER] {ticker}: Evaluating with {len(last_5_days)} rows of data")
				#print(f"[ENTRY-FILTER] {ticker}: Data columns: {list(last_5_days.columns)}")
				#print(f"[ENTRY-FILTER] {ticker}: Data sample:\n{last_5_days.head(5)}")

				#print(f"[ENTRY-FILTER] {ticker}: {data_history.get(ticker, 'No data in context').columns if ticker in data_history else 'No data in context'}")
				#print(f"[ENTRY-FILTER] {ticker}: {data_history.get(ticker, 'No data in context')}")

				# Debug: Show available columns and values for first few rows
				if len(last_5_days) > 0:
					available_cols = list(last_5_days.columns)
					self.logger.debug(f"[ENTRY-FILTER] {ticker}: Available columns: {available_cols}")
					if 'sha_10_red' in available_cols and 'sha_10_green' in available_cols:
						for i in range(min(3, len(last_5_days))):
							row = last_5_days.iloc[i]
							self.logger.debug(f"[ENTRY-FILTER] {ticker}[{i}]: sha_10_red={row.get('sha_10_red')}, sha_10_green={row.get('sha_10_green')}, sha_10_bullish={row.get('sha_10_bullish')}")

				# Evaluate entry_filter formula
				try:
					self.logger.info(f"[ENTRY-FILTER] {ticker}: Evaluating formula '{entry_filter_formula}' on {len(last_5_days)} rows")

					# Debug: Show actual values at each index
					if len(last_5_days) > 0 and 'sha_10_red' in last_5_days.columns:
						self.logger.info(f"[ENTRY-FILTER] {ticker}: sha_10_red values: {list(last_5_days['sha_10_red'].iloc[:3].values)}")
					if len(last_5_days) > 0 and 'sha_10_bullish' in last_5_days.columns:
						self.logger.info(f"[ENTRY-FILTER] {ticker}: sha_10_bullish values: {list(last_5_days['sha_10_bullish'].iloc[:3].values)}")

					# Debug: Check individual parts
					if len(last_5_days) > 0:
						try:
							red_prev = evaluate("sha_10_red[-1] == 1", last_5_days)
							self.logger.info(f"[ENTRY-FILTER] {ticker}: sha_10_red[-1] == 1 evaluates to {red_prev}")
						except Exception as e:
							self.logger.info(f"[ENTRY-FILTER] {ticker}: sha_10_red[-1] error: {e}")
						try:
							bullish_now = evaluate("sha_10_bullish[0] == 1", last_5_days)
							self.logger.info(f"[ENTRY-FILTER] {ticker}: sha_10_bullish[0] == 1 evaluates to {bullish_now}")
						except Exception as e:
							self.logger.info(f"[ENTRY-FILTER] {ticker}: sha_10_bullish[0] error: {e}")

					passes_filter = evaluate(entry_filter_formula, last_5_days)
					self.logger.info(f"[ENTRY-FILTER] {ticker}: Combined formula result = {passes_filter}")
					if passes_filter:
						self.logger.debug(f"[ENTRY-FILTER] {ticker}: PASS")
						passed_tickers.append(ticker)
						filtered_watchlist[ticker] = ticker_data
					else:
						self.logger.debug(f"[ENTRY-FILTER] {ticker}: BLOCKED")
						blocked_count += 1
				except Exception as e:
						error_msg = str(e)
						available_cols = list(last_5_days.columns) if len(last_5_days) > 0 else []
						# Check if this is a syntax error in the formula
						if "unexpected token" in error_msg.lower() or "syntax error" in error_msg.lower():
							# Could be syntax error OR missing column - check if it's a known column
							import re
							token_match = re.search(r"Token\(INDICATOR, '([a-z_][a-z0-9_]*)\[(-?\d+)\]'\)", error_msg)
							if token_match:
								indicator_name = token_match.group(1)

								# Check if column exists
								if indicator_name in available_cols:
									error_msg = f"Formula syntax error in '{entry_filter_formula}': {error_msg}. Check for missing operators (&&, ||) between expressions."
								else:
									error_msg = f"Missing indicator '{indicator_name}' in formula '{entry_filter_formula}'. Available columns: {available_cols}"
							else:
								error_msg = f"Formula syntax error in '{entry_filter_formula}': {error_msg}. Available columns: {available_cols}"
						elif "not found" in error_msg.lower():
							# Missing indicator error
							error_msg = f"Formula evaluation error in '{entry_filter_formula}': {error_msg}. Available columns: {available_cols}"
						else:
							# Other errors
							error_msg = f"Formula evaluation failed in '{entry_filter_formula}': {error_msg}. Available columns: {available_cols}"

						self.logger.error(f"Entry filter evaluation error for {ticker}: {error_msg}")
						error_tickers.append(f"{ticker} ({error_msg})")
						# On formula error, block the recommendation (don't pass through)
						blocked_count += 1

			# Update context with filtered watchlist
			self.context.set("watchlist", filtered_watchlist)

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
					"passed_count": len(filtered_watchlist),
					"error_tickers": error_tickers,
				},
				"message": f"Filtered {blocked_count} tickers"
			}

		except Exception as e:
			self.logger.error(f"Unexpected error in entry_filter: {str(e)}")
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

		# Check if watchlist exists (can be empty dict but must exist)
		if self.context.get("watchlist") is None:
			self.logger.warning("watchlist not found in context")
			return {
				"status": "error",
				"input": {},
				"output": {},
				"message": "Missing watchlist in context"
			}

		return None
