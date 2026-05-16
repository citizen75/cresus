"""Numeric formula evaluator for DSL and traditional syntax.

Evaluates mathematical formulas to numeric results.
Supports both DSL syntax (close[0]) and traditional syntax (data['close']).
Uses the DSL parser from tools.formula for consistent evaluation.
"""

import re
import pandas as pd
from typing import Any, Dict, Optional, Union
from loguru import logger
from .dsl_parser import evaluate_dsl
from .dsl_helpers import is_dsl_formula


def evaluate_numeric_formula(formula: str, data: Union[Dict[str, Any], pd.DataFrame]) -> Optional[float]:
	"""Evaluate a numeric formula to a float result.

	Supports DSL syntax like "close[0] * 1.5" or traditional syntax like "data['close'] * 1.5"
	Uses the DSL parser from tools.formula for consistent evaluation.

	Args:
		formula: Formula string (DSL or traditional syntax)
		data: Dictionary or DataFrame with column data (e.g., OHLCV + indicators)

	Returns:
		Evaluated result as float, or None if evaluation fails or formula is disabled
	"""
	if not formula or not isinstance(formula, str):
		return None

	# Handle disabled formulas
	if formula.strip().lower() == 'false':
		return None

	try:
		# Convert dict to simple dict for eval context
		if isinstance(data, dict):
			data_dict = data
		elif isinstance(data, pd.DataFrame):
			row_dict = data.iloc[0].to_dict()
			# Normalize column names to lowercase for DSL compatibility
			data_dict = {k.lower(): v for k, v in row_dict.items()}
		else:
			data_dict = {}

		# Convert DSL syntax to traditional syntax for numeric evaluation
		# (DSL parser is for boolean expressions, not numeric results)
		eval_formula = _convert_dsl_to_traditional(formula)

		# Create safe evaluation context
		namespace = {
			"data": data_dict,
			"abs": abs,
			"round": round,
			"max": max,
			"min": min,
			"int": int,
			"float": float,
		}

		# Evaluate the formula using Python's eval with restricted builtins
		result = eval(eval_formula, {"__builtins__": {}}, namespace)

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


def evaluate_position_size(formula: str, data: Dict[str, Any], max_shares: Optional[int] = None) -> Optional[int]:
	"""Evaluate position size formula and return integer share count.

	Args:
		formula: Formula string like "1000 / close[0]"
		data: Dictionary with column data
		max_shares: Optional maximum share limit

	Returns:
		Share count as integer, or None if evaluation fails
	"""
	import math

	result = evaluate_numeric_formula(formula, data)

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


def _convert_dsl_to_traditional(formula: str) -> str:
	"""Convert DSL syntax to traditional data['column'] syntax.

	Converts: close[0] -> data['close']
	Converts: ema_20[-1] -> data['ema_20'] (ignores shift for numeric calculations)
	Leaves traditional syntax unchanged: data['close']
	"""
	# Replace DSL patterns: identifier[shift] -> data['identifier']
	def replace_dsl(match):
		indicator = match.group(1)
		# Ignore the shift notation for numeric calculations
		return f"data['{indicator}']"

	# Pattern: identifier[number] or identifier[-number]
	# Match both lowercase and uppercase identifiers to handle case variations
	dsl_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\[-?\d+\]'
	converted = re.sub(dsl_pattern, replace_dsl, formula)
	return converted
