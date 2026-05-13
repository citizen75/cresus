"""Strategy configuration validator.

Validates strategy configurations against required structure and rules.
"""

from typing import Dict, List, Any, Tuple


class StrategyValidator:
	"""Validate strategy configurations.

	Uses template as source of truth for required structure.
	No hardcoded field definitions - all structure comes from template.
	"""

	def validate(self, strategy_config: Dict[str, Any]) -> Tuple[bool, List[str]]:
		"""Validate strategy configuration structure.

		Basic structural validation. For full validation including template compliance,
		use StrategyManager.validate_against_template() which uses template as source of truth.

		Args:
			strategy_config: Strategy configuration dictionary

		Returns:
			Tuple of (is_valid, error_messages)
		"""
		errors = []

		# Basic validation: ensure it's a dict
		if not isinstance(strategy_config, dict):
			errors.append("Strategy configuration must be a dictionary")
			return False, errors

		# Check basic required fields that every strategy needs
		if not strategy_config.get("name"):
			errors.append("Missing required field: name")

		if not strategy_config.get("description"):
			errors.append("Missing required field: description")

		# Validate indicators if present
		indicator_errors = self._validate_indicators(strategy_config)
		errors.extend(indicator_errors)

		return len(errors) == 0, errors


	def _validate_indicators(self, strategy_config: Dict[str, Any]) -> List[str]:
		"""Validate indicator list if present.

		Args:
			strategy_config: Strategy configuration

		Returns:
			List of error messages
		"""
		errors = []

		indicators = strategy_config.get("indicators")
		if indicators is None:
			# Indicators not defined - will be caught by template validation
			return errors

		if not isinstance(indicators, list):
			errors.append("indicators must be a list")
			return errors

		# Check for common indicator name issues
		for indicator in indicators:
			if not isinstance(indicator, str):
				errors.append(f"Indicator must be a string, got: {type(indicator).__name__}")
			elif not indicator:
				errors.append("Indicator name cannot be empty")

		return errors

	def validate_against_template(self, strategy_config: Dict[str, Any], template_config: Dict[str, Any]) -> List[str]:
		"""Validate strategy against template structure to find extra keys.

		Args:
			strategy_config: Strategy configuration
			template_config: Template configuration

		Returns:
			List of warning messages for extra keys
		"""
		warnings = []
		self._find_extra_keys(strategy_config, template_config, "", warnings)
		return warnings

	def _find_extra_keys(self, strategy_item: Any, template_item: Any, path: str, warnings: List[str]):
		"""Recursively find extra keys in strategy not present in template.

		Args:
			strategy_item: Current item in strategy
			template_item: Current item in template
			path: Current path in the structure
			warnings: List to accumulate warning messages
		"""
		if not isinstance(strategy_item, dict) or not isinstance(template_item, dict):
			return

		# Check each key in strategy
		for key in strategy_item.keys():
			current_path = f"{path}.{key}" if path else key

			# If key doesn't exist in template
			if key not in template_item:
				warnings.append(f"Extra key not in template: {current_path}")
			else:
				# Recursively check nested dictionaries
				strategy_value = strategy_item[key]
				template_value = template_item[key]

				if isinstance(strategy_value, dict) and isinstance(template_value, dict):
					self._find_extra_keys(strategy_value, template_value, current_path, warnings)
