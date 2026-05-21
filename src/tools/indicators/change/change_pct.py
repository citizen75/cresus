"""
Change Percent Indicator

Syntax: change_pct_<period>
Example: change_pct_1

Returns: Series with percentage change
"""

import pandas as pd
from typing import Optional
from ..utils.helpers import get_close


def calculate(
    data: pd.DataFrame,
    period: int = 1,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate percentage change over period.

    Args:
        data: OHLCV DataFrame
        period: Lookback period (default: 1)
        history_df: Optional historical data

    Returns:
        Series with percentage change values

    Formula:
        Change% = ((Close - Close[n periods ago]) / Close[n periods ago]) * 100
    """
    # Get close
    close = get_close(data)

    # Use history if provided
    if history_df is not None:
        hist_close = get_close(history_df)
        combined = pd.concat([hist_close, close], ignore_index=True)
    else:
        combined = close

    # Calculate percentage change
    change_pct = ((combined - combined.shift(period)) / combined.shift(period) * 100)

    # Extract current period
    result_len = len(data)
    change_pct = change_pct.iloc[-result_len:].reset_index(drop=True)

    return change_pct.fillna(0.0)
