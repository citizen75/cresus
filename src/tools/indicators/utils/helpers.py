"""
Helper functions for indicator calculations.

Provides convenient accessors for common column patterns and output validation.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict
from .errors import ColumnError, IndicatorError


def get_close(data: pd.DataFrame) -> pd.Series:
	"""Get close price from data.

	Args:
		data: OHLCV DataFrame

	Returns:
		Close price Series

	Raises:
		ColumnError: If close column not found
	"""
	for col in data.columns:
		if col.lower() == "close":
			return data[col].reset_index(drop=True)
	raise ColumnError("Close column not found in data")


def get_open(data: pd.DataFrame) -> pd.Series:
	"""Get open price from data."""
	for col in data.columns:
		if col.lower() == "open":
			return data[col].reset_index(drop=True)
	raise ColumnError("Open column not found in data")


def get_high(data: pd.DataFrame) -> pd.Series:
	"""Get high price from data."""
	for col in data.columns:
		if col.lower() == "high":
			return data[col].reset_index(drop=True)
	raise ColumnError("High column not found in data")


def get_low(data: pd.DataFrame) -> pd.Series:
	"""Get low price from data."""
	for col in data.columns:
		if col.lower() == "low":
			return data[col].reset_index(drop=True)
	raise ColumnError("Low column not found in data")


def get_volume(data: pd.DataFrame) -> pd.Series:
	"""Get volume from data."""
	for col in data.columns:
		if col.lower() == "volume":
			return data[col].reset_index(drop=True)
	raise ColumnError("Volume column not found in data")


def get_ohlc(data: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
	"""Get OHLC tuple from data.

	Returns:
		Tuple of (open, high, low, close) Series
	"""
	return (get_open(data), get_high(data), get_low(data), get_close(data))


def get_ohlcv(data: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
	"""Get OHLCV tuple from data.

	Returns:
		Tuple of (open, high, low, close, volume) Series
	"""
	return (get_open(data), get_high(data), get_low(data), get_close(data), get_volume(data))


def get_hl(data: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
	"""Get high and low from data.

	Returns:
		Tuple of (high, low) Series
	"""
	return (get_high(data), get_low(data))


def get_hlc(data: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
	"""Get high, low, and close from data.

	Returns:
		Tuple of (high, low, close) Series
	"""
	return (get_high(data), get_low(data), get_close(data))


def validate_indicator_output(
	result: pd.Series or Dict[str, pd.Series],
	indicator_name: str,
	min_value: float = None,
	max_value: float = None
) -> None:
	"""Validate indicator output for NaN/Inf and value ranges.

	Args:
		result: Indicator output (Series or dict of Series)
		indicator_name: Name of indicator for error messages
		min_value: Minimum allowed value (optional)
		max_value: Maximum allowed value (optional)

	Raises:
		IndicatorError: If validation fails
	"""
	series_dict = {}
	if isinstance(result, pd.Series):
		series_dict = {indicator_name: result}
	elif isinstance(result, dict):
		series_dict = result
	else:
		raise IndicatorError(f"Invalid indicator output type: {type(result)}")

	# Check for NaN/Inf in all series
	for key, series in series_dict.items():
		if not isinstance(series, pd.Series):
			continue

		# Check for infinity values
		if np.isinf(series).any():
			raise IndicatorError(
				f"Indicator {indicator_name} ({key}) contains infinity values"
			)

		# Check value ranges if specified
		if min_value is not None and (series < min_value).any():
			raise IndicatorError(
				f"Indicator {indicator_name} ({key}) contains values < {min_value}"
			)

		if max_value is not None and (series > max_value).any():
			raise IndicatorError(
				f"Indicator {indicator_name} ({key}) contains values > {max_value}"
			)


def validate_rsi_output(result: pd.Series) -> None:
	"""Validate RSI output (0-100 range)."""
	validate_indicator_output(result, "RSI", min_value=0, max_value=100)


def validate_binary_output(result: pd.Series or Dict[str, pd.Series]) -> None:
	"""Validate binary output (0 or 1)."""
	series_dict = {}
	if isinstance(result, pd.Series):
		series_dict = {"output": result}
	elif isinstance(result, dict):
		series_dict = result

	for key, series in series_dict.items():
		if not isinstance(series, pd.Series):
			continue
		unique_vals = set(series.dropna().unique())
		if not unique_vals.issubset({0, 1}):
			raise IndicatorError(
				f"Binary indicator ({key}) contains non-binary values: {unique_vals}"
			)


def safe_divide(numerator: pd.Series, denominator: pd.Series, fill_value: float = 0) -> pd.Series:
	"""Safely divide two series, avoiding division by zero.

	Args:
		numerator: Numerator series
		denominator: Denominator series
		fill_value: Value to use where denominator is zero

	Returns:
		Result series with no division by zero errors
	"""
	result = pd.Series(fill_value, index=numerator.index)
	valid_mask = denominator != 0
	result[valid_mask] = numerator[valid_mask] / denominator[valid_mask]
	return result
