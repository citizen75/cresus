"""
EMA (Exponential Moving Average) Indicator

Syntax: ema_<period>
Example: ema_20

Returns: Series with EMA values

Uses pandas-ta library for canonical implementation.
"""

import pandas as pd
import pandas_ta
from typing import Optional
from ..utils.helpers import get_close


def calculate(
    data: pd.DataFrame,
    period: int = 20,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate EMA (Exponential Moving Average) using pandas-ta.

    Args:
        data: OHLCV DataFrame
        period: EMA period (default: 20)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with EMA values
    """
    # Get close prices
    close = get_close(data)

    # Use history if provided
    if history_df is not None:
        hist_close = get_close(history_df)
        combined = pd.concat([hist_close, close], ignore_index=True)
    else:
        combined = close

    # Calculate EMA using pandas-ta
    ema = pandas_ta.ema(combined, length=period)

    # Extract only current period
    result_len = len(data)
    ema = ema.iloc[-result_len:].reset_index(drop=True)

    return ema.fillna(close.mean())
