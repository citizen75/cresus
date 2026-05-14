"""
Lowest/Highest Price Indicators

Syntax: lowest_<period> or highest_<period>
Example: lowest_60 (lowest low over past 60 bars)

Returns: Series with lowest/highest values over the period
"""

import pandas as pd
from typing import Optional


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
	low = data.get("LOW", data.get("Low", None))

	if low is None:
		return pd.Series([0.0] * len(data))

	# Use history if provided
	if history_df is not None:
		hist_low = history_df.get("LOW", history_df.get("Low", None))
		if hist_low is not None:
			low = pd.concat([hist_low, low], ignore_index=True)

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
	high = data.get("HIGH", data.get("High", None))

	if high is None:
		return pd.Series([0.0] * len(data))

	# Use history if provided
	if history_df is not None:
		hist_high = history_df.get("HIGH", history_df.get("High", None))
		if hist_high is not None:
			high = pd.concat([hist_high, high], ignore_index=True)

	# Calculate rolling maximum (highest)
	highest = high.rolling(window=period, min_periods=1).max()

	# Extract only current period
	result_len = len(data)
	highest = highest.iloc[-result_len:].reset_index(drop=True)

	return highest.fillna(0.0)
