"""
ADX (Average Directional Index) Indicator

Syntax: adx_<period> or adx_<period>_force
Example: adx_14 or adx_14_force

Returns:
  - adx_14: Series with ADX values (0-100)
  - adx_14_force: Series with force values (-1, 0, 1)
    -1: Weak trend (adx < 20)
     0: Neutral (20 <= adx <= 25)
     1: Strong trend (adx > 25)

Uses pandas-ta library for canonical implementation.
"""

import pandas as pd
import numpy as np
import pandas_ta_classic as pandas_ta
from typing import Optional, Union, Dict
from ..utils.helpers import get_high, get_low, get_close


def calculate(
    data: pd.DataFrame,
    period: int = 14,
    history_df: Optional[pd.DataFrame] = None,
    __component__: Optional[str] = None,
    **kwargs
) -> Union[pd.Series, Dict[str, pd.Series]]:
    """
    Calculate ADX (Average Directional Index) using pandas-ta.

    Args:
        data: OHLCV DataFrame with HIGH, LOW, CLOSE columns
        period: ADX period (default: 14)
        history_df: Optional historical data for extended lookback
        __component__: Component to return ('force' for trend conviction, None for main ADX)

    Returns:
        Series with ADX values (0-100) or Dict with 'adx' and 'force' keys
        - adx: ADX trend strength (0-100)
        - force: Trend conviction (-1, 0, 1)
    """
    # Get OHLC
    try:
        high = get_high(data)
        low = get_low(data)
        close = get_close(data)
    except Exception:
        # Return neutral ADX if can't calculate
        default_adx = pd.Series([25.0] * len(data))
        if __component__ == 'force':
            return pd.Series([0] * len(data))
        return default_adx

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
    adx = adx.fillna(25.0)

    # Calculate force component (trend conviction)
    force = np.where(
        adx < 20,
        -1,  # Weak trend - low conviction
        np.where(
            adx > 25,
            1,  # Strong trend - high conviction
            0   # Neutral - moderate conviction
        )
    )
    force = pd.Series(force, index=adx.index)

    # Return requested component or both
    if __component__ == 'force':
        return force

    # Return as dict if both components might be needed
    return {'adx': adx, 'force': force}
