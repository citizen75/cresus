"""
CMF (Chaikin Money Flow) Indicator

Syntax: cmf_<period>
Example: cmf_20

Returns: Series with CMF values
"""

import pandas as pd
from typing import Optional
from ..utils.helpers import get_high, get_low, get_close, get_volume


def calculate(
    data: pd.DataFrame,
    period: int = 20,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate CMF (Chaikin Money Flow).

    Args:
        data: OHLCV DataFrame with HIGH, LOW, CLOSE, VOLUME columns
        period: CMF period (default: 20)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with CMF values

    Formula:
        Money Flow Multiplier = ((Close - Low) - (High - Close)) / (High - Low)
        Money Flow Volume = Money Flow Multiplier * Volume
        CMF = Sum of Money Flow Volume over period / Sum of Volume over period
    """
    # Get HLCV
    try:
        high = get_high(data)
        low = get_low(data)
        close = get_close(data)
        volume = get_volume(data)
    except Exception:
        return pd.Series([0.0] * len(data))

    # Use history if provided
    if history_df is not None:
        try:
            hist_high = get_high(history_df)
            hist_low = get_low(history_df)
            hist_close = get_close(history_df)
            hist_volume = get_volume(history_df)

            high = pd.concat([hist_high, high], ignore_index=True)
            low = pd.concat([hist_low, low], ignore_index=True)
            close = pd.concat([hist_close, close], ignore_index=True)
            volume = pd.concat([hist_volume, volume], ignore_index=True)
        except Exception:
            pass

    # Calculate Money Flow Multiplier
    hl_range = high - low
    hl_range = hl_range.replace(0, 1)  # Avoid division by zero

    mfm = ((close - low) - (high - close)) / hl_range

    # Money Flow Volume
    mfv = mfm * volume

    # CMF
    mfv_sum = mfv.rolling(window=period, min_periods=1).sum()
    vol_sum = volume.rolling(window=period, min_periods=1).sum()

    cmf = mfv_sum / vol_sum.replace(0, 1)

    # Extract only current period
    result_len = len(data)
    cmf = cmf.iloc[-result_len:].reset_index(drop=True)

    return cmf.fillna(0.0)
