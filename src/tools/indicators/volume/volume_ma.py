"""Volume moving average indicator."""

from typing import Optional
import pandas as pd


def calculate(
	df: pd.DataFrame,
	period: int = 20,
	history_df: Optional[pd.DataFrame] = None,
	**kwargs
) -> pd.Series:
	"""Calculate volume SMA (simple moving average).

	Computes a simple moving average (SMA) of volume over the specified period.
	Useful for detecting volume anomalies when volume is significantly above/below average.

	Args:
		df: DataFrame with OHLCV data (must have 'volume' or 'VOLUME' column)
		period: Period for moving average (default: 20)
		history_df: Optional historical data (not used for this indicator)
		**kwargs: Additional parameters (ignored)

	Returns:
		Series with volume SMA values
	"""
	# Handle both lowercase and uppercase column names
	volume_col = None
	if "volume" in df.columns:
		volume_col = "volume"
	elif "VOLUME" in df.columns:
		volume_col = "VOLUME"
	
	if volume_col is None:
		raise ValueError("Volume column not found in data")

	# Calculate simple moving average of volume
	result = df[volume_col].rolling(window=period, min_periods=1).mean()
	return result
