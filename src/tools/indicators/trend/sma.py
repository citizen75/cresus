"""
SMA (Simple Moving Average) Indicator

Syntax: sma_<period>
Example: sma_50

Returns: Series with SMA values
"""

import pandas as pd
from typing import Optional
from ..utils.helpers import get_close


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
    close = get_close(data)

    # Use history if provided
    if history_df is not None:
        hist_close = get_close(history_df)
        combined = pd.concat([hist_close, close], ignore_index=True)
    else:
        combined = close

    # Calculate SMA
    sma = combined.rolling(window=period, min_periods=1).mean()

    # Extract only current period
    result_len = len(data)
    sma = sma.iloc[-result_len:].reset_index(drop=True)

    return sma.fillna(close.mean())
