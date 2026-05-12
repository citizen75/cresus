"""Agent to filter watchlist by trend analysis using strategy config formula."""

from typing import Any, Dict, Optional, List
import re
import os
from pathlib import Path
from core.agent import Agent
from core.context import AgentContext
from tools.formula import evaluate
from tools.strategy.strategy import StrategyManager


class TrendAgent(Agent):
	"""Analyze trends using formula from strategy configuration.

	Reads tickers, data_history, and trend formula from context.
	Filters tickers where the trend formula evaluates to True.
	Formula is a Python expression evaluated on each row of data.

	Example formula: "data['close'] > data['ema_20'] and data['ema_20'] > data['ema_50'] and data['adx_14'] > 25"
	"""

	def __init__(self, name: str = "TrendAgent"):
		"""Initialize trend agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Analyze trends using formula from strategy config.

		Reads 'watchlist', 'data_history', and trend formula from context.
		Evaluates trend formula on latest row of each ticker's data.
		Stores filtered tickers back in context.

		Args:
			input_data: Input data (not used, uses context instead)

		Returns:
			Response with trend analysis results
		"""
		if input_data is None:
			input_data = {}

		watchlist = self.context.get("watchlist")
		data_history = self.context.get("data_history")
		strategy_config = self.context.get("strategy_config")

		if not watchlist:
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

		# Get trend formula from strategy config
		trend_formula = None
		if strategy_config:
			watchlist_config = strategy_config.get("watchlist", {})
			trend_config = watchlist_config.get("parameters", {}).get("trend", {})
			trend_formula = trend_config.get("formula")

		if not trend_formula:
			self.logger.warning("No trend formula found in strategy config")
			return {
				"status": "success",
				"input": input_data,
				"output": {
					"trend_count": len(watchlist),
					"removed_count": 0,
					"formula_available": False
				}
			}

		# Extract and add required indicators to strategy config
		required_indicators = self._extract_indicators(trend_formula)
		if required_indicators and strategy_config:
			current_indicators = strategy_config.get("indicators", [])
			added_indicators = [ind for ind in required_indicators if ind not in current_indicators]
			if added_indicators:
				strategy_config["indicators"] = current_indicators + added_indicators
				self.context.set("strategy_config", strategy_config)

				# Save updated config to file
				strategy_name = strategy_config.get("name")
				if strategy_name:
					self._save_strategy_config(strategy_name, strategy_config)
				self.logger.debug(f"Added indicators to strategy config: {added_indicators}")

		# Analyze trend for each ticker in watchlist
		trending_watchlist = []
		for ticker in watchlist:
			if ticker in data_history:
				ticker_data = data_history[ticker]
				if self._matches_trend_formula(ticker_data, trend_formula):
					trending_watchlist.append(ticker)

		removed_count = len(watchlist) - len(trending_watchlist)
		self.context.set("watchlist", trending_watchlist)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"trend_count": len(trending_watchlist),
				"removed_count": removed_count,
				"formula_available": True
			}
		}

	def _matches_trend_formula(self, ticker_data: Any, formula: str) -> bool:
		"""Evaluate trend formula on latest row of ticker data.

		Extracts required indicators from formula and calculates them,
		then evaluates the formula on the latest row.

		Formula is a Python expression using 'data' dict notation.
		Example: "data['close'] > data['ema_20'] and data['ema_20'] > data['ema_50']"

		Args:
			ticker_data: Price history DataFrame
			formula: Python expression to evaluate

		Returns:
			True if formula evaluates to True on latest row
		"""
		try:
			if not hasattr(ticker_data, 'iloc') or len(ticker_data) == 0:
				return False

			# Extract indicator names from formula (e.g., ema_20, adx_14)
			indicators = self._extract_indicators(formula)

			# Check that all required indicators are available (calculated by DataAgent)
			if indicators:
				missing_indicators = [ind for ind in indicators if ind not in ticker_data.columns]
				if missing_indicators:
					self.logger.error(f"Missing indicators {missing_indicators} not pre-calculated by DataAgent for formula: {formula}")
					return False

			# Get latest row
			latest = ticker_data.iloc[0]  # Data is sorted newest-first, so [0] is most recent

			# Create data dict for formula evaluation
			data = latest.to_dict()

			# Evaluate formula safely using pandas eval
			return evaluate(formula, data)

		except Exception as e:
			self.logger.debug(f"Error evaluating trend formula: {e}")
			return False

	def _extract_indicators(self, formula: str) -> List[str]:
		"""Extract indicator names from formula string.

		Looks for patterns like data['indicator_name'] in the formula.

		Args:
			formula: Formula string

		Returns:
			List of unique indicator names found in formula
		"""
		# Find all patterns like data['xxx'] or data["xxx"]
		pattern = r"data\[[\'\"]([^\)\'\"]+)[\'\"]"
		matches = re.findall(pattern, formula)

		# Filter out non-indicator columns (close, open, high, low, volume)
		non_indicators = {"close", "open", "high", "low", "volume", "timestamp", "ticker"}
		indicators = [m for m in matches if m.lower() not in non_indicators]

		# Return unique indicators
		return list(set(indicators))

	def _save_strategy_config(self, strategy_name: str, config: Dict[str, Any]) -> None:
		"""Save updated strategy config to file.

		Args:
			strategy_name: Name of the strategy
			config: Updated strategy configuration
		"""
		try:
			project_root = Path(os.environ.get("CRESUS_PROJECT_ROOT", "."))
			strategy_manager = StrategyManager(project_root)
			result = strategy_manager.save_strategy(strategy_name, config)

			if result.get("status") == "success":
				self.logger.info(f"Saved strategy config: {strategy_name}")
			else:
				self.logger.warning(f"Failed to save strategy config: {result.get('message')}")

		except Exception as e:
			self.logger.warning(f"Error saving strategy config: {e}")
