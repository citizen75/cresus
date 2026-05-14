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


def simplify_formula(formula: str, for_dataframe: bool = False) -> str:
	"""Convert DSL shorthand to pandas shift notation.
	
	Args:
		formula: Formula string with optional DSL syntax
		for_dataframe: If True, convert 'and'/'or' to '&'/'|' for Series operations
		
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
	
	# First replace shift notation
	formula = re.sub(DSL_PATTERN, replace_shift, formula)
	
	# If evaluating on DataFrame, convert 'and'/'or' to '&'/'|' for Series operations
	if for_dataframe:
		# Replace logical operators with bitwise equivalents
		# Use word boundaries to avoid partial matches
		formula = re.sub(r'\band\b', '&', formula)
		formula = re.sub(r'\bor\b', '|', formula)
		
		# Add parentheses around comparisons and convert bare Series to boolean
		# Split by & and |, process each part
		parts = re.split(r'(&|\|)', formula)
		result_parts = []
		for part in parts:
			part = part.strip()
			if part in ('&', '|'):
				result_parts.append(part)
			elif any(op in part for op in ['==', '!=', '<', '>', '<=', '>=']):
				# This part has a comparison, wrap it if not already wrapped
				if not (part.startswith('(') and part.endswith(')')):
					result_parts.append(f'({part})')
				else:
					result_parts.append(part)
			elif part:
				# This is a bare Series reference (no comparison)
				# Convert to boolean by checking != 0
				if not (part.startswith('(') and part.endswith(')')):
					result_parts.append(f'(({part}) != 0)')
				else:
					result_parts.append(f'({part} != 0)')
		
		formula = ' '.join(result_parts)
	
	return formula


def is_dsl_formula(formula: str) -> bool:
	"""Check if formula uses DSL syntax.

	Args:
		formula: Formula string to check

	Returns:
		True if formula contains DSL notation (indicator[n]) or DSL operators (&&, ||, !, comparisons)
	"""
	# Check for shift notation or DSL operators
	has_shift_notation = bool(re.search(DSL_PATTERN, formula))
	# DSL operators: logical (&&, ||, !), comparisons (==, !=, <, >, <=, >=), arithmetic in compound expressions
	has_dsl_operators = bool(re.search(r'(&&|\|\||!(?!=)|!=|<=|>=|==|[<>])', formula))
	return has_shift_notation or has_dsl_operators


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
