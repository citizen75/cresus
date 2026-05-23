"""
MACD (Moving Average Convergence Divergence) Indicator

Syntax: macd_<fast>_<slow>_<signal>
Example: macd_12_26_9

Returns: Dict with 'macd_line', 'macd_signal', 'macd_histogram' Series

Uses pandas-ta library for canonical implementation.
"""

import pandas as pd
import pandas_ta
from typing import Optional, Dict
from ..utils.helpers import get_close


def calculate(
    data: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> Dict[str, pd.Series]:
    """
    Calculate MACD (Moving Average Convergence Divergence) using pandas-ta.

    Args:
        data: OHLCV DataFrame
        fast: Fast EMA period (default: 12)
        slow: Slow EMA period (default: 26)
        signal: Signal line EMA period (default: 9)
        history_df: Optional historical data for extended lookback

    Returns:
        Dict with keys:
            - 'macd_line': MACD line
            - 'macd_signal': Signal line (EMA of MACD line)
            - 'macd_histogram': Difference between MACD and signal
    """
    # Get close prices
    close = get_close(data)

    # Use history_df for calculation if provided
    if history_df is not None:
        hist_close = get_close(history_df)
        combined = pd.concat([hist_close, close], ignore_index=True)
    else:
        combined = close

    # Calculate MACD using pandas-ta
    # pandas-ta returns a DataFrame with MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9 columns
    macd_df = pandas_ta.macd(combined, fast=fast, slow=slow, signal=signal)

    # Extract only the current period data
    result_len = len(data)

    # Get the column names from the result
    macd_col = f"MACD_{fast}_{slow}_{signal}"
    signal_col = f"MACDs_{fast}_{slow}_{signal}"
    histogram_col = f"MACDh_{fast}_{slow}_{signal}"

    macd_line = macd_df[macd_col].iloc[-result_len:].reset_index(drop=True)
    signal_line = macd_df[signal_col].iloc[-result_len:].reset_index(drop=True)
    histogram = macd_df[histogram_col].iloc[-result_len:].reset_index(drop=True)

    return {
        "macd": macd_line,
        "macd_line": macd_line,
        "macd_signal": signal_line,
        "macd_histogram": histogram,
    }
