"""
OBV (On-Balance Volume) Indicator

Syntax: obv

Returns: Series with OBV values
"""

import pandas as pd
from typing import Optional
from ..utils.helpers import get_close, get_volume


def calculate(
    data: pd.DataFrame,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate OBV (On-Balance Volume).

    Args:
        data: OHLCV DataFrame
        history_df: Optional historical data for extended lookback

    Returns:
        Series with OBV values

    Formula:
        OBV = previous OBV + volume (if close > previous close)
        OBV = previous OBV - volume (if close < previous close)
        OBV = previous OBV (if close == previous close)
    """
    # Get close and volume
    close = get_close(data)
    volume = get_volume(data)

    # Use history if provided
    if history_df is not None:
        hist_close = get_close(history_df)
        hist_volume = get_volume(history_df)

        close = pd.concat([hist_close, close], ignore_index=True)
        volume = pd.concat([hist_volume, volume], ignore_index=True)

    # Calculate OBV
    price_diff = close.diff()
    obv_values = volume.copy()

    # Determine direction
    obv_values = obv_values * (price_diff.apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0)))

    # Cumulative sum
    obv = obv_values.cumsum()

    # Extract only current period
    result_len = len(data)
    obv = obv.iloc[-result_len:].reset_index(drop=True)

    return obv.fillna(0.0)
