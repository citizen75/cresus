"""
ADX Force (Trend Conviction) Indicator

Syntax: adx_<period>_force
Example: adx_14_force

Returns: Series with force values (-1, 0, 1)
  -1: Weak trend (adx < 20) - low conviction
   0: Neutral (20 <= adx <= 25) - moderate conviction
   1: Strong trend (adx > 25) - high conviction

Uses ADX to measure trend strength and confidence level.
Useful for risk filtering and position sizing.
"""

import pandas as pd
import numpy as np
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
    Calculate ADX Force (trend conviction level).

    Args:
        data: OHLCV DataFrame with HIGH, LOW, CLOSE columns
        period: ADX period (default: 14)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with force values (-1, 0, 1)
        -1: weak trend, 0: neutral, 1: strong trend
    """
    # Get OHLC
    try:
        high = get_high(data)
        low = get_low(data)
        close = get_close(data)
    except Exception:
        # Return neutral if can't calculate
        return pd.Series([0] * len(data))

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

    # Extract ADX values
    adx_col = f"ADX_{period}"
    adx = adx_df[adx_col]

    # Extract only current period
    result_len = len(data)
    adx = adx.iloc[-result_len:].reset_index(drop=True)
    adx = adx.fillna(25.0)

    # Calculate force: -1 (weak), 0 (neutral), 1 (strong)
    force = np.where(
        adx < 20,
        -1,  # Weak trend - low conviction
        np.where(
            adx > 25,
            1,  # Strong trend - high conviction
            0   # Neutral - moderate conviction
        )
    )

    return pd.Series(force, index=adx.index)
