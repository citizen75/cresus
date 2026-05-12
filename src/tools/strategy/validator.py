"""Strategy configuration validator.

Validates strategy configurations against required structure and rules.
"""

from typing import Dict, List, Any, Tuple


class StrategyValidator:
	"""Validate strategy configurations."""

	REQUIRED_TOP_LEVEL_KEYS = ["name", "description", "engine"]
	VALID_ENGINES = ["TaModel", "LightGbmModel", "AnomalyModel"]
	REQUIRED_SECTIONS = ["entry", "exit"]
	OPTIONAL_SECTIONS = ["watchlist", "signals", "order", "backtest"]

	def validate(self, strategy_config: Dict[str, Any]) -> Tuple[bool, List[str]]:
		"""Validate strategy configuration.

		Args:
			strategy_config: Strategy configuration dictionary

		Returns:
			Tuple of (is_valid, error_messages)
		"""
		errors = []

		# Check required top-level keys
		for key in self.REQUIRED_TOP_LEVEL_KEYS:
			if key not in strategy_config:
				errors.append(f"Missing required key: {key}")

		# Check engine is valid
		if "engine" in strategy_config:
			engine = strategy_config.get("engine")
			if engine not in self.VALID_ENGINES:
				errors.append(
					f"Invalid engine '{engine}'. Must be one of: {', '.join(self.VALID_ENGINES)}"
				)

		# Check required sections
		for section in self.REQUIRED_SECTIONS:
			if section not in strategy_config:
				errors.append(f"Missing required section: {section}")
			elif not isinstance(strategy_config.get(section), dict):
				errors.append(f"Section '{section}' must be a dictionary")

		# Validate entry section
		if "entry" in strategy_config:
			entry_errors = self._validate_entry_section(strategy_config.get("entry", {}))
			errors.extend(entry_errors)

		# Validate exit section
		if "exit" in strategy_config:
			exit_errors = self._validate_exit_section(strategy_config.get("exit", {}))
			errors.extend(exit_errors)

		# Validate indicators exist if referenced
		indicator_errors = self._validate_indicators(strategy_config)
		errors.extend(indicator_errors)

		return len(errors) == 0, errors

	def _validate_entry_section(self, entry_config: Dict[str, Any]) -> List[str]:
		"""Validate entry section.

		Args:
			entry_config: Entry configuration

		Returns:
			List of error messages
		"""
		errors = []

		if not isinstance(entry_config, dict):
			return ["entry section must be a dictionary"]

		# Check if enabled and has parameters
		if entry_config.get("enabled"):
			params = entry_config.get("parameters", {})
			if not isinstance(params, dict):
				errors.append("entry.parameters must be a dictionary")
				return errors

			# Check required parameters
			required_params = ["position_size", "order_type", "entry_filter"]
			for param in required_params:
				if param not in params:
					errors.append(f"entry.parameters missing required parameter: {param}")
				else:
					param_val = params[param]
					if isinstance(param_val, dict) and "formula" not in param_val:
						errors.append(
							f"entry.parameters.{param} missing 'formula' key"
						)

		return errors

	def _validate_exit_section(self, exit_config: Dict[str, Any]) -> List[str]:
		"""Validate exit section.

		Args:
			exit_config: Exit configuration

		Returns:
			List of error messages
		"""
		errors = []

		if not isinstance(exit_config, dict):
			return ["exit section must be a dictionary"]

		# Check if enabled and has parameters
		if exit_config.get("enabled"):
			params = exit_config.get("parameters", {})
			if not isinstance(params, dict):
				errors.append("exit.parameters must be a dictionary")
				return errors

			# Check required parameters
			required_params = ["stop", "take_profit"]
			for param in required_params:
				if param not in params:
					errors.append(f"exit.parameters missing required parameter: {param}")
				else:
					param_val = params[param]
					if isinstance(param_val, dict):
						# For stop parameter, check for 'type' and 'formula'
						if param == "stop":
							if "type" not in param_val:
								errors.append(
									f"exit.parameters.{param} missing 'type' key (should be 'fix' or 'trailing')"
								)
							if "formula" not in param_val:
								errors.append(
									f"exit.parameters.{param} missing 'formula' key"
								)
						elif "formula" not in param_val:
							errors.append(
								f"exit.parameters.{param} missing 'formula' key"
							)

		return errors

	def _validate_indicators(self, strategy_config: Dict[str, Any]) -> List[str]:
		"""Validate that referenced indicators are defined.

		Args:
			strategy_config: Strategy configuration

		Returns:
			List of error messages
		"""
		errors = []

		indicators = strategy_config.get("indicators", [])
		if not indicators:
			errors.append("No indicators defined. At least one indicator is required.")
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
