"""
Smooth Heikin Ashi Down (Bearish without Top Wick) Indicator

Syntax: sha_<period>_down
Example: sha_14_down

Returns: Binary Series (1 = bearish candle with no top wick, 0 otherwise)

A bearish candle without a top wick indicates strong downward momentum with no
rejection from above - the high stays below or at the open price.
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
    Calculate Smooth Heikin Ashi down (bearish without top wick) indicator.

    Args:
        data: OHLCV DataFrame
        period: EMA period for SHA smoothing (default: 14)
        history_df: Optional historical data for extended lookback

    Returns:
        Binary Series (1 = bearish candle with no top wick, 0 otherwise)

    Formula:
        SHA_Down = 1 if (SHA_Close < SHA_Open) AND (SHA_High <= SHA_Open) else 0
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
    high_key = f"sha_{period}_high"

    sha_open = result[open_key]
    sha_close = result[close_key]
    sha_high = result[high_key]

    # Bearish candle with no top wick
    # (Close < Open) AND (High <= Open)
    is_down = (sha_close < sha_open) & (sha_high <= sha_open)

    return pd.Series(is_down.astype(int), index=sha_close.index)
