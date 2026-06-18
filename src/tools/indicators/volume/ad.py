"""Accumulation/Distribution Line (A/D Line) indicator."""

import pandas as pd
import numpy as np
from typing import Optional


def calculate(df: pd.DataFrame, history_df: Optional[pd.DataFrame] = None, **kwargs) -> pd.Series:
	"""Calculate Accumulation/Distribution Line.

	The A/D Line is a volume-weighted indicator that accumulates volume based on
	the price position within the daily range. It helps identify bullish/bearish
	volume accumulation.

	Formula:
		Money Flow Multiplier = ((Close - Low) - (High - Close)) / (High - Low)
		Money Flow Volume = Money Flow Multiplier × Volume
		A/D = Previous A/D + Money Flow Volume

	Args:
		df: DataFrame with OHLCV data (must have high, low, close, volume columns)
		history_df: Optional historical data for extended lookback

	Returns:
		Series with A/D values

	Raises:
		ValueError: If required OHLCV columns are not found
	"""
	# Helper to get column case-insensitively
	def get_column(data, column_names):
		"""Get first available column from list of names (case-insensitive)."""
		for col_name in column_names:
			# Check exact match
			if col_name in data.columns:
				return data[col_name].values
			# Check case-insensitive match
			for actual_col in data.columns:
				if actual_col.lower() == col_name.lower():
					return data[actual_col].values
		raise ValueError(f"Missing required column: {column_names}")

	# Get OHLCV columns with validation
	try:
		high = get_column(df, ['high', 'HIGH'])
	except ValueError as e:
		raise ValueError(f"AD Line calculation failed: {e}") from None

	try:
		low = get_column(df, ['low', 'LOW'])
	except ValueError as e:
		raise ValueError(f"AD Line calculation failed: {e}") from None

	try:
		close = get_column(df, ['close', 'CLOSE'])
	except ValueError as e:
		raise ValueError(f"AD Line calculation failed: {e}") from None

	try:
		volume = get_column(df, ['volume', 'VOLUME'])
	except ValueError as e:
		raise ValueError(f"AD Line calculation failed: {e}") from None

	# Use history if provided for extended lookback
	if history_df is not None:
		try:
			hist_high = get_column(history_df, ['high', 'HIGH'])
			hist_low = get_column(history_df, ['low', 'LOW'])
			hist_close = get_column(history_df, ['close', 'CLOSE'])
			hist_volume = get_column(history_df, ['volume', 'VOLUME'])

			high = np.concatenate([hist_high, high])
			low = np.concatenate([hist_low, low])
			close = np.concatenate([hist_close, close])
			volume = np.concatenate([hist_volume, volume])
		except (ValueError, KeyError):
			# If history data doesn't have required columns, use only current data
			pass

	# Calculate the Money Flow Multiplier
	hl_range = high - low
	# Avoid division by zero
	hl_range = np.where(hl_range == 0, 1, hl_range)

	mfm = ((close - low) - (high - close)) / hl_range

	# Calculate Money Flow Volume
	mfv = mfm * volume

	# Calculate cumulative A/D from entire history
	ad_line = np.cumsum(mfv)

	# Extract only current period if history was used
	result_len = len(df)
	ad_line = ad_line[-result_len:]

	return pd.Series(ad_line, index=df.index)
