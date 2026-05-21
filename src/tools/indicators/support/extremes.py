"""
Lowest/Highest Price Indicators

Syntax: lowest_<period> or highest_<period>
Example: lowest_60 (lowest low over past 60 bars)

Returns: Series with lowest/highest values over the period
"""

import pandas as pd
from typing import Optional
from ..utils.helpers import get_high, get_low


def calculate_lowest(
	data: pd.DataFrame,
	period: int = 14,
	history_df: Optional[pd.DataFrame] = None,
	**kwargs
) -> pd.Series:
	"""
	Calculate Lowest Low over a period.

	Args:
		data: OHLCV DataFrame with LOW column
		period: Lookback period (default: 14)
		history_df: Optional historical data for extended lookback

	Returns:
		Series with lowest low values over the period

	Formula:
		Lowest = minimum(LOW) over last N bars
	"""
	# Get LOW
	try:
		low = get_low(data)
	except Exception:
		return pd.Series([0.0] * len(data))

	# Use history if provided
	if history_df is not None:
		try:
			hist_low = get_low(history_df)
			low = pd.concat([hist_low, low], ignore_index=True)
		except Exception:
			pass

	# Calculate rolling minimum (lowest)
	lowest = low.rolling(window=period, min_periods=1).min()

	# Extract only current period
	result_len = len(data)
	lowest = lowest.iloc[-result_len:].reset_index(drop=True)

	return lowest.fillna(0.0)


def calculate_highest(
	data: pd.DataFrame,
	period: int = 14,
	history_df: Optional[pd.DataFrame] = None,
	**kwargs
) -> pd.Series:
	"""
	Calculate Highest High over a period.

	Args:
		data: OHLCV DataFrame with HIGH column
		period: Lookback period (default: 14)
		history_df: Optional historical data for extended lookback

	Returns:
		Series with highest high values over the period

	Formula:
		Highest = maximum(HIGH) over last N bars
	"""
	# Get HIGH
	try:
		high = get_high(data)
	except Exception:
		return pd.Series([0.0] * len(data))

	# Use history if provided
	if history_df is not None:
		try:
			hist_high = get_high(history_df)
			high = pd.concat([hist_high, high], ignore_index=True)
		except Exception:
			pass

	# Calculate rolling maximum (highest)
	highest = high.rolling(window=period, min_periods=1).max()

	# Extract only current period
	result_len = len(data)
	highest = highest.iloc[-result_len:].reset_index(drop=True)

	return highest.fillna(0.0)
