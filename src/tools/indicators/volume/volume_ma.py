"""Volume moving average indicator."""

from typing import Dict, Any
import pandas as pd


def calculate(df: pd.DataFrame, period: int = 20) -> Dict[str, Any]:
	"""Calculate volume SMA (simple moving average).

	Computes a simple moving average (SMA) of volume over the specified period.
	Useful for detecting volume anomalies when volume is significantly above/below average.

	Args:
		df: DataFrame with OHLCV data (must have 'volume' column)
		period: Period for moving average (default: 20)

	Returns:
		Dict with:
			- status: "success" or "error"
			- data: DataFrame with original columns + volume_sma_X column (X = period)
			- message: Status message
	"""
	try:
		if "volume" not in df.columns:
			return {
				"status": "error",
				"data": df,
				"message": "Volume column not found in data",
			}

		# Calculate simple moving average of volume
		df_copy = df.copy()
		df_copy[f"volume_sma_{period}"] = df_copy["volume"].rolling(window=period, min_periods=1).mean()

		return {
			"status": "success",
			"data": df_copy,
			"message": f"Volume SMA {period}-period calculated",
		}

	except Exception as e:
		return {
			"status": "error",
			"data": df,
			"message": f"Error calculating volume SMA: {str(e)}",
		}
