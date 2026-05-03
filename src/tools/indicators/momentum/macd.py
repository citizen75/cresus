"""
MACD (Moving Average Convergence Divergence) Indicator

Syntax: macd_<fast>_<slow>_<signal>
Example: macd_12_26_9

Returns: Dict with 'macd_line', 'macd_signal', 'macd_histogram' Series
"""

import pandas as pd
from typing import Optional, Dict


def calculate(
    data: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> Dict[str, pd.Series]:
    """
    Calculate MACD (Moving Average Convergence Divergence).

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

    Formula:
        MACD Line = 12-EMA - 26-EMA
        Signal Line = 9-EMA of MACD Line
        Histogram = MACD Line - Signal Line
    """
    # Get close prices
    if "CLOSE" in data.columns:
        close = data["CLOSE"]
    elif "Close" in data.columns:
        close = data["Close"]
    else:
        close = data.iloc[:, -1]

    # Use history_df for calculation if provided (to get earlier values)
    if history_df is not None:
        if "CLOSE" in history_df.columns:
            hist_close = history_df["CLOSE"]
        else:
            hist_close = history_df.iloc[:, -1]
        # Combine history + current
        combined = pd.concat([hist_close, close], ignore_index=True)
    else:
        combined = close

    # Calculate EMAs
    ema_fast = combined.ewm(span=fast, adjust=False).mean()
    ema_slow = combined.ewm(span=slow, adjust=False).mean()

    # MACD line
    macd_line = ema_fast - ema_slow

    # Signal line
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()

    # Histogram
    histogram = macd_line - signal_line

    # Extract only the current period data (slice to match input length)
    result_len = len(data)
    macd_line = macd_line.iloc[-result_len:].reset_index(drop=True)
    signal_line = signal_line.iloc[-result_len:].reset_index(drop=True)
    histogram = histogram.iloc[-result_len:].reset_index(drop=True)

    return {
        "macd": macd_line,
        "macd_line": macd_line,
        "macd_signal": signal_line,
        "macd_histogram": histogram,
    }
