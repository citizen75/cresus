"""
Smooth Heikin Ashi Down (Bearish without Top Wick) Indicator

Syntax: sha_<period>_down
Example: sha_14_down

Returns: Binary Series (1 = bearish candle with no top wick, 0 otherwise)

A bearish candle without a top wick indicates strong downward momentum with no
rejection from above - the high should not be significantly above the open price.

WICK_TOLERANCE = 0.005 (0.5% of price) is used to detect "no top wick" condition.
"""

import pandas as pd
from typing import Optional
from . import heikin_ashi

# Wick tolerance: 0.5% of price to account for numerical precision
WICK_TOLERANCE = 0.005


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
        SHA_Down = 1 if (SHA_Close < SHA_Open) AND
                        (SHA_High - SHA_Open) / SHA_Open < WICK_TOLERANCE
                  else 0

    The second condition detects when there is no top wick by checking if
    the high is within WICK_TOLERANCE (0.5%) of the open price.
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

    # Bearish candle: close < open
    is_bearish = sha_close < sha_open

    # No top wick: high is within WICK_TOLERANCE of open
    # Calculate wick size as percentage of open price
    wick_size = (sha_high - sha_open) / sha_open.abs()
    no_top_wick = wick_size < WICK_TOLERANCE

    # Both conditions must be true
    is_down = is_bearish & no_top_wick

    return pd.Series(is_down.astype(int), index=sha_close.index)
