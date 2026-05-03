"""
ROC (Rate of Change) / Momentum Indicator

Syntax: roc_<period>
Example: roc_12

Returns: Series with ROC values (percentage change)
"""

import pandas as pd
from typing import Optional


def calculate(
    data: pd.DataFrame,
    period: int = 12,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate ROC (Rate of Change) / Momentum.

    Args:
        data: OHLCV DataFrame
        period: ROC period (default: 12)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with ROC values (percentage change)

    Formula:
        ROC = ((Close - Close[n periods ago]) / Close[n periods ago]) * 100
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

    # Calculate ROC
    roc = ((combined - combined.shift(period)) / combined.shift(period) * 100)

    # Extract only current period
    result_len = len(data)
    roc = roc.iloc[-result_len:].reset_index(drop=True)

    return roc.fillna(0.0)
