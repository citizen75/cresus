"""Formula evaluator for strategy conditions and trend formulas."""

from typing import Any, Dict, Optional
import pandas as pd


def evaluate(formula: str, data: Dict[str, Any]) -> bool:
	"""Evaluate a formula expression safely.

	Args:
		formula: Python expression string using 'data' dict notation
		         Example: "data['close'] > data['ema_20'] and data['adx_14'] > 25"
		data: Dictionary of column values for the formula

	Returns:
		Boolean result of the formula evaluation

	Raises:
		ValueError: If formula is invalid or evaluation fails
	"""
	if not formula:
		raise ValueError("Formula cannot be empty")

	try:
		# Use pandas eval for safer expression evaluation
		result = pd.eval(formula, local_dict={"data": data}, global_dict={})
		return bool(result)

	except Exception as e:
		raise ValueError(f"Failed to evaluate formula '{formula}': {str(e)}")
