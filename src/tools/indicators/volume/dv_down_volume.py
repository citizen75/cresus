"""
Directional Volume - Down Volume Indicator

Syntax: dv_down_volume
Returns: Series with cumulative down volume (volume on days when Close < Open)
"""

import pandas as pd
from typing import Optional
from ..utils.helpers import get_close, get_open, get_volume


def calculate(
	data: pd.DataFrame,
	history_df: Optional[pd.DataFrame] = None,
	**kwargs
) -> pd.Series:
	"""
	Calculate directional down volume (volume on down days).

	Down day is defined as: Close < Open

	Args:
		data: OHLCV DataFrame with columns: Open, High, Low, Close, Volume
		history_df: Optional historical data (not used for this indicator)

	Returns:
		Series with volume on down days (0 if up day)
	"""
	close = get_close(data)
	open_price = get_open(data)
	volume = get_volume(data)

	down_days = close < open_price
	down_volume = volume.where(down_days, 0)

	return down_volume.reset_index(drop=True)
