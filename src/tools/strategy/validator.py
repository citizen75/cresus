"""Strategy configuration validator.

Validates strategy configurations against required structure and rules.
"""

from typing import Dict, List, Any, Tuple, Set, Union
from src.tools.formula import check_syntax, extract_indicators, validate_formulas
from src.tools.indicators import check_indicator, CheckResult

# Data fields that are not indicators (OHLCV data)
DATA_FIELDS = {'open', 'high', 'low', 'close', 'volume', 'timestamp', 'ticker', 'date'}


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

	def validate_formulas(self, strategy_config: Dict[str, Any]) -> Tuple[List[str], List[str]]:
		"""Validate all formulas in strategy configuration.

		Args:
			strategy_config: Strategy configuration dictionary

		Returns:
			Tuple of (formula_errors, invalid_formulas)
			- formula_errors: List of error messages from validation
			- invalid_formulas: List of invalid formula strings
		"""
		errors = []
		invalid_formulas = []
		formulas = self._collect_all_formulas(strategy_config)

		if not formulas:
			return errors, invalid_formulas

		# Validate all formulas
		all_valid, invalid = validate_formulas(formulas)

		if not all_valid:
			for result in invalid:
				invalid_formulas.append(result.formula)
				errors.append(f"Invalid formula: {result.formula} - {result.error_message}")

		return errors, invalid_formulas

	def extract_indicators_from_strategy(self, strategy_config: Dict[str, Any]) -> Set[str]:
		"""Extract all indicators referenced in strategy formulas.

		Args:
			strategy_config: Strategy configuration dictionary

		Returns:
			Set of indicator names found in all formulas (excluding data fields)
		"""
		formulas = self._collect_all_formulas(strategy_config)

		if not formulas:
			return set()

		all_indicators = set()
		for formula in formulas:
			if formula and isinstance(formula, str):
				indicators = extract_indicators(formula)
				# Filter out data fields (close, volume, etc.) which are not indicators
				indicators = {ind for ind in indicators if ind.lower() not in DATA_FIELDS}
				all_indicators.update(indicators)

		return all_indicators

	def validate_extracted_indicators(
		self,
		strategy_config: Dict[str, Any]
	) -> Tuple[Dict[str, CheckResult], List[str]]:
		"""Validate all indicators extracted from strategy formulas.

		Extracts all indicators referenced in formulas and validates them
		against the indicator checker to ensure they exist and work correctly.

		Args:
			strategy_config: Strategy configuration dictionary

		Returns:
			Tuple of (check_results_dict, error_messages)
			- check_results_dict: Dict mapping indicator names to CheckResult objects
			- error_messages: List of error messages from invalid indicators
		"""
		# Extract all indicators from formulas
		extracted_indicators = self.extract_indicators_from_strategy(strategy_config)

		if not extracted_indicators:
			return {}, []

		# Check all extracted indicators
		check_results = check_indicator(
			list(extracted_indicators),
			verbose=False
		)

		# Ensure we have a dict even for single indicator
		if not isinstance(check_results, dict):
			check_results = {list(extracted_indicators)[0]: check_results}

		# Collect error messages from invalid indicators
		error_messages = []
		for indicator_name, result in check_results.items():
			if not result.is_valid():
				if result.errors:
					for error in result.errors:
						error_messages.append(f"Indicator '{indicator_name}': {error}")
				else:
					error_messages.append(f"Indicator '{indicator_name}': Invalid")

		return check_results, error_messages

	def validate_indicators_in_declaration(
		self,
		strategy_config: Dict[str, Any]
	) -> Tuple[Dict[str, CheckResult], List[str]]:
		"""Validate all indicators declared in strategy.indicators list.

		Validates indicators explicitly declared in the 'indicators' field.

		Args:
			strategy_config: Strategy configuration dictionary

		Returns:
			Tuple of (check_results_dict, error_messages)
		"""
		indicators = strategy_config.get("indicators", [])

		if not indicators:
			return {}, []

		# Check all declared indicators
		check_results = check_indicator(indicators, verbose=False)

		# Ensure we have a dict
		if not isinstance(check_results, dict):
			check_results = {indicators[0]: check_results}

		# Collect error messages
		error_messages = []
		for indicator_name, result in check_results.items():
			if not result.is_valid():
				if result.errors:
					for error in result.errors:
						error_messages.append(f"Declared indicator '{indicator_name}': {error}")
				else:
					error_messages.append(f"Declared indicator '{indicator_name}': Invalid")

		return check_results, error_messages

	def validate_all_indicators(
		self,
		strategy_config: Dict[str, Any]
	) -> Dict[str, Any]:
		"""Validate both declared and extracted indicators comprehensively.

		Validates:
		1. Indicators declared in strategy.indicators
		2. Indicators extracted from all formulas
		3. Consistency between declared and extracted

		Args:
			strategy_config: Strategy configuration dictionary

		Returns:
			Dict with:
			- 'declared_results': Check results for declared indicators
			- 'declared_errors': Error messages for declared indicators
			- 'extracted_results': Check results for extracted indicators
			- 'extracted_errors': Error messages for extracted indicators
			- 'missing_from_declaration': Extracted indicators not in declaration
			- 'total_errors': Combined error count
			- 'is_valid': Whether all checks passed
		"""
		# Validate declared indicators
		declared_results, declared_errors = self.validate_indicators_in_declaration(
			strategy_config
		)

		# Validate extracted indicators
		extracted_results, extracted_errors = self.validate_extracted_indicators(
			strategy_config
		)

		# Check for missing indicators (excluding data fields)
		declared_names = set(strategy_config.get("indicators", []))
		extracted_names = set(extracted_results.keys())
		missing_from_declaration = extracted_names - declared_names
		# Filter out data fields from missing list
		missing_from_declaration = {ind for ind in missing_from_declaration if ind.lower() not in DATA_FIELDS}

		return {
			'declared_results': declared_results,
			'declared_errors': declared_errors,
			'extracted_results': extracted_results,
			'extracted_errors': extracted_errors,
			'declared_indicators': list(declared_names),
			'extracted_indicators': list(extracted_names),
			'missing_from_declaration': list(missing_from_declaration),
			'total_errors': len(declared_errors) + len(extracted_errors),
			'is_valid': (
				len(declared_errors) == 0 and
				len(extracted_errors) == 0 and
				len(missing_from_declaration) == 0
			),
		}

	def _collect_all_formulas(self, strategy_config: Dict[str, Any]) -> List[str]:
		"""Collect all formulas from strategy configuration.

		Args:
			strategy_config: Strategy configuration dictionary

		Returns:
			List of all formula strings found
		"""
		formulas = []

		# Watchlist formulas
		watchlist = strategy_config.get("watchlist", {})
		if isinstance(watchlist, dict):
			params = watchlist.get("parameters", {})
			if isinstance(params, dict):
				for param_name, param_cfg in params.items():
					if isinstance(param_cfg, dict) and "formula" in param_cfg:
						formula = param_cfg.get("formula")
						if formula:
							formulas.append(formula)

		# Features/Alphas formulas
		features = strategy_config.get("features", {})
		if isinstance(features, dict):
			alphas = features.get("alphas", {})
			if isinstance(alphas, dict):
				for alpha_group, alpha_list in alphas.items():
					if isinstance(alpha_list, list):
						for alpha_item in alpha_list:
							if isinstance(alpha_item, dict) and "formula" in alpha_item:
								formula = alpha_item.get("formula")
								if formula:
									formulas.append(formula)

		# Signals formulas
		signals = strategy_config.get("signals", {})
		if isinstance(signals, dict):
			sig_params = signals.get("parameters", {})
			if isinstance(sig_params, dict):
				for param_name, param_cfg in sig_params.items():
					if isinstance(param_cfg, dict) and "formula" in param_cfg:
						formula = param_cfg.get("formula")
						# Skip disabled signals (formula='False')
						if formula and formula != 'False':
							formulas.append(formula)

		# Entry formulas
		entry = strategy_config.get("entry", {})
		if isinstance(entry, dict):
			entry_params = entry.get("parameters", {})
			if isinstance(entry_params, dict):
				for param_name, param_cfg in entry_params.items():
					if isinstance(param_cfg, dict) and "formula" in param_cfg:
						formula = param_cfg.get("formula")
						if formula:
							formulas.append(formula)

		# Order formulas
		order = strategy_config.get("order", {})
		if isinstance(order, dict):
			order_params = order.get("parameters", {})
			if isinstance(order_params, dict):
				for param_name, param_cfg in order_params.items():
					if isinstance(param_cfg, dict) and "formula" in param_cfg:
						formula = param_cfg.get("formula")
						if formula:
							formulas.append(formula)

		# Exit formulas
		exit_cfg = strategy_config.get("exit", {})
		if isinstance(exit_cfg, dict):
			exit_params = exit_cfg.get("parameters", {})
			if isinstance(exit_params, dict):
				for param_name, param_cfg in exit_params.items():
					if isinstance(param_cfg, dict) and "formula" in param_cfg:
						formula = param_cfg.get("formula")
						# Skip disabled exit conditions (formula='False')
						if formula and formula != 'False':
							formulas.append(formula)

		return formulas
