"""Agent to generate mean reversion signals from indicator formulas."""

from typing import Any, Dict, Optional, List
import re
from core.agent import Agent
from tools.formula import evaluate
from tools.indicators.indicators import calculate as calculate_indicators


class MeanReversionAgent(Agent):
	"""Generate mean reversion signals based on formula from strategy config."""

	def __init__(self, name: str = "MeanReversionAgent"):
		"""Initialize mean reversion agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Generate mean reversion signals.

		Args:
			input_data: Input data (optional, uses context instead)

		Returns:
			Response with signal analysis results
		"""
		if input_data is None:
			input_data = {}

		data_history = self.context.get("data_history")
		strategy_config = self.context.get("strategy_config")

		if not data_history:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No data available"
			}

		# Get mean reversion formula from strategy config
		mr_formula = None
		if strategy_config:
			signals_config = strategy_config.get("signals", {})
			mr_config = signals_config.get("parameters", {}).get("mean_reversion", {})
			mr_formula = mr_config.get("formula")

		if not mr_formula:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No mean reversion formula configured"
			}

		# Analyze mean reversion for each ticker
		mr_tickers = []
		for ticker, ticker_data in data_history.items():
			if self._matches_mr_formula(ticker_data, mr_formula):
				mr_tickers.append(ticker)

		strength = len(mr_tickers) / len(data_history) if data_history else 0

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"tickers": mr_tickers,
				"strength": strength,
				"count": len(mr_tickers),
				"total": len(data_history)
			}
		}

	def _matches_mr_formula(self, ticker_data: Any, formula: str) -> bool:
		"""Evaluate mean reversion formula on latest row.

		Args:
			ticker_data: Price history DataFrame
			formula: Python expression to evaluate

		Returns:
			True if mean reversion condition is met
		"""
		try:
			if not hasattr(ticker_data, 'iloc') or len(ticker_data) == 0:
				return False

			# Extract indicators from formula
			indicators = self._extract_indicators(formula)

			# Calculate missing indicators
			if indicators:
				try:
					calculated = calculate_indicators(indicators, ticker_data)
					for indicator_name, series in calculated.items():
						ticker_data[indicator_name] = series
				except Exception as e:
					self.logger.debug(f"Failed to calculate indicators: {e}")
					return False

			# Get latest row
			latest = ticker_data.iloc[-1]
			data = latest.to_dict()

			# Evaluate formula
			return evaluate(formula, data)

		except Exception as e:
			self.logger.debug(f"Error evaluating mean reversion formula: {e}")
			return False

	def _extract_indicators(self, formula: str) -> List[str]:
		"""Extract indicator names from formula string.

		Args:
			formula: Formula string

		Returns:
			List of unique indicator names
		"""
		pattern = r"data\[[\'\"]([^\)\'\"]+)[\'\"]"
		matches = re.findall(pattern, formula)

		non_indicators = {"close", "open", "high", "low", "volume", "timestamp", "ticker"}
		indicators = [m for m in matches if m.lower() not in non_indicators]

		return list(set(indicators))
