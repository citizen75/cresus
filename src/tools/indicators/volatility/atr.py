"""
ATR (Average True Range) Indicator

Syntax: atr_<period>
Example: atr_14

Returns: Series with ATR values

Uses pandas-ta library for canonical implementation.
"""

import pandas as pd
import pandas_ta
from typing import Optional
from ..utils.helpers import get_high, get_low, get_close


def calculate(
    data: pd.DataFrame,
    period: int = 14,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate ATR (Average True Range) using pandas-ta.

    Args:
        data: OHLCV DataFrame with HIGH, LOW, CLOSE columns
        period: ATR period (default: 14)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with ATR values
    """
    # Get OHLC
    high = get_high(data)
    low = get_low(data)
    close = get_close(data)

    # Use history if provided
    if history_df is not None:
        hist_high = get_high(history_df)
        hist_low = get_low(history_df)
        hist_close = get_close(history_df)

        high = pd.concat([hist_high, high], ignore_index=True)
        low = pd.concat([hist_low, low], ignore_index=True)
        close = pd.concat([hist_close, close], ignore_index=True)

    # Calculate ATR using pandas-ta
    atr = pandas_ta.atr(high, low, close, length=period)

    # Extract only current period
    result_len = len(data)
    atr = atr.iloc[-result_len:].reset_index(drop=True)

    return atr.fillna(0.0)
