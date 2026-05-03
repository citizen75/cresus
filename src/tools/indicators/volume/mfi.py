"""
MFI (Money Flow Index) Indicator

Syntax: mfi_<period>
Example: mfi_14

Returns: Series with MFI values (0-100)
"""

import pandas as pd
import numpy as np
from typing import Optional


def calculate(
    data: pd.DataFrame,
    period: int = 14,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate MFI (Money Flow Index).

    Args:
        data: OHLCV DataFrame with HIGH, LOW, CLOSE, VOLUME columns
        period: MFI period (default: 14)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with MFI values (0-100)

    Formula:
        TP (Typical Price) = (High + Low + Close) / 3
        Money Flow = TP * Volume
        Positive Money Flow = sum of Money Flow when TP > TP[previous]
        Negative Money Flow = sum of Money Flow when TP < TP[previous]
        Money Flow Ratio = Positive Money Flow / Negative Money Flow
        MFI = 100 - (100 / (1 + Money Flow Ratio))
    """
    # Get HLCV
    high = data.get("HIGH", data.get("High", None))
    low = data.get("LOW", data.get("Low", None))
    close = data.get("CLOSE", data.get("Close", None))
    volume = data.get("VOLUME", data.get("Volume", None))

    if any(x is None for x in [high, low, close, volume]):
        return pd.Series([50.0] * len(data))

    # Use history if provided
    if history_df is not None:
        hist_high = history_df.get("HIGH", history_df.get("High", None))
        hist_low = history_df.get("LOW", history_df.get("Low", None))
        hist_close = history_df.get("CLOSE", history_df.get("Close", None))
        hist_volume = history_df.get("VOLUME", history_df.get("Volume", None))

        if all(x is not None for x in [hist_high, hist_low, hist_close, hist_volume]):
            high = pd.concat([hist_high, high], ignore_index=True)
            low = pd.concat([hist_low, low], ignore_index=True)
            close = pd.concat([hist_close, close], ignore_index=True)
            volume = pd.concat([hist_volume, volume], ignore_index=True)

    # Calculate Typical Price
    tp = (high + low + close) / 3

    # Calculate Money Flow
    mf = tp * volume

    # Determine direction
    tp_diff = tp.diff()
    pos_mf = mf.where(tp_diff > 0, 0)
    neg_mf = mf.where(tp_diff < 0, 0)

    # Sum over period
    pos_mf_sum = pos_mf.rolling(window=period, min_periods=1).sum()
    neg_mf_sum = neg_mf.rolling(window=period, min_periods=1).sum()

    # Calculate MFI
    mf_ratio = pos_mf_sum / neg_mf_sum.replace(0, np.nan)
    mfi = 100 - (100 / (1 + mf_ratio))
    mfi = mfi.fillna(50)  # Fill NaN with 50 (neutral)

    # Extract only current period
    result_len = len(data)
    mfi = mfi.iloc[-result_len:].reset_index(drop=True)

    return mfi
