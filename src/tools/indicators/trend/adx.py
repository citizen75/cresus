"""
ADX (Average Directional Index) Indicator

Syntax: adx_<period>
Example: adx_14

Returns: Series with ADX values (0-100)

Uses pandas-ta library for canonical implementation.
"""

import pandas as pd
import pandas_ta_classic as pandas_ta
from typing import Optional
from ..utils.helpers import get_high, get_low, get_close


def calculate(
    data: pd.DataFrame,
    period: int = 14,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate ADX (Average Directional Index) using pandas-ta.

    Args:
        data: OHLCV DataFrame with HIGH, LOW, CLOSE columns
        period: ADX period (default: 14)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with ADX values (0-100, trend strength)
    """
    # Get OHLC
    try:
        high = get_high(data)
        low = get_low(data)
        close = get_close(data)
    except Exception:
        # Return neutral ADX if can't calculate
        return pd.Series([25.0] * len(data))

    # Use history if provided
    if history_df is not None:
        try:
            hist_high = get_high(history_df)
            hist_low = get_low(history_df)
            hist_close = get_close(history_df)

            high = pd.concat([hist_high, high], ignore_index=True)
            low = pd.concat([hist_low, low], ignore_index=True)
            close = pd.concat([hist_close, close], ignore_index=True)
        except Exception:
            pass

    # Calculate ADX using pandas-ta
    adx_df = pandas_ta.adx(high, low, close, length=period)

    # pandas-ta returns DataFrame with ADX_<period>, DMP_<period>, DMN_<period>
    adx_col = f"ADX_{period}"
    adx = adx_df[adx_col]

    # Extract only current period
    result_len = len(data)
    adx = adx.iloc[-result_len:].reset_index(drop=True)

    return adx.fillna(25.0)
