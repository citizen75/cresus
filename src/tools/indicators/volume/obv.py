"""
OBV (On-Balance Volume) Indicator

Syntax: obv

Returns: Series with OBV values
"""

import pandas as pd
from typing import Optional


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
    if "CLOSE" in data.columns:
        close = data["CLOSE"]
    elif "Close" in data.columns:
        close = data["Close"]
    else:
        close = data.iloc[:, -2]  # Assume second to last is close

    if "VOLUME" in data.columns:
        volume = data["VOLUME"]
    elif "Volume" in data.columns:
        volume = data["Volume"]
    else:
        volume = data.iloc[:, -1]  # Assume last is volume

    # Use history if provided
    if history_df is not None:
        if "CLOSE" in history_df.columns:
            hist_close = history_df["CLOSE"]
        else:
            hist_close = history_df.iloc[:, -2]
        if "VOLUME" in history_df.columns:
            hist_volume = history_df["VOLUME"]
        else:
            hist_volume = history_df.iloc[:, -1]

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
