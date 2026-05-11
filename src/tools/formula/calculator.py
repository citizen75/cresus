"""Formula evaluator for strategy conditions and trend formulas."""

from typing import Union
import pandas as pd
from .dsl_parser import evaluate_dsl, parse_formula
from .dsl_helpers import is_dsl_formula


def evaluate(formula: str, data: Union[dict, pd.DataFrame]) -> bool:
	"""Evaluate a formula expression safely.

	Supports both DSL syntax and traditional pandas syntax:

	DSL syntax (recommended for strategy formulas):
	- Indicator notation: sha_10_green[-1], ema_20[0], adx_14[-2]
	- Logical operators: && (and), || (or), ! (not)
	- Comparisons: ==, !=, <, >, <=, >=
	- Arithmetic: +, -, *, /
	- Examples:
	  - "sha_10_green[-1] && sha_10_red[-2] == 1"
	  - "ema_20 < close && adx_14 > adx_14[-1]"
	  - "(rsi_14 > 50) || (macd_12_26 > 0)"

	Traditional pandas syntax (legacy, for backward compatibility):
	- "data['close'] > data['ema_20']"
	- "data['adx_14'] > 25"

	Args:
		formula: DSL or traditional pandas formula string
		data: Dictionary of column values or DataFrame for the formula
		      - dict: evaluates current bar (shift notation not supported)
		      - DataFrame: supports shift notation (data must be sorted newest-first)

	Returns:
		Boolean result of the formula evaluation

	Raises:
		ValueError: If formula is invalid or evaluation fails
		KeyError: If indicator or column is not found
	"""
	if not formula:
		raise ValueError("Formula cannot be empty")

	try:
		# Try DSL parsing first
		if is_dsl_formula(formula):
			return evaluate_dsl(formula, data)
		
		# Fall back to traditional pandas syntax for backward compatibility
		result = pd.eval(formula, local_dict={"data": data}, global_dict={})
		
		# If result is a Series (from DataFrame), get the first value
		if isinstance(result, pd.Series):
			result = result.iloc[0]
		
		return bool(result)

	except KeyError as e:
		# Check if this is a DSL parser error (already has good message)
		error_msg = str(e).strip("'\"")
		if error_msg.startswith("Indicator"):
			# DSL error - raise as ValueError with original message
			raise ValueError(error_msg)
		
		# Traditional pandas KeyError - enhance with available columns
		if isinstance(data, dict):
			available = list(data.keys())
		else:
			available = list(data.columns) if hasattr(data, 'columns') else []
		raise ValueError(f"Missing indicator or column '{error_msg}' in formula '{formula}'. Available columns: {available}")
	except ValueError as e:
		# Re-raise ValueError from DSL parser as-is (already has good message)
		error_msg = str(e)
		if "not found" in error_msg or "not supported" in error_msg or "Formula syntax" in error_msg:
			raise  # Re-raise DSL parser error as-is
		# Otherwise wrap with more context
		raise ValueError(f"Failed to evaluate formula '{formula}': {error_msg}")
	except SyntaxError as e:
		raise ValueError(f"Formula syntax error: {str(e)}")
	except Exception as e:
		raise ValueError(f"Failed to evaluate formula '{formula}': {str(e)}")
