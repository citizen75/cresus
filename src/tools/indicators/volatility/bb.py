"""
Bollinger Bands Indicator

Syntax: bb_<period>_<std_dev> or bollinger_bands_<period>_<std_dev>
Example: bb_20_2

Returns: Dict with 'bb_upper', 'bb_middle', 'bb_lower' Series
"""

import pandas as pd
from typing import Optional, Dict
from ..utils.helpers import get_close


def calculate(
	data: pd.DataFrame,
	period: int = 20,
	std_dev: float = 2,
	history_df: Optional[pd.DataFrame] = None,
	**kwargs
) -> Dict[str, pd.Series]:
	"""
	Calculate Bollinger Bands.

	Args:
		data: OHLCV DataFrame
		period: SMA period (default: 20)
		std_dev: Standard deviation multiplier (default: 2)
		history_df: Optional historical data for extended lookback

	Returns:
		Dict with keys:
			- 'bb': Upper band
			- 'bb_upper': Upper band
			- 'bb_middle': Middle band (SMA)
			- 'bb_lower': Lower band
	"""
	# Get close prices
	close = get_close(data)

	# Use history if provided
	if history_df is not None:
		hist_close = get_close(history_df)
		combined = pd.concat([hist_close, close], ignore_index=True)
	else:
		combined = close

	# Calculate SMA and standard deviation
	sma = combined.rolling(window=period, min_periods=1).mean()
	std = combined.rolling(window=period, min_periods=1).std()

	# Calculate bands
	upper = sma + (std_dev * std)
	lower = sma - (std_dev * std)
	middle = sma

	# Extract only current period
	result_len = len(data)
	lower = lower.iloc[-result_len:].reset_index(drop=True)
	middle = middle.iloc[-result_len:].reset_index(drop=True)
	upper = upper.iloc[-result_len:].reset_index(drop=True)

	return {
		f"bb_{period}": upper,
		f"bb_{period}_upper": upper,
		f"bb_{period}_middle": middle,
		f"bb_{period}_lower": lower,
	}
