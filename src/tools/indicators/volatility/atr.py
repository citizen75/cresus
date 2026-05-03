"""
ATR (Average True Range) Indicator

Syntax: atr_<period>
Example: atr_14

Returns: Series with ATR values
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
    Calculate ATR (Average True Range).

    Args:
        data: OHLCV DataFrame with HIGH, LOW, CLOSE columns
        period: ATR period (default: 14)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with ATR values

    Formula:
        TR = max(High - Low, abs(High - Close[prev]), abs(Low - Close[prev]))
        ATR = EMA of TR
    """
    # Get OHLC
    high = data.get("HIGH", data.get("High", None))
    low = data.get("LOW", data.get("Low", None))
    close = data.get("CLOSE", data.get("Close", None))

    if high is None or low is None or close is None:
        return pd.Series([0.0] * len(data))

    # Use history if provided
    if history_df is not None:
        hist_high = history_df.get("HIGH", history_df.get("High", None))
        hist_low = history_df.get("LOW", history_df.get("Low", None))
        hist_close = history_df.get("CLOSE", history_df.get("Close", None))

        if hist_high is not None:
            high = pd.concat([hist_high, high], ignore_index=True)
        if hist_low is not None:
            low = pd.concat([hist_low, low], ignore_index=True)
        if hist_close is not None:
            close = pd.concat([hist_close, close], ignore_index=True)

    # Calculate True Range
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Calculate ATR (EMA of TR)
    atr = tr.ewm(span=period, adjust=False).mean()

    # Extract only current period
    result_len = len(data)
    atr = atr.iloc[-result_len:].reset_index(drop=True)

    return atr.fillna(0.0)
