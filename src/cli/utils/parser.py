"""Safe argument parsing utilities."""

import re
from typing import Any, Dict, List, Optional, Type, Union


class ValidationError(Exception):
	"""Raised when argument validation fails."""

	pass


class ArgParser:
	"""Safe argument parser with validation.

	Examples:
		parser = ArgParser()
		args = parser.parse_positional(input_str, ['name', 'count'])
		args = parser.parse_with_flags(input_str, {
			'--source': 'str',
			'--limit': 'int',
			'--force': 'bool'
		})
	"""

	@staticmethod
	def parse_positional(
		args_str: str,
		names: List[str],
		optional: Optional[List[str]] = None,
	) -> Dict[str, str]:
		"""Parse positional arguments.

		Args:
			args_str: Raw argument string
			names: Names of positional arguments
			optional: Names of optional positional arguments

		Returns:
			Dictionary mapping names to values

		Raises:
			ValidationError: If required arguments missing
		"""
		optional = optional or []
		required_count = len(names) - len(optional)

		parts = args_str.split()
		if len(parts) < required_count:
			missing = names[len(parts) : required_count]
			raise ValidationError(f"Missing required arguments: {', '.join(missing)}")

		result = {}
		for i, name in enumerate(names):
			result[name] = parts[i] if i < len(parts) else None

		return result

	@staticmethod
	def parse_with_flags(
		args_str: str,
		flag_spec: Dict[str, Type],
		positional: Optional[List[str]] = None,
	) -> Dict[str, Any]:
		"""Parse arguments with flags.

		Args:
			args_str: Raw argument string
			flag_spec: Dict mapping flag names to types ('str', 'int', 'bool')
			positional: Names of positional arguments (optional)

		Returns:
			Dictionary mapping flags/positionals to values

		Raises:
			ValidationError: If parsing fails
		"""
		result = {}
		positional_vals = []

		parts = args_str.split()
		i = 0

		while i < len(parts):
			part = parts[i]

			if part.startswith("--"):
				# Handle flag
				flag = part
				if flag not in flag_spec:
					raise ValidationError(f"Unknown flag: {flag}")

				flag_type = flag_spec[flag]

				if flag_type == "bool":
					result[flag] = True
					i += 1
				else:
					if i + 1 >= len(parts) or parts[i + 1].startswith("--"):
						raise ValidationError(f"Flag {flag} requires a value")
					value = parts[i + 1]
					result[flag] = ArgParser._coerce_type(value, flag_type)
					i += 2
			else:
				# Positional argument
				positional_vals.append(part)
				i += 1

		# Map positional arguments
		if positional:
			for j, name in enumerate(positional):
				if j < len(positional_vals):
					result[name] = positional_vals[j]
				else:
					raise ValidationError(f"Missing required positional: {name}")

		return result

	@staticmethod
	def _coerce_type(value: str, type_name: Union[Type, str]) -> Any:
		"""Coerce string value to specified type.

		Args:
			value: String value
			type_name: Type name ('str', 'int', 'float', 'bool')

		Returns:
			Coerced value

		Raises:
			ValidationError: If coercion fails
		"""
		if isinstance(type_name, type):
			type_name = type_name.__name__

		try:
			if type_name == "str":
				return value
			elif type_name == "int":
				return int(value)
			elif type_name == "float":
				return float(value)
			elif type_name == "bool":
				return value.lower() in ("true", "yes", "1", "on")
			else:
				raise ValidationError(f"Unknown type: {type_name}")
		except ValueError as e:
			raise ValidationError(f"Cannot convert '{value}' to {type_name}: {e}")

	@staticmethod
	def extract_subcommand(args_str: str) -> tuple[Optional[str], str]:
		"""Extract subcommand from arguments.

		Args:
			args_str: Raw argument string

		Returns:
			Tuple of (subcommand, remaining_args)

		Examples:
			"list --limit 10" -> ("list", "--limit 10")
			"create foo bar" -> ("create", "foo bar")
		"""
		parts = args_str.split(None, 1)
		if not parts:
			return None, ""

		return parts[0], parts[1] if len(parts) > 1 else ""

	@staticmethod
	def parse_key_value(args_str: str, sep: str = "=") -> Dict[str, str]:
		"""Parse key=value pairs.

		Args:
			args_str: Raw argument string ("key1=val1 key2=val2")
			sep: Separator character

		Returns:
			Dictionary of key-value pairs

		Raises:
			ValidationError: If format invalid
		"""
		result = {}
		pairs = args_str.split()

		for pair in pairs:
			if sep not in pair:
				raise ValidationError(f"Invalid key-value pair: {pair} (expected format: key{sep}value)")

			key, value = pair.split(sep, 1)
			result[key] = value

		return result

	@staticmethod
	def parse_comma_separated(args_str: str, strip: bool = True) -> List[str]:
		"""Parse comma-separated values.

		Args:
			args_str: Raw argument string
			strip: Whether to strip whitespace

		Returns:
			List of values
		"""
		items = args_str.split(",")
		if strip:
			items = [item.strip() for item in items]
		return [item for item in items if item]
