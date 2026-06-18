"""
Rogers-Satchell Volatility Estimator

Syntax: rogers_satchell_<period>
Example: rogers_satchell_14

Returns: Series with volatility estimates (non-negative)

The Rogers-Satchell estimator uses high, low, open, and close prices.
Unlike other volatility measures, it doesn't assume zero overnight drift,
making it suitable for gap openings and price limits.

Citation: L. C. G. Rogers & S. E. Satchell (1991)
"""

import pandas as pd
import numpy as np
from typing import Optional
from ..utils.helpers import get_high, get_low, get_close, get_open, ColumnError


def calculate(
    data: pd.DataFrame,
    period: int = 14,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate Rogers-Satchell Volatility Estimator.

    Args:
        data: OHLCV DataFrame with HIGH, LOW, OPEN, CLOSE columns
        period: Lookback period (default: 14)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with volatility estimates (non-negative)

    Formula:
        RS = sqrt(mean(ln(H/C) * ln(H/O) + ln(L/C) * ln(L/O)))

    Advantages:
        - Doesn't assume zero drift
        - Works with gap openings
        - Unbiased for price limits
    """
    # Get OHLC with proper error handling
    try:
        high = get_high(data)
        low = get_low(data)
        close = get_close(data)
        open_price = get_open(data)
    except ColumnError as e:
        raise ValueError(f"Rogers-Satchell calculation failed: {str(e)}") from e

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
        except (ColumnError, KeyError) as e:
            # Continue with current data if history fails
            pass

    # Avoid division by zero - replace with NaN
    high = high.replace(0, np.nan)
    low = low.replace(0, np.nan)
    close = close.replace(0, np.nan)
    open_price = open_price.replace(0, np.nan)

    # Calculate log returns with protection against invalid operations
    # Clip values to avoid log(0) or log(inf)
    high = high.clip(lower=1e-10)
    low = low.clip(lower=1e-10)
    close = close.clip(lower=1e-10)
    open_price = open_price.clip(lower=1e-10)

    # Calculate log ratios
    ln_hc = np.log(high / close)
    ln_ho = np.log(high / open_price)
    ln_lc = np.log(low / close)
    ln_lo = np.log(low / open_price)

    # Calculate RS product
    rs_value = ln_hc * ln_ho + ln_lc * ln_lo

    # Calculate rolling mean then take square root
    # Ensure we only take sqrt of non-negative values
    rs_mean = rs_value.rolling(window=period, min_periods=1).mean()
    rs_mean = rs_mean.clip(lower=0.0)  # Ensure non-negative before sqrt
    rs = np.sqrt(rs_mean)

    # Extract only current period
    result_len = len(data)
    rs = rs.iloc[-result_len:].reset_index(drop=True)

    # Fill NaN and ensure non-negative
    rs = rs.fillna(0.0)
    rs = rs.clip(lower=0.0)

    return rs
