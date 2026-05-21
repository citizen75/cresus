"""
EMA (Exponential Moving Average) Indicator

Syntax: ema_<period>
Example: ema_20

Returns: Series with EMA values
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
    Calculate EMA (Exponential Moving Average).

    Args:
        data: OHLCV DataFrame
        period: EMA period (default: 20)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with EMA values

    Formula:
        EMA = Price * (2 / (period + 1)) + EMA[previous] * (1 - (2 / (period + 1)))
    """
    # Get close prices
    close = get_close(data)

    # Use history if provided
    if history_df is not None:
        hist_close = get_close(history_df)
        combined = pd.concat([hist_close, close], ignore_index=True)
    else:
        combined = close

    # Calculate EMA
    ema = combined.ewm(span=period, adjust=False).mean()

    # Extract only current period
    result_len = len(data)
    ema = ema.iloc[-result_len:].reset_index(drop=True)

    return ema.fillna(close.mean())
