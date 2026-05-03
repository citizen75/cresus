"""
Bollinger Bands Indicator

Syntax: bb_<period>_<std_dev> or bollinger_bands_<period>_<std_dev>
Example: bb_20_2

Returns: Dict with 'bb_upper', 'bb_middle', 'bb_lower' Series
"""

import pandas as pd
from typing import Optional, Dict


def calculate(
    data: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> Dict[str, pd.Series]:
    """
    Calculate Bollinger Bands.

    Args:
        data: OHLCV DataFrame
        period: SMA period (default: 20)
        std_dev: Standard deviation multiplier (default: 2)
        history_df: Optional historical data for extended lookback

    Returns:
        Dict with keys:
            - 'bb': Upper band
            - 'bb_upper': Upper band
            - 'bb_middle': Middle band (SMA)
            - 'bb_lower': Lower band

    Formula:
        Middle Band = SMA
        Upper Band = SMA + (std_dev * StdDev)
        Lower Band = SMA - (std_dev * StdDev)
    """
    # Get close prices
    if "CLOSE" in data.columns:
        close = data["CLOSE"]
    elif "Close" in data.columns:
        close = data["Close"]
    else:
        close = data.iloc[:, -1]

    # Use history if provided
    if history_df is not None:
        if "CLOSE" in history_df.columns:
            hist_close = history_df["CLOSE"]
        else:
            hist_close = history_df.iloc[:, -1]
        combined = pd.concat([hist_close, close], ignore_index=True)
    else:
        combined = close

    # Calculate SMA and StdDev
    sma = combined.rolling(window=period, min_periods=1).mean()
    std = combined.rolling(window=period, min_periods=1).std()

    # Calculate bands
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)

    # Extract only current period
    result_len = len(data)
    sma = sma.iloc[-result_len:].reset_index(drop=True)
    upper = upper.iloc[-result_len:].reset_index(drop=True)
    lower = lower.iloc[-result_len:].reset_index(drop=True)

    return {
        "bb": upper,
        "bb_upper": upper,
        "bb_middle": sma,
        "bb_lower": lower,
    }
