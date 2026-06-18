"""
Directional Volume - Up Volume Indicator

Syntax: dv_up_volume
Returns: Series with cumulative up volume (volume on days when Close > Open)
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
	Calculate directional up volume (volume on up days).

	Up day is defined as: Close > Open

	Args:
		data: OHLCV DataFrame with columns: Open, High, Low, Close, Volume
		history_df: Optional historical data (not used for this indicator)

	Returns:
		Series with volume on up days (0 if down day)
	"""
	close = get_close(data)
	open_price = get_open(data)
	volume = get_volume(data)

	up_days = close > open_price
	up_volume = volume.where(up_days, 0)

	return up_volume.reset_index(drop=True)
