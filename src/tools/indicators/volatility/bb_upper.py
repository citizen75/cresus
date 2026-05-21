"""
Bollinger Bands Upper Band Indicator

Syntax: bb_<period>_upper or bollinger_bands_<period>_upper
Example: bb_20_upper (uses default std_dev=2)

Returns: Series with upper band values
"""

import pandas as pd
from typing import Optional
from . import bb as bb_module


def calculate(
    data: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate Bollinger Band upper band.

    Args:
        data: OHLCV DataFrame
        period: SMA period (default: 20)
        std_dev: Standard deviation multiplier (default: 2)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with upper band values

    Formula:
        Upper Band = SMA + (std_dev * StdDev)
    """
    result = bb_module.calculate(
        data,
        period=period,
        std_dev=std_dev,
        history_df=history_df,
        **kwargs
    )
    return result["bb_upper"]
