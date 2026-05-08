"""Agent to generate volume anomaly signals from indicator formulas."""

from typing import Any, Dict, Optional, List
import re
from core.agent import Agent
from tools.formula import evaluate
from tools.indicators.indicators import calculate as calculate_indicators


class VolumeAnomalyAgent(Agent):
	"""Generate volume anomaly signals based on formula from strategy config."""

	def __init__(self, name: str = "VolumeAnomalyAgent"):
		"""Initialize volume anomaly agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Generate volume anomaly signals.

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

		# Get volume anomaly formula from strategy config
		va_formula = None
		if strategy_config:
			signals_config = strategy_config.get("signals", {})
			va_config = signals_config.get("parameters", {}).get("volume_anomaly", {})
			va_formula = va_config.get("formula")

		if not va_formula:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No volume anomaly formula configured"
			}

		# Analyze volume anomalies for each ticker
		va_tickers = []
		for ticker, ticker_data in data_history.items():
			if self._matches_va_formula(ticker_data, va_formula):
				va_tickers.append(ticker)

		strength = len(va_tickers) / len(data_history) if data_history else 0

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"tickers": va_tickers,
				"strength": strength,
				"count": len(va_tickers),
				"total": len(data_history)
			}
		}

	def _matches_va_formula(self, ticker_data: Any, formula: str) -> bool:
		"""Evaluate volume anomaly formula on latest row.

		Args:
			ticker_data: Price history DataFrame
			formula: Python expression to evaluate

		Returns:
			True if volume anomaly condition is met
		"""
		try:
			if not hasattr(ticker_data, 'iloc') or len(ticker_data) == 0:
				return False

			# Extract indicators from formula
			indicators = self._extract_indicators(formula)

			# Calculate only missing indicators (skip if already in data)
			if indicators:
				missing_indicators = [ind for ind in indicators if ind not in ticker_data.columns]
				if missing_indicators:
					try:
						calculated = calculate_indicators(missing_indicators, ticker_data)
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
			self.logger.debug(f"Error evaluating volume anomaly formula: {e}")
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
