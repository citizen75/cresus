"""
ROC (Rate of Change) / Momentum Indicator

Syntax: roc_<period>
Example: roc_12

Returns: Series with ROC values (percentage change)

Uses pandas-ta library for canonical implementation.
"""

import pandas as pd
import pandas_ta
from typing import Optional
from ..utils.helpers import get_close


def calculate(
    data: pd.DataFrame,
    period: int = 12,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate ROC (Rate of Change) / Momentum using pandas-ta.

    Args:
        data: OHLCV DataFrame
        period: ROC period (default: 12)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with ROC values (percentage change)
    """
    # Get close prices
    close = get_close(data)

    # Use history if provided
    if history_df is not None:
        hist_close = get_close(history_df)
        combined = pd.concat([hist_close, close], ignore_index=True)
    else:
        combined = close

    # Calculate ROC using pandas-ta
    roc = pandas_ta.roc(combined, length=period)

    # Extract only current period
    result_len = len(data)
    roc = roc.iloc[-result_len:].reset_index(drop=True)

    return roc.fillna(0.0)
