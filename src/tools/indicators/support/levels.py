"""
Support/Resistance Levels Indicator

Syntax: support_<period> or resistance_<period>
Example: support_14

Returns: Series with support/resistance levels
"""

import pandas as pd
from typing import Optional


def calculate(
    data: pd.DataFrame,
    period: int = 14,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate Support/Resistance Levels.

    Args:
        data: OHLCV DataFrame with HIGH, LOW columns
        period: Lookback period (default: 14)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with support/resistance levels

    Formula:
        Support/Resistance = (High + Low) / 2 from lookback period
    """
    # Get HIGH and LOW
    high = data.get("HIGH", data.get("High", None))
    low = data.get("LOW", data.get("Low", None))

    if high is None or low is None:
        return pd.Series([0.0] * len(data))

    # Use history if provided
    if history_df is not None:
        hist_high = history_df.get("HIGH", history_df.get("High", None))
        hist_low = history_df.get("LOW", history_df.get("Low", None))

        if hist_high is not None:
            high = pd.concat([hist_high, high], ignore_index=True)
        if hist_low is not None:
            low = pd.concat([hist_low, low], ignore_index=True)

    # Calculate pivot levels (average of high and low)
    hl_avg = (high + low) / 2

    # Use rolling max as support/resistance
    levels = hl_avg.rolling(window=period, min_periods=1).mean()

    # Extract only current period
    result_len = len(data)
    levels = levels.iloc[-result_len:].reset_index(drop=True)

    return levels.fillna(0.0)
