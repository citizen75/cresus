"""
Parkinson Volatility Estimator

Syntax: parkinson_<period>
Example: parkinson_14

Returns: Series with volatility estimates (non-negative)

The Parkinson estimator is a volatility estimator that uses only high-low range
without considering close prices, making it faster to compute than traditional
intraday volatility measures.

Citation: H. A. Latané & R. J. Rendleman (1976)
"""

import pandas as pd
import numpy as np
from typing import Optional
from ..utils.helpers import get_high, get_low, ColumnError


def calculate(
    data: pd.DataFrame,
    period: int = 14,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate Parkinson Volatility Estimator.

    Args:
        data: OHLCV DataFrame with HIGH, LOW columns
        period: Lookback period (default: 14)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with volatility estimates (non-negative)

    Formula:
        c = 1 / (4 * ln(2)) ≈ 0.3607
        Parkinson = sqrt(c / n * sum(ln(H/L)^2))

    where n is the period and H/L are high/low prices
    """
    # Get HIGH and LOW with proper error handling
    try:
        high = get_high(data)
        low = get_low(data)
    except ColumnError as e:
        raise ValueError(f"Parkinson calculation failed: {str(e)}") from e

    # Use history if provided
    if history_df is not None:
        try:
            hist_high = get_high(history_df)
            hist_low = get_low(history_df)

            high = pd.concat([hist_high, high], ignore_index=True)
            low = pd.concat([hist_low, low], ignore_index=True)
        except (ColumnError, KeyError) as e:
            # Continue with current data if history fails
            pass

    # Calculate log returns with zero protection
    hl_ratio = high / low
    hl_ratio = hl_ratio.replace(0, np.nan)  # Avoid division by zero
    hl_ratio = hl_ratio.replace(np.inf, np.nan)  # Avoid infinity
    log_returns = np.log(hl_ratio.clip(lower=1e-10))  # Clip to avoid log(0)

    # Calculate Parkinson constant
    # c = 1 / (4 * ln(2)) ≈ 0.3607
    c = 1 / (4 * np.log(2))

    # Calculate sum of squared log returns over period
    sum_sq_log_returns = (log_returns ** 2).rolling(window=period, min_periods=1).sum()

    # Calculate Parkinson estimate
    parkinson = np.sqrt(c / period * sum_sq_log_returns)

    # Extract only current period
    result_len = len(data)
    parkinson = parkinson.iloc[-result_len:].reset_index(drop=True)

    # Fill NaN and ensure non-negative
    parkinson = parkinson.fillna(0.0)
    parkinson = parkinson.clip(lower=0.0)

    return parkinson
