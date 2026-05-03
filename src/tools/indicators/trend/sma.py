"""
SMA (Simple Moving Average) Indicator

Syntax: sma_<period>
Example: sma_50

Returns: Series with SMA values
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
    Calculate SMA (Simple Moving Average).

    Args:
        data: OHLCV DataFrame
        period: SMA period (default: 20)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with SMA values

    Formula:
        SMA = Sum of prices over period / period
    """
    # Get close prices
    if "CLOSE" in data.columns:
        close = data["CLOSE"]
    elif "Close" in data.columns:
        close = data["Close"]
    else:
        close = data.iloc[:, -1]

    # Use history if provided
    if history_df is not None:
        if "CLOSE" in history_df.columns:
            hist_close = history_df["CLOSE"]
        else:
            hist_close = history_df.iloc[:, -1]
        combined = pd.concat([hist_close, close], ignore_index=True)
    else:
        combined = close

    # Calculate SMA
    sma = combined.rolling(window=period, min_periods=1).mean()

    # Extract only current period
    result_len = len(data)
    sma = sma.iloc[-result_len:].reset_index(drop=True)

    return sma.fillna(close.mean())
