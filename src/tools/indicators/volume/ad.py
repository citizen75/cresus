"""Accumulation/Distribution Line (A/D Line) indicator."""

import pandas as pd
import numpy as np


def calculate(df: pd.DataFrame, **kwargs) -> pd.Series:
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

	Returns:
		Series with A/D values
	"""
	# Ensure required columns exist
	for col in ['high', 'low', 'close', 'volume']:
		if col.upper() in df.columns:
			df = df.copy()
			df[col] = df[col.upper()]
		elif col not in df.columns:
			raise ValueError(f"Missing required column: {col}")

	high = df['high'].values if 'high' in df.columns else df['HIGH'].values
	low = df['low'].values if 'low' in df.columns else df['LOW'].values
	close = df['close'].values if 'close' in df.columns else df['CLOSE'].values
	volume = df['volume'].values if 'volume' in df.columns else df['VOLUME'].values

	# Calculate the Money Flow Multiplier
	hl_range = high - low
	# Avoid division by zero
	hl_range = np.where(hl_range == 0, 1, hl_range)

	mfm = ((close - low) - (high - close)) / hl_range

	# Calculate Money Flow Volume
	mfv = mfm * volume

	# Calculate cumulative A/D
	ad_line = np.cumsum(mfv)

	return pd.Series(ad_line, index=df.index)
