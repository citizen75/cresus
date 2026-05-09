"""DSL helper functions for simplified formula syntax.

Converts shorthand DSL syntax to pandas shift notation:
  - indicator[0] → data['indicator']  (current bar)
  - indicator[-1] → data.shift(1)['indicator']  (previous bar)
  - indicator[-2] → data.shift(2)['indicator']  (2 bars back)
"""

import re
from typing import Dict


# Pattern to match: word characters, underscore, digits [shift_value]
# Examples: sha_10_green[0], ema_20[-1], adx_14[-2]
DSL_PATTERN = r'(\w+)\[(-?\d+)\]'


def simplify_formula(formula: str) -> str:
	"""Convert DSL shorthand to pandas shift notation.
	
	Args:
		formula: Formula string with optional DSL syntax
		
	Returns:
		Formula with DSL syntax converted to data['...'] and shift notation
		
	Examples:
		>>> simplify_formula("sha_10_green[-1] == 1")
		"data.shift(1)['sha_10_green'] == 1"
		
		>>> simplify_formula("ema_20[0] < close[0]")
		"data['ema_20'] < data['close']"
		
		>>> simplify_formula("adx_14[0] > adx_14[-1]")
		"data['adx_14'] > data.shift(1)['adx_14']"
	"""
	def replace_shift(match) -> str:
		indicator = match.group(1)
		shift_value = int(match.group(2))
		
		if shift_value == 0:
			# Current bar: indicator[0] → data['indicator']
			return f"data['{indicator}']"
		elif shift_value < 0:
			# Previous bars: indicator[-1] → data.shift(1)['indicator']
			return f"data.shift({abs(shift_value)})['{indicator}']"
		else:
			# Future bars (rare): indicator[1] → data.shift(-1)['indicator']
			return f"data.shift(-{shift_value})['{indicator}']"
	
	return re.sub(DSL_PATTERN, replace_shift, formula)


def is_dsl_formula(formula: str) -> bool:
	"""Check if formula uses DSL syntax.
	
	Args:
		formula: Formula string to check
		
	Returns:
		True if formula contains DSL notation (indicator[n])
	"""
	return bool(re.search(DSL_PATTERN, formula))


def convert_formulas_in_dict(data: Dict) -> Dict:
	"""Recursively convert DSL formulas in a dictionary.
	
	Useful for strategy configs that have formulas nested in dicts.
	
	Args:
		data: Dictionary that may contain formula strings
		
	Returns:
		Dictionary with all formula strings converted
	"""
	if not isinstance(data, dict):
		return data
	
	result = {}
	for key, value in data.items():
		if isinstance(value, str) and is_dsl_formula(value):
			result[key] = simplify_formula(value)
		elif isinstance(value, dict):
			result[key] = convert_formulas_in_dict(value)
		elif isinstance(value, list):
			result[key] = [
				simplify_formula(item) if isinstance(item, str) and is_dsl_formula(item) else item
				for item in value
			]
		else:
			result[key] = value
	
	return result
