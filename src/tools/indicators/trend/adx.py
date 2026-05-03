"""
ADX (Average Directional Index) Indicator

Syntax: adx_<period>
Example: adx_14

Returns: Series with ADX values (0-100)
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
    Calculate ADX (Average Directional Index).

    Args:
        data: OHLCV DataFrame with HIGH, LOW, CLOSE columns
        period: ADX period (default: 14)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with ADX values (0-100, trend strength)

    Formula:
        +DM = High - High[previous] (if positive and > -DM)
        -DM = Low[previous] - Low (if positive and > +DM)
        TR = max(High - Low, abs(High - Close[prev]), abs(Low - Close[prev]))
        +DI = 100 * (+DM / TR) smoothed
        -DI = 100 * (-DM / TR) smoothed
        DX = 100 * |+DI - -DI| / (+DI + -DI)
        ADX = EMA of DX
    """
    # Get OHLC
    high = data.get("HIGH", data.get("High", None))
    low = data.get("LOW", data.get("Low", None))
    close = data.get("CLOSE", data.get("Close", None))

    if high is None or low is None or close is None:
        # Return neutral ADX if can't calculate
        return pd.Series([25.0] * len(data))

    # Use history if provided
    if history_df is not None:
        hist_high = history_df.get("HIGH", history_df.get("High", None))
        hist_low = history_df.get("LOW", history_df.get("Low", None))
        hist_close = history_df.get("CLOSE", history_df.get("Close", None))

        if hist_high is not None:
            high = pd.concat([hist_high, high], ignore_index=True)
        if hist_low is not None:
            low = pd.concat([hist_low, low], ignore_index=True)
        if hist_close is not None:
            close = pd.concat([hist_close, close], ignore_index=True)

    # Calculate True Range
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Calculate Directional Movements
    up = high - high.shift(1)
    down = low.shift(1) - low

    # Determine positive and negative directional movements
    plus_dm = np.where((up > down) & (up > 0), up, 0)
    minus_dm = np.where((down > up) & (down > 0), down, 0)

    # Calculate Directional Indicators
    tr_smooth = tr.rolling(window=period, min_periods=1).sum()
    plus_dm_smooth = pd.Series(plus_dm).rolling(window=period, min_periods=1).sum()
    minus_dm_smooth = pd.Series(minus_dm).rolling(window=period, min_periods=1).sum()

    plus_di = 100 * (plus_dm_smooth / tr_smooth)
    minus_di = 100 * (minus_dm_smooth / tr_smooth)

    # Calculate DX
    dx_denom = plus_di + minus_di
    dx = 100 * ((plus_di - minus_di).abs() / dx_denom)
    dx = dx.fillna(0)

    # Calculate ADX (EMA of DX)
    adx = dx.ewm(span=period, adjust=False).mean()

    # Extract only current period
    result_len = len(data)
    adx = adx.iloc[-result_len:].reset_index(drop=True)

    return adx.fillna(25.0)
