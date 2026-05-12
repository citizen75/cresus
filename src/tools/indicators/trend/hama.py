"""
HAMA (Heikin-Ashi Moving Average) Indicator

Syntax: hama_<length_open>_<length_close>_<ema_line>
Example: hama_25_20_55

Returns: Series with HAMA smoothed values
"""

import pandas as pd
from typing import Optional


def calculate(
    data: pd.DataFrame,
    length_open: int = 25,
    length_close: int = 20,
    ema_line: int = 55,
    ma_line_type: str = "WMA",
    ma_source: str = "hl2",
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate HAMA (Heikin-Ashi Moving Average).

    Args:
        data: OHLCV DataFrame
        length_open: Period for open moving average (default: 25)
        length_close: Period for close moving average (default: 20)
        ema_line: Period for trend line MA (default: 55)
        ma_line_type: Type of MA for trend line - "EMA", "SMA", "WMA" (default: "WMA")
        ma_source: Source for trend line - "hl2" (H+L)/2, "ohlc4" (O+H+L+C)/4 (default: "hl2")
        history_df: Optional historical data for extended lookback

    Returns:
        Series with HAMA smoothed values
    """
    # Combine history if provided
    if history_df is not None:
        df = pd.concat([history_df, data], ignore_index=True)
    else:
        df = data.copy()

    # Get OHLC
    if "Open" in df.columns:
        opens = df["Open"]
        highs = df["High"]
        lows = df["Low"]
        closes = df["Close"]
    else:
        opens = df.iloc[:, 0]
        highs = df.iloc[:, 1]
        lows = df.iloc[:, 2]
        closes = df.iloc[:, 3]

    # Calculate Heikin-Ashi candles
    ha_close = (opens + highs + lows + closes) / 4

    # Calculate cumulative HA open
    ha_open = opens.copy()
    for i in range(1, len(df)):
        ha_open.iloc[i] = (ha_open.iloc[i-1] + ha_close.iloc[i-1]) / 2

    # Apply moving averages to HA candles
    ha_open_ma = _apply_ma(ha_open, length_open, "EMA")
    ha_close_ma = _apply_ma(ha_close, length_close, "EMA")

    # Calculate trend line source
    if ma_source.lower() == "hl2":
        trend_source = (highs + lows) / 2
    elif ma_source.lower() == "ohlc4":
        trend_source = (opens + highs + lows + closes) / 4
    else:
        trend_source = closes

    # Apply MA line to trend source
    trend_line = _apply_ma(trend_source, ema_line, ma_line_type)

    # HAMA is the smoothed close with trend
    hama = (ha_close_ma + trend_line) / 2

    # Extract only current period if history was used
    if history_df is not None:
        result_len = len(data)
        hama = hama.iloc[-result_len:].reset_index(drop=True)

    return hama.fillna(closes.mean())


def _apply_ma(series: pd.Series, period: int, ma_type: str = "EMA") -> pd.Series:
    """Apply moving average to series."""
    if ma_type.upper() == "EMA":
        return series.ewm(span=period, adjust=False).mean()
    elif ma_type.upper() == "WMA":
        # Weighted Moving Average
        weights = pd.Series(range(1, period + 1))
        return series.rolling(period).apply(
            lambda x: (x * weights).sum() / weights.sum(),
            raw=False
        )
    else:  # SMA
        return series.rolling(period).mean()
