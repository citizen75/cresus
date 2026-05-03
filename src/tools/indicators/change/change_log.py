"""
Change Log Indicator

Syntax: change_log_<period>
Example: change_log_1

Returns: Series with log change values
"""

import pandas as pd
import numpy as np
from typing import Optional


def calculate(
    data: pd.DataFrame,
    period: int = 1,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate log change over period.

    Args:
        data: OHLCV DataFrame
        period: Lookback period (default: 1)
        history_df: Optional historical data

    Returns:
        Series with log change values

    Formula:
        Log Change = log(Close / Close[n periods ago])
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

    # Calculate log change
    log_change = np.log(combined / combined.shift(period))

    # Extract current period
    result_len = len(data)
    log_change = log_change.iloc[-result_len:].reset_index(drop=True)

    return log_change.fillna(0.0)
