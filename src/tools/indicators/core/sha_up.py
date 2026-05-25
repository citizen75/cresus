"""
Smooth Heikin Ashi Up (Bullish without Bottom Wick) Indicator

Syntax: sha_<period>_up
Example: sha_14_up

Returns: Binary Series (1 = bullish candle with no bottom wick, 0 otherwise)

A bullish candle without a bottom wick indicates strong upward momentum with no
rejection from below - the low equals the open price.
"""

import pandas as pd
from typing import Optional
from . import heikin_ashi


def calculate(
    data: pd.DataFrame,
    period: int = 14,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate Smooth Heikin Ashi up (bullish without bottom wick) indicator.

    Args:
        data: OHLCV DataFrame
        period: EMA period for SHA smoothing (default: 14)
        history_df: Optional historical data for extended lookback

    Returns:
        Binary Series (1 = bullish candle with no bottom wick, 0 otherwise)

    Formula:
        SHA_Up = 1 if (SHA_Close > SHA_Open) AND (SHA_Low == SHA_Open) else 0
    """
    result = heikin_ashi.calculate_smooth(
        data,
        period=period,
        history_df=history_df,
        **kwargs
    )

    # Extract OHLC components
    open_key = f"sha_{period}_open"
    close_key = f"sha_{period}_close"
    low_key = f"sha_{period}_low"

    sha_open = result[open_key]
    sha_close = result[close_key]
    sha_low = result[low_key]

    # Bullish candle with no bottom wick: close > open and low == open
    is_up = (sha_close > sha_open) & (sha_low == sha_open)

    return pd.Series(is_up.astype(int), index=sha_close.index)
