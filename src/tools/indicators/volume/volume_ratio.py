"""
Volume Ratio Indicator

Syntax: volume_ratio_<period>
Example: volume_ratio_20

Returns: Series with volume ratio values
"""

import pandas as pd
from typing import Optional


def calculate(
    data: pd.DataFrame,
    period: int = 20,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate Volume Ratio (Current Volume / Average Volume).

    Args:
        data: OHLCV DataFrame
        period: Lookback period for average (default: 20)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with volume ratio values (ratio > 1 = above average)

    Formula:
        Volume Ratio = Current Volume / SMA(Volume, period)
    """
    # Get volume
    if "VOLUME" in data.columns:
        volume = data["VOLUME"]
    elif "Volume" in data.columns:
        volume = data["Volume"]
    else:
        volume = data.iloc[:, -1]

    # Use history if provided
    if history_df is not None:
        if "VOLUME" in history_df.columns:
            hist_volume = history_df["VOLUME"]
        else:
            hist_volume = history_df.iloc[:, -1]
        combined = pd.concat([hist_volume, volume], ignore_index=True)
    else:
        combined = volume

    # Calculate volume SMA
    vol_sma = combined.rolling(window=period, min_periods=1).mean()

    # Volume ratio
    vol_ratio = combined / vol_sma.replace(0, 1)

    # Extract only current period
    result_len = len(data)
    vol_ratio = vol_ratio.iloc[-result_len:].reset_index(drop=True)

    return vol_ratio.fillna(1.0)
