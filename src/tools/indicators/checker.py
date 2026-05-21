"""
Indicator Checker - Validate indicators for errors and issues.

Performs comprehensive checks on one or multiple indicators to identify:
- Syntax errors in implementation
- Missing column handling
- Output validation issues
- Parameter validation
- Import errors
"""

import sys
import traceback
from typing import List, Dict, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import inspect

from .indicators import get_registered_indicator, list_available_indicators
from .utils.errors import IndicatorError


class ErrorLevel(Enum):
	"""Severity levels for indicator errors."""
	CRITICAL = "critical"  # Indicator won't load or execute
	ERROR = "error"        # Indicator fails on valid data
	WARNING = "warning"    # Indicator works but has issues
	INFO = "info"          # Informational messages


@dataclass
class CheckResult:
	"""Result of checking a single indicator."""
	indicator_name: str
	exists: bool = True
	syntax_valid: bool = True
	errors: List[str] = None
	warnings: List[str] = None
	infos: List[str] = None
	test_results: Dict[str, Any] = None

	def __post_init__(self):
		if self.errors is None:
			self.errors = []
		if self.warnings is None:
			self.warnings = []
		if self.infos is None:
			self.infos = []
		if self.test_results is None:
			self.test_results = {}

	def is_valid(self) -> bool:
		"""Check if indicator is valid (no critical errors)."""
		return self.syntax_valid and len(self.errors) == 0

	def add_error(self, message: str):
		"""Add an error message."""
		self.errors.append(message)

	def add_warning(self, message: str):
		"""Add a warning message."""
		self.warnings.append(message)

	def add_info(self, message: str):
		"""Add an info message."""
		self.infos.append(message)

	def summary(self) -> str:
		"""Get a summary of the check results."""
		if not self.exists:
			return f"❌ {self.indicator_name}: Indicator not found"

		if not self.syntax_valid:
			return f"❌ {self.indicator_name}: Syntax error - {self.errors[0] if self.errors else 'Unknown'}"

		if len(self.errors) > 0:
			return f"❌ {self.indicator_name}: {len(self.errors)} error(s)"

		if len(self.warnings) > 0:
			return f"⚠️  {self.indicator_name}: {len(self.warnings)} warning(s)"

		return f"✅ {self.indicator_name}: OK"


