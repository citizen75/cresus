"""
Smooth Heikin Ashi Green (Bullish) Indicator

Syntax: sha_<period>_green
Example: sha_14_green

Returns: Binary Series (1 = bullish/green candle, 0 = bearish/red candle)
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
    Calculate Smooth Heikin Ashi green (bullish) indicator.

    Args:
        data: OHLCV DataFrame
        period: EMA period for SHA smoothing (default: 14)
        history_df: Optional historical data for extended lookback

    Returns:
        Binary Series (1 = bullish candle, 0 = bearish)

    Formula:
        SHA_Green = 1 if SHA_Close > SHA_Open else 0
    """
    result = heikin_ashi.calculate_smooth(
        data,
        period=period,
        history_df=history_df,
        **kwargs
    )
    key = f"sha_{period}_green"
    return result[key]
