"""Strategy configuration formula evaluator.

Evaluates mathematical formulas from strategy config with data context.
Safely evaluates formulas like: "data['close'] - data['atr_14'] * 1.5"
"""

import re
from typing import Any, Dict, Optional
from loguru import logger


class ConfigEvaluator:
	"""Evaluate strategy configuration formulas with data context."""

	@staticmethod
	def evaluate_formula(formula: str, data: Dict[str, Any]) -> Optional[float]:
		"""Safely evaluate a formula string with data context.

		Args:
			formula: Formula string like "data['close'] - data['atr_14'] * 1.5"
			data: Dictionary with data context (e.g., OHLCV data)

		Returns:
			Evaluated result as float, or None if evaluation fails or formula is disabled (False)
		"""
		if not formula or not isinstance(formula, str):
			return None

		# Handle disabled formulas: return None for 'False' (string) or False (boolean result)
		if formula.strip().lower() == 'false':
			return None

		try:
			# Create safe namespace with data dict and built-in functions
			namespace = {
				"data": data,
				"abs": abs,
				"round": round,
				"max": max,
				"min": min,
				"int": int,
				"float": float,
			}

			# Evaluate the formula
			result = eval(formula, {"__builtins__": {}}, namespace)

			# If result is boolean False, treat as disabled
			if isinstance(result, bool) and result is False:
				return None

			# Convert to float
			if result is not None:
				return float(result)

			return None

		except Exception as e:
			logger.error(f"Failed to evaluate formula '{formula}': {e}")
			return None

	@staticmethod
	def evaluate_position_size(
		formula: str, data: Dict[str, Any], max_shares: Optional[int] = None
	) -> Optional[int]:
		"""Evaluate position size formula and return integer share count.

		Args:
			formula: Formula string like "1000 / data['close']"
			data: Dictionary with data context
			max_shares: Optional maximum share limit

		Returns:
			Share count as integer, or None if evaluation fails
		"""
		import math
		result = ConfigEvaluator.evaluate_formula(formula, data)

		if result is None:
			return None

		# Check for NaN or Inf values
		if math.isnan(result) or math.isinf(result):
			return None

		shares = int(result)

		# Apply max limit if provided
		if max_shares is not None:
			shares = min(shares, max_shares)

		return max(0, shares)  # Ensure non-negative
