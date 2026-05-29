"""Input validation utilities."""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional


class Validator:
	"""Input validation utilities."""

	@staticmethod
	def is_valid_date(date_str: str, format: str = "%Y-%m-%d") -> bool:
		"""Check if string is valid date.

		Args:
			date_str: Date string
			format: Expected format

		Returns:
			True if valid date, False otherwise
		"""
		try:
			datetime.strptime(date_str, format)
			return True
		except ValueError:
			return False

	@staticmethod
	def is_valid_ticker(ticker: str) -> bool:
		"""Check if string is valid ticker.

		Args:
			ticker: Ticker symbol

		Returns:
			True if valid ticker format
		"""
		# Ticker: 2-6 uppercase letters, optional .exchange (1-2 letters for exchange codes like PA, L, SW)
		pattern = r"^[A-Z]{2,6}(\.[A-Z]{1,2})?$"
		return bool(re.match(pattern, ticker))

	@staticmethod
	def is_valid_identifier(name: str) -> bool:
		"""Check if string is valid identifier (strategy, screener name, etc).

		Args:
			name: Identifier string

		Returns:
			True if valid identifier
		"""
		# Identifier: alphanumeric + underscore, starts with letter
		pattern = r"^[a-zA-Z_][a-zA-Z0-9_]*$"
		return bool(re.match(pattern, name))

	@staticmethod
	def is_valid_path(path_str: str, must_exist: bool = False) -> bool:
		"""Check if string is valid file path.

		Args:
			path_str: Path string
			must_exist: Whether path must exist

		Returns:
			True if valid path
		"""
		try:
			path = Path(path_str)
			if must_exist:
				return path.exists()
			return True
		except (ValueError, TypeError):
			return False

	@staticmethod
	def is_valid_percentage(value: str) -> bool:
		"""Check if string is valid percentage (0-100).

		Args:
			value: Value string

		Returns:
			True if valid percentage
		"""
		try:
			num = float(value)
			return 0 <= num <= 100
		except ValueError:
			return False

	@staticmethod
	def is_positive_number(value: str) -> bool:
		"""Check if string is positive number.

		Args:
			value: Value string

		Returns:
			True if positive number
		"""
		try:
			num = float(value)
			return num > 0
		except ValueError:
			return False

	@staticmethod
	def is_valid_formula(formula: str) -> bool:
		"""Check if string looks like valid formula.

		Args:
			formula: Formula string

		Returns:
			True if formula syntax looks valid
		"""
		# Basic checks: has operators and indicators
		if not formula:
			return False

		# Should contain comparison operators
		has_operator = any(op in formula for op in ["<", ">", "==", "!=", "<=", ">=", "&&", "||"])
		if not has_operator:
			return False

		# Check for balanced brackets
		return formula.count("[") == formula.count("]")

	@staticmethod
	def validate_required_string(value: Optional[str], field_name: str = "Field") -> tuple[bool, Optional[str]]:
		"""Validate required string field.

		Args:
			value: String value
			field_name: Field name for error message

		Returns:
			Tuple of (is_valid, error_message)
		"""
		if not value or not value.strip():
			return False, f"{field_name} is required"
		return True, None

	@staticmethod
	def validate_choice(value: str, choices: list, field_name: str = "Field") -> tuple[bool, Optional[str]]:
		"""Validate choice from list.

		Args:
			value: Value to check
			choices: List of valid choices
			field_name: Field name for error message

		Returns:
			Tuple of (is_valid, error_message)
		"""
		if value not in choices:
			return False, f"{field_name} must be one of: {', '.join(choices)}"
		return True, None

	@staticmethod
	def validate_range(value: str, min_val: Optional[float] = None, max_val: Optional[float] = None, field_name: str = "Field") -> tuple[bool, Optional[str]]:
		"""Validate numeric range.

		Args:
			value: String value
			min_val: Minimum value (inclusive)
			max_val: Maximum value (inclusive)
			field_name: Field name for error message

		Returns:
			Tuple of (is_valid, error_message)
		"""
		try:
			num = float(value)
		except ValueError:
			return False, f"{field_name} must be a number"

		if min_val is not None and num < min_val:
			return False, f"{field_name} must be >= {min_val}"

		if max_val is not None and num > max_val:
			return False, f"{field_name} must be <= {max_val}"

		return True, None

	@staticmethod
	def validate_length(value: str, min_len: Optional[int] = None, max_len: Optional[int] = None, field_name: str = "Field") -> tuple[bool, Optional[str]]:
		"""Validate string length.

		Args:
			value: String value
			min_len: Minimum length
			max_len: Maximum length
			field_name: Field name for error message

		Returns:
			Tuple of (is_valid, error_message)
		"""
		if min_len is not None and len(value) < min_len:
			return False, f"{field_name} must be at least {min_len} characters"

		if max_len is not None and len(value) > max_len:
			return False, f"{field_name} must be at most {max_len} characters"

		return True, None
