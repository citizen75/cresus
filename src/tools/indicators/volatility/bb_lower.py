"""
Bollinger Bands Lower Band Indicator

Syntax: bb_<period>_lower or bollinger_bands_<period>_lower
Example: bb_20_lower (uses default std_dev=2)

Returns: Series with lower band values
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
    Calculate Bollinger Band lower band.

    Args:
        data: OHLCV DataFrame
        period: SMA period (default: 20)
        std_dev: Standard deviation multiplier (default: 2)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with lower band values

    Formula:
        Lower Band = SMA - (std_dev * StdDev)
    """
    result = bb_module.calculate(
        data,
        period=period,
        std_dev=std_dev,
        history_df=history_df,
        **kwargs
    )
    return result["bb_lower"]
