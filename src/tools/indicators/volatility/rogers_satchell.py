"""
Rogers-Satchell Volatility Estimator

Syntax: rogers_satchell_<period>
Example: rogers_satchell_14

Returns: Series with volatility estimates
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
    high = data.get("HIGH", data.get("High", None))
    low = data.get("LOW", data.get("Low", None))
    close = data.get("CLOSE", data.get("Close", None))
    open_price = data.get("OPEN", data.get("Open", None))

    if any(x is None for x in [high, low, close, open_price]):
        return pd.Series([0.0] * len(data))

    # Use history if provided
    if history_df is not None:
        hist_high = history_df.get("HIGH", history_df.get("High", None))
        hist_low = history_df.get("LOW", history_df.get("Low", None))
        hist_close = history_df.get("CLOSE", history_df.get("Close", None))
        hist_open = history_df.get("OPEN", history_df.get("Open", None))

        if all(x is not None for x in [hist_high, hist_low, hist_close, hist_open]):
            high = pd.concat([hist_high, high], ignore_index=True)
            low = pd.concat([hist_low, low], ignore_index=True)
            close = pd.concat([hist_close, close], ignore_index=True)
            open_price = pd.concat([hist_open, open_price], ignore_index=True)

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
