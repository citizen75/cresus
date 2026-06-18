"""
EMA Percentage Change Indicator

Syntax: ema_<ema_period>_chgpct_<change_period>
Example: ema_20_chgpct_5

Returns: Series with percentage change of EMA over lookback period

Calculates the percentage change of an EMA over a specified number of days.
Formula:
    1. Calculate EMA with ema_period
    2. Calculate change% of EMA over change_period days
    Change% = ((EMA - EMA[change_period days ago]) / EMA[change_period days ago]) * 100
"""

import pandas as pd
import pandas_ta_classic as pandas_ta
from typing import Optional
from ..utils.helpers import get_close


def calculate(
    data: pd.DataFrame,
    ema_period: int = 20,
    change_period: int = 5,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate percentage change of EMA.

    Args:
        data: OHLCV DataFrame
        ema_period: EMA period (default: 20)
        change_period: Lookback period for percentage change (default: 5)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with percentage change of EMA values
    """
    # Get close prices
    close = get_close(data)

    # Use history if provided
    if history_df is not None:
        hist_close = get_close(history_df)
        combined = pd.concat([hist_close, close], ignore_index=True)
    else:
        combined = close

    # Calculate EMA using pandas-ta
    ema = pandas_ta.ema(combined, length=ema_period)

    # Calculate percentage change of EMA over change_period
    ema_chgpct = ((ema - ema.shift(change_period)) / ema.shift(change_period) * 100)

    # Extract only current period
    result_len = len(data)
    ema_chgpct = ema_chgpct.iloc[-result_len:].reset_index(drop=True)

    return ema_chgpct.fillna(0.0)