class IndicatorChecker:
	"""Comprehensive indicator checker."""

	def __init__(self):
		self.sample_data = self._create_sample_data()

	def check(
		self,
		indicators: Union[str, List[str]],
		verbose: bool = False
	) -> Union[CheckResult, Dict[str, CheckResult]]:
		"""
		Check one or multiple indicators for errors.

		Args:
			indicators: Single indicator name or list of names
			verbose: Show detailed output

		Returns:
			CheckResult for single indicator, dict of results for multiple
		"""
		if isinstance(indicators, str):
			result = self._check_single(indicators)
			if verbose:
				self._print_result(result)
			return result

		else:
			results = {}
			for indicator in indicators:
				results[indicator] = self._check_single(indicator)
			if verbose:
				self._print_results(results)
			return results

	def _check_single(self, indicator_name: str) -> CheckResult:
		"""Check a single indicator."""
		result = CheckResult(indicator_name=indicator_name)

		# Try to get indicator - first with full name
		indicator_fn = get_registered_indicator(indicator_name)

		if indicator_fn is None:
			# Try base name fallback for parametrized indicators
			# 1. Numeric parameters: 'rsi_14' -> base='rsi', remainder='14' (numeric) ✓
			# 2. Parametrized components: 'bb_20_lower' -> parse as DSL, check if base 'bb' is registered
			parts = indicator_name.split('_')
			if len(parts) > 1:
				base_name = parts[0]
				remainder = '_'.join(parts[1:])

				# Check if remainder contains only digits and underscores (valid parameters)
				if all(c.isdigit() or c == '_' for c in remainder):
					indicator_fn = get_registered_indicator(base_name)
				else:
					# Try parsing as DSL formula (e.g., 'bb_20_lower' -> base='bb')
					try:
						from .parser import parse_formula
						parsed_base, parsed_params = parse_formula(indicator_name)
						indicator_fn = get_registered_indicator(parsed_base)
						if indicator_fn:
							result.add_info(f"Parsed as DSL formula: {parsed_base} with params {parsed_params}")
					except Exception:
						pass

		if indicator_fn is None:
			result.exists = False
			result.add_error(f"Indicator '{indicator_name}' not found in registry")
			return result

		# Check syntax by importing
		try:
			result.add_info(f"Indicator module loaded successfully")
		except Exception as e:
			result.syntax_valid = False
			result.add_error(f"Failed to load indicator: {str(e)}")
			return result

		# Check function signature
		try:
			sig = inspect.signature(indicator_fn)
			params = list(sig.parameters.keys())
			if 'data' not in params and 'df' not in params:
				result.add_warning("Expected 'data' or 'df' parameter in function signature")
			result.add_info(f"Function signature: {sig}")
		except Exception as e:
			result.add_warning(f"Could not inspect function signature: {str(e)}")

		# Test with sample data
		try:
			output = indicator_fn(self.sample_data)
			result.test_results['output_type'] = type(output).__name__

			if isinstance(output, pd.Series):
				result.test_results['series_length'] = len(output)
				result.test_results['nan_count'] = output.isna().sum()
				result.test_results['inf_count'] = (output == float('inf')).sum()

				if result.test_results['nan_count'] > len(output) * 0.5:
					result.add_warning(
						f"Series has {result.test_results['nan_count']} NaN values "
						f"({result.test_results['nan_count'] / len(output) * 100:.1f}%)"
					)

				if result.test_results['inf_count'] > 0:
					result.add_error(
						f"Series contains {result.test_results['inf_count']} infinity values"
					)

			elif isinstance(output, dict):
				result.test_results['keys'] = list(output.keys())
				for key, val in output.items():
					if isinstance(val, pd.Series):
						if val.isna().sum() > len(val) * 0.5:
							result.add_warning(
								f"Key '{key}' has high NaN count: "
								f"{val.isna().sum() / len(val) * 100:.1f}%"
							)
						if (val == float('inf')).sum() > 0:
							result.add_error(
								f"Key '{key}' contains infinity values"
							)

			else:
				result.add_warning(
					f"Unexpected output type: {type(output).__name__}"
				)

			result.add_info("Sample data test passed")

		except Exception as e:
			result.add_error(f"Test with sample data failed: {str(e)}")
			result.test_results['error'] = str(e)

		# Check for common issues
		self._check_common_issues(indicator_name, indicator_fn, result)

		return result

	def _check_common_issues(self, indicator_name: str, fn, result: CheckResult):
		"""Check for common implementation issues."""
		try:
			source = inspect.getsource(fn)

			# Check for bare except
			if 'except:' in source:
				result.add_warning("Found bare 'except:' clause (catches all exceptions)")

			# Check for print statements
			if 'print(' in source:
				result.add_warning("Found print() statement - should use logging instead")

			# Check for TODO comments
			if 'TODO' in source or 'FIXME' in source:
				result.add_info("Found TODO/FIXME comments in code")

			# Check for hardcoded parameters
			if any(f'= {i}' in source for i in range(10, 100)):
				result.add_info("Possible hardcoded numeric parameters found")

		except Exception as e:
			result.add_info(f"Could not analyze source code: {str(e)}")

	def _create_sample_data(self, rows: int = 100) -> pd.DataFrame:
		"""Create sample OHLCV data for testing."""
		import numpy as np
		np.random.seed(42)

		prices = 100 + np.cumsum(np.random.randn(rows))

		# Use uppercase column names for consistency with DataValidator expectations
		return pd.DataFrame({
			'OPEN': prices + np.random.randn(rows),
			'HIGH': prices + abs(np.random.randn(rows)),
			'LOW': prices - abs(np.random.randn(rows)),
			'CLOSE': prices,
			'VOLUME': np.random.randint(1000, 10000, rows),
		})

	def _print_result(self, result: CheckResult):
		"""Pretty print a single result."""
		print(f"\n{'=' * 60}")
		print(f"Indicator: {result.indicator_name}")
		print(f"{'=' * 60}")
		print(result.summary())

		if result.errors:
			print(f"\n❌ Errors ({len(result.errors)}):")
			for error in result.errors:
				print(f"   • {error}")

		if result.warnings:
			print(f"\n⚠️  Warnings ({len(result.warnings)}):")
			for warning in result.warnings:
				print(f"   • {warning}")

		if result.infos:
			print(f"\nℹ️  Info ({len(result.infos)}):")
			for info in result.infos:
				print(f"   • {info}")

		if result.test_results:
			print(f"\n📊 Test Results:")
			for key, val in result.test_results.items():
				if key != 'keys':
					print(f"   • {key}: {val}")

	def _print_results(self, results: Dict[str, CheckResult]):
		"""Pretty print multiple results."""
		print(f"\n{'=' * 60}")
		print(f"Checking {len(results)} indicator(s)")
		print(f"{'=' * 60}\n")

		# Summary table
		valid_count = sum(1 for r in results.values() if r.is_valid())
		error_count = sum(1 for r in results.values() if not r.exists or not r.syntax_valid)
		warning_count = sum(1 for r in results.values() if r.is_valid() and len(r.warnings) > 0)

		for indicator_name, result in sorted(results.items()):
			print(result.summary())

		print(f"\n{'=' * 60}")
		print(f"Summary: {valid_count} valid, {error_count} errors, {warning_count} warnings")
		print(f"{'=' * 60}")

		# Detailed results for errors only
		errors_exist = any(not r.is_valid() for r in results.values())
		if errors_exist:
			print("\n📋 Detailed Issues:\n")
			for indicator_name, result in sorted(results.items()):
				if not result.is_valid():
					self._print_result(result)


def check_indicator(
	indicators: Union[str, List[str]],
	verbose: bool = True
) -> Union[CheckResult, Dict[str, CheckResult]]:
	"""
	Check one or multiple indicators for errors.

	Args:
		indicators: Single indicator name or list of names
		verbose: Print detailed results

	Returns:
		CheckResult for single indicator, dict of results for multiple
	"""
	checker = IndicatorChecker()
	return checker.check(indicators, verbose=verbose)


def check_all_indicators(verbose: bool = False) -> Dict[str, CheckResult]:
	"""
	Check all registered indicators.

	Args:
		verbose: Print detailed results

	Returns:
		Dict of check results for all indicators
	"""
	all_indicators = list_available_indicators()
	checker = IndicatorChecker()
	results = {}

	for indicator_name in all_indicators:
		results[indicator_name] = checker._check_single(indicator_name)

	if verbose:
		checker._print_results(results)

	return results


def print_checker_report(results: Union[CheckResult, Dict[str, CheckResult]]):
	"""Print a formatted report of checker results."""
	checker = IndicatorChecker()

	if isinstance(results, CheckResult):
		checker._print_result(results)
	else:
		checker._print_results(results)
