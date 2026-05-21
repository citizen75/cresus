"""
Rogers-Satchell Volatility Estimator

Syntax: rogers_satchell_<period>
Example: rogers_satchell_14

Returns: Series with volatility estimates
"""

import pandas as pd
import numpy as np
from typing import Optional
from ..utils.helpers import get_high, get_low, get_close, get_open


def calculate(
    data: pd.DataFrame,
    period: int = 14,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate Rogers-Satchell Volatility Estimator.

    Args:
        data: OHLCV DataFrame with HIGH, LOW, CLOSE columns
        period: Lookback period (default: 14)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with volatility estimates

    Formula:
        RS = sqrt(mean(ln(H/C) * ln(H/O) + ln(L/C) * ln(L/O)))
    """
    # Get OHLC
    try:
        high = get_high(data)
        low = get_low(data)
        close = get_close(data)
        open_price = get_open(data)
    except Exception:
        return pd.Series([0.0] * len(data))

    # Use history if provided
    if history_df is not None:
        try:
            hist_high = get_high(history_df)
            hist_low = get_low(history_df)
            hist_close = get_close(history_df)
            hist_open = get_open(history_df)

            high = pd.concat([hist_high, high], ignore_index=True)
            low = pd.concat([hist_low, low], ignore_index=True)
            close = pd.concat([hist_close, close], ignore_index=True)
            open_price = pd.concat([hist_open, open_price], ignore_index=True)
        except Exception:
            pass

    # Avoid division by zero
    high = high.replace(0, np.nan)
    low = low.replace(0, np.nan)
    close = close.replace(0, np.nan)
    open_price = open_price.replace(0, np.nan)

    # Calculate log returns
    ln_hc = np.log(high / close)
    ln_ho = np.log(high / open_price)
    ln_lc = np.log(low / close)
    ln_lo = np.log(low / open_price)

    # Calculate RS
    rs_value = ln_hc * ln_ho + ln_lc * ln_lo
    rs = (rs_value.rolling(window=period, min_periods=1).mean()).apply(lambda x: np.sqrt(x) if x >= 0 else 0)

    # Extract only current period
    result_len = len(data)
    rs = rs.iloc[-result_len:].reset_index(drop=True)

    return rs.fillna(0.0)
