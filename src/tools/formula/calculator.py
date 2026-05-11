"""Formula evaluator for strategy conditions and trend formulas."""

from typing import Any, Dict, Optional
import pandas as pd
from .dsl_helpers import simplify_formula, is_dsl_formula


def evaluate(formula: str, data: Dict[str, Any]) -> bool:
	"""Evaluate a formula expression safely.

	Supports both traditional and simplified DSL syntax:
	- Traditional: "data['close'] > data['ema_20']"
	- DSL: "close[0] > ema_20[0]"

	Args:
		formula: Python expression string
		         Examples:
		         - Traditional: "data['close'] > data['ema_20'] and data['adx_14'] > 25"
		         - DSL: "close[0] > ema_20[0] and adx_14[0] > 25"
		         - Mixed with shift: "sha_10_green[-1] == 1 and ema_20[0] < close[0]"
		data: Dictionary of column values for the formula

	Returns:
		Boolean result of the formula evaluation

	Raises:
		ValueError: If formula is invalid or evaluation fails
	"""
	if not formula:
		raise ValueError("Formula cannot be empty")

	try:
		print(f"Evaluating formula: {formula} with data: {data}")
		
		# Convert DSL syntax if present
		if is_dsl_formula(formula):
			formula = simplify_formula(formula)
		
		# Use pandas eval for safer expression evaluation
		result = pd.eval(formula, local_dict={"data": data}, global_dict={})
		return bool(result)

	except KeyError as e:
		# Extract the missing key from the error message
		missing_key = str(e).strip("'\"")
		raise ValueError(f"Missing indicator or column '{missing_key}' in formula '{formula}'. Available columns: {list(data.keys())}")
	except Exception as e:
		raise ValueError(f"Failed to evaluate formula '{formula}': {str(e)}")
