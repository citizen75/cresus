"""
RSI (Relative Strength Index) Indicator

Syntax: rsi_<period>
Example: rsi_14

Returns: Series with RSI values (0-100)
"""

import pandas as pd
import numpy as np
from typing import Optional


def calculate(
    data: pd.DataFrame,
    period: int = 14,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate RSI (Relative Strength Index).

    Args:
        data: OHLCV DataFrame
        period: RSI period (default: 14)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with RSI values (0-100)

    Formula:
        RS = Average Gain / Average Loss
        RSI = 100 - (100 / (1 + RS))
    """
    # Get close prices
    if "CLOSE" in data.columns:
        close = data["CLOSE"]
    elif "Close" in data.columns:
        close = data["Close"]
    else:
        close = data.iloc[:, -1]  # Assume last column is close

    # Calculate price changes
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    # Calculate average gain/loss (exponential moving average)
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()

    # Avoid division by zero
    rs = avg_gain / avg_loss.replace(0, np.nan)

    # Calculate RSI
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50)  # Fill NaN with 50 (neutral)

    return rsi.reset_index(drop=True)
