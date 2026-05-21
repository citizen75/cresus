"""
Support/Resistance Levels Indicator

Syntax: support_<period> or resistance_<period>
Example: support_14

Returns: Series with support/resistance levels
"""

import pandas as pd
from typing import Optional
from ..utils.helpers import get_high, get_low


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
    try:
        high = get_high(data)
        low = get_low(data)
    except Exception:
        return pd.Series([0.0] * len(data))

    # Use history if provided
    if history_df is not None:
        try:
            hist_high = get_high(history_df)
            hist_low = get_low(history_df)

            high = pd.concat([hist_high, high], ignore_index=True)
            low = pd.concat([hist_low, low], ignore_index=True)
        except Exception:
            pass

    # Calculate pivot levels (average of high and low)
    hl_avg = (high + low) / 2

    # Use rolling max as support/resistance
    levels = hl_avg.rolling(window=period, min_periods=1).mean()

    # Extract only current period
    result_len = len(data)
    levels = levels.iloc[-result_len:].reset_index(drop=True)

    return levels.fillna(0.0)
