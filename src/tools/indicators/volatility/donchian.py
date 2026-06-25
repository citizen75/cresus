"""
Donchian Channel Indicator

Syntax: dc_<period> or dc_<period>_<upper|lower|mid>
Example: dc_20, dc_20_upper, dc_20_lower, dc_20_mid

Returns: Dict with 'dc_<period>', 'dc_<period>_upper', 'dc_<period>_mid', 'dc_<period>_lower' Series
"""

import pandas as pd
from typing import Optional, Dict
from ..utils.helpers import get_high, get_low


def calculate(
	data: pd.DataFrame,
	period: int = 20,
	history_df: Optional[pd.DataFrame] = None,
	**kwargs
) -> Dict[str, pd.Series]:
	"""
	Calculate Donchian Channel.

	Args:
		data: OHLCV DataFrame with HIGH, LOW columns
		period: Lookback period (default: 20)
		history_df: Optional historical data for extended lookback

	Returns:
		Dict with keys:
			- 'dc_<period>': Upper band (alias)
			- 'dc_<period>_upper': Highest high over the period
			- 'dc_<period>_mid': Midpoint of upper and lower bands
			- 'dc_<period>_lower': Lowest low over the period

	Formula:
		upper = highest(HIGH, period)
		lower = lowest(LOW, period)
		mid = (upper + lower) / 2
	"""
	high = get_high(data)
	low = get_low(data)

	# Use history if provided
	if history_df is not None:
		hist_high = get_high(history_df)
		hist_low = get_low(history_df)
		high = pd.concat([hist_high, high], ignore_index=True)
		low = pd.concat([hist_low, low], ignore_index=True)

	upper = high.rolling(window=period, min_periods=1).max()
	lower = low.rolling(window=period, min_periods=1).min()
	mid = (upper + lower) / 2

	# Extract only current period
	result_len = len(data)
	upper = upper.iloc[-result_len:].reset_index(drop=True)
	lower = lower.iloc[-result_len:].reset_index(drop=True)
	mid = mid.iloc[-result_len:].reset_index(drop=True)

	return {
		f"dc_{period}": upper,
		f"dc_{period}_upper": upper,
		f"dc_{period}_mid": mid,
		f"dc_{period}_lower": lower,
	}
