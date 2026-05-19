"""
Return Indicator - Multi-period returns

Syntax: return_<period>
Examples: return_1d, return_5d, return_20d, return_60d, return_120d, return_250d

Returns: Series with percentage returns (as %)
"""

import pandas as pd
from typing import Optional


def calculate(
    data: pd.DataFrame,
    period: int = 5,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate percentage return over period.

    Args:
        data: OHLCV DataFrame
        period: Lookback period in days (default: 5)
        history_df: Optional historical data for lookback

    Returns:
        Series with percentage return values

    Formula:
        Return% = ((Close[0] - Close[period]) / Close[period]) * 100
    """
    # Get close price
    if "CLOSE" in data.columns:
        close = data["CLOSE"]
    elif "Close" in data.columns:
        close = data["Close"]
    else:
        close = data.iloc[:, -1]

    # Use history if provided for lookback
    if history_df is not None:
        if "CLOSE" in history_df.columns:
            hist_close = history_df["CLOSE"]
        else:
            hist_close = history_df.iloc[:, -1]
        combined = pd.concat([hist_close, close], ignore_index=True)
    else:
        combined = close

    # Calculate returns: (Close[0] - Close[period]) / Close[period] * 100
    returns = ((combined - combined.shift(period)) / combined.shift(period) * 100)

    # Extract current period
    result_len = len(data)
    returns = returns.iloc[-result_len:].reset_index(drop=True)

    return returns.fillna(0.0)
