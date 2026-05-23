"""
RSI (Relative Strength Index) Indicator

Syntax: rsi_<period>
Example: rsi_14

Returns: Series with RSI values (0-100)

Uses pandas-ta library for canonical implementation.
"""

import pandas as pd
import pandas_ta_classic as pandas_ta
from typing import Optional
from ..utils.helpers import get_close, validate_rsi_output


def calculate(
    data: pd.DataFrame,
    period: int = 14,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate RSI (Relative Strength Index) using pandas-ta.

    Args:
        data: OHLCV DataFrame
        period: RSI period (default: 14)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with RSI values (0-100)
    """
    # Get close prices
    close = get_close(data)

    # Use history if provided
    if history_df is not None:
        hist_close = get_close(history_df)
        combined = pd.concat([hist_close, close], ignore_index=True)
    else:
        combined = close

    # Calculate RSI using pandas-ta
    rsi = pandas_ta.rsi(combined, length=period)

    # Extract only current period
    result_len = len(data)
    rsi = rsi.iloc[-result_len:].reset_index(drop=True)

    # Fill NaN with 50 (neutral)
    rsi = rsi.fillna(50)
    validate_rsi_output(rsi)

    return rsi
