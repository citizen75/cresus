"""
Change Percent Indicator

Syntax: change_pct_<period>
Example: change_pct_1

Returns: Series with percentage change
"""

import pandas as pd
from typing import Optional


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

    # Calculate percentage change
    change_pct = ((combined - combined.shift(period)) / combined.shift(period) * 100)

    # Extract current period
    result_len = len(data)
    change_pct = change_pct.iloc[-result_len:].reset_index(drop=True)

    return change_pct.fillna(0.0)
