"""
Smooth Heikin Ashi Red (Bearish) Indicator

Syntax: sha_<period>_red
Example: sha_14_red

Returns: Binary Series (1 = bearish/red candle, 0 = bullish/green candle)
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
    Calculate Smooth Heikin Ashi red (bearish) indicator.

    Args:
        data: OHLCV DataFrame
        period: EMA period for SHA smoothing (default: 14)
        history_df: Optional historical data for extended lookback

    Returns:
        Binary Series (1 = bearish candle, 0 = bullish)

    Formula:
        SHA_Red = 1 if SHA_Close < SHA_Open else 0
    """
    result = heikin_ashi.calculate_smooth(
        data,
        period=period,
        history_df=history_df,
        **kwargs
    )
    key = f"sha_{period}_red"
    return result[key]
