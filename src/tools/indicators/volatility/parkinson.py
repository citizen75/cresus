"""
Parkinson Volatility Estimator

Syntax: parkinson_<period>
Example: parkinson_14

Returns: Series with volatility estimates
"""

import pandas as pd
import numpy as np
from typing import Optional
from ..utils.helpers import get_high, get_low


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
        Series with volatility estimates

    Formula:
        Parkinson = sqrt(1/(4*n*ln(2)) * sum(ln(H/L)^2))
    """
    # Get HIGH and LOW
    try:
        high = get_high(data)
        low = get_low(data)
    except Exception:
        return pd.Series([0.0] * len(data))

    # Use history if provided
    if history_df is not None:
        try:
            hist_high = get_high(history_df)
            hist_low = get_low(history_df)

            high = pd.concat([hist_high, high], ignore_index=True)
            low = pd.concat([hist_low, low], ignore_index=True)
        except Exception:
            pass

    # Calculate log returns
    hl_ratio = high / low
    hl_ratio = hl_ratio.replace(0, np.nan)  # Avoid division by zero
    log_returns = np.log(hl_ratio)

    # Calculate Parkinson
    c = 1 / (4 * np.log(2))
    parkinson = (log_returns ** 2).rolling(window=period, min_periods=1).sum()
    parkinson = np.sqrt(c / period * parkinson)

    # Extract only current period
    result_len = len(data)
    parkinson = parkinson.iloc[-result_len:].reset_index(drop=True)

    return parkinson.fillna(0.0)
