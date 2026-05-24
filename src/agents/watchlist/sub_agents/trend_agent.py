"""Agent to filter watchlist by trend analysis using strategy config formula."""

from typing import Any, Dict, Optional, List
import re
import os
from pathlib import Path
from core.agent import Agent
from core.context import AgentContext
from tools.formula import evaluate
from tools.strategy.strategy import StrategyManager


class FilterAgent(Agent):
	"""Filter watchlist using formula from strategy configuration.

	Reads tickers, data_history, and filter formula from context.
	Filters tickers where the filter formula evaluates to True.
	Formula is a Python expression evaluated on each row of data.

	Example formula: "data['close'] > data['ema_20'] and data['ema_20'] > data['ema_50'] and data['adx_14'] > 25"
	"""

	def __init__(self, name: str = "FilterAgent"):
		"""Initialize trend agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Filter watchlist using formula from strategy config.

		Reads 'watchlist', 'data_history', and filter formula from context.
		Evaluates filter formula on latest row of each ticker's data.
		Stores filtered tickers back in context.

		Args:
			input_data: Input data (not used, uses context instead)

		Returns:
			Response with trend analysis results
		"""
		self.logger.debug("[WATCHLIST][FILTER] Starting trend analysis")
		if input_data is None:
			input_data = {}

		watchlist = self.context.get("watchlist")
		data_history = self.context.get("data_history")
		strategy_config = self.context.get("strategy_config")

		if not watchlist:
			self.logger.error("No watchlist available in context for filter analysis")
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No watchlist in context"
			}

		if not data_history:
			self.logger.error("No data history available for trend analysis")
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No data history available for trend analysis"
			}

		# Get filter formula from strategy config
		trend_formula = None
		if strategy_config:
			watchlist_config = strategy_config.get("watchlist", {})
			trend_config = watchlist_config.get("parameters", {}).get("filter", {})
			trend_formula = trend_config.get("formula")

		if not trend_formula:
			self.logger.warning("No filter formula found in strategy config")
			return {
				"status": "success",
				"input": input_data,
				"output": {
					"trend_count": len(watchlist),
					"removed_count": 0,
					"formula_available": False
				}
			}


		# Analyze trend for each ticker in watchlist
		trending_watchlist = {}
		pass_count = 0
		fail_count = 0
		for ticker in list(watchlist.keys()):
			if ticker in data_history:
				ticker_data = data_history[ticker]
				if self._matches_filter_formula(ticker_data, trend_formula):
					trending_watchlist[ticker] = watchlist[ticker]
					pass_count += 1
					self.logger.info(f"[FILTER] {ticker}: PASS")
				else:
					fail_count += 1
					self.logger.info(f"[FILTER] {ticker}: FAIL")

		removed_count = len(watchlist) - len(trending_watchlist)
		self.context.set("watchlist", trending_watchlist)
		self.logger.debug(f"[FILTER] filtered watchlist: {len(trending_watchlist)} tickers passed, {removed_count} removed")
		return {
			"status": "success",
			"input": input_data,
			"output": {
				"filtered_count": len(trending_watchlist),
				"removed_count": removed_count,
				"formula_available": True
			}
		}

	def _matches_filter_formula(self, ticker_data: Any, formula: str) -> bool:
		"""Evaluate filter formula on latest row of ticker data.

		Supports both traditional 'data[col]' notation and DSL shift notation like 'col[0]', 'col[-1]'.

		Args:
			ticker_data: Price history DataFrame
			formula: Python expression to evaluate (e.g., "sha_10_up[0] == 1")

		Returns:
			True if formula evaluates to True on latest row
		"""
		try:
			if not hasattr(ticker_data, 'iloc') or len(ticker_data) == 0:
				return False

			# Pass full data to evaluate, which handles sorting and shift notation
			result = evaluate(formula, ticker_data)
			self.logger.debug(f"[FILTER] Formula '{formula}' evaluated to {result}")
			return result

		except Exception as e:
			self.logger.error(f"[FILTER] Error evaluating filter formula '{formula}': {e}")
			return False

