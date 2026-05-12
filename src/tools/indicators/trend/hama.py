"""
HAMA (Heikin-Ashi Moving Average) Indicator - NST Version

Implements the North Star Day Trading HAMA Candles indicator.

Syntax: hama_<length_open>_<length_close>_<ema_line>
Example: hama_25_20_55

Returns: Dict with 'open', 'high', 'low', 'close', 'ma_line' Series
"""

import pandas as pd
from typing import Optional, Dict


def calculate(
    data: pd.DataFrame,
    length_open: int = 25,
    length_close: int = 20,
    ema_line: int = 55,
    open_type: str = "EMA",
    close_type: str = "EMA",
    ma_line_type: str = "WMA",
    ma_source: str = "hl2",
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> Dict[str, pd.Series]:
    """
    Calculate HAMA (Heikin-Ashi Moving Average) - NST Version.

    Implements the exact algorithm from the Pine Script:
    - Open: EMA of previous (O+C)/2
    - High: EMA of max(H, C)
    - Low: EMA of min(L, C)
    - Close: EMA of (O+H+L+C)/4
    - MA Line: WMA of (H+L)/2

    Args:
        data: OHLCV DataFrame
        length_open: Period for open MA (default: 25)
        length_close: Period for close MA (default: 20)
        ema_line: Period for trend line MA (default: 55)
        open_type: Type of MA for open - "EMA", "SMA", "WMA" (default: "EMA")
        close_type: Type of MA for close - "EMA", "SMA", "WMA" (default: "EMA")
        ma_line_type: Type of MA for trend line - "EMA", "SMA", "WMA" (default: "WMA")
        ma_source: Source for trend line - "hl2" (H+L)/2, "ohlc4" (O+H+L+C)/4 (default: "hl2")
        history_df: Optional historical data for extended lookback

    Returns:
        Dict with Series: 'open', 'high', 'low', 'close', 'ma_line'
    """
    # Combine history if provided
    if history_df is not None:
        df = pd.concat([history_df, data], ignore_index=True)
    else:
        df = data.copy()

    # Get OHLC
    if "Open" in df.columns:
        opens = df["Open"].reset_index(drop=True)
        highs = df["High"].reset_index(drop=True)
        lows = df["Low"].reset_index(drop=True)
        closes = df["Close"].reset_index(drop=True)
    else:
        opens = df.iloc[:, 0].reset_index(drop=True)
        highs = df.iloc[:, 1].reset_index(drop=True)
        lows = df.iloc[:, 2].reset_index(drop=True)
        closes = df.iloc[:, 3].reset_index(drop=True)

    # === HAMA Open ===
    # SourceOpen = (open[1] + close[1]) / 2 (previous bar's (O+C)/2)
    source_open = ((opens.shift(1) + closes.shift(1)) / 2).fillna((opens + closes) / 2)
    hama_open = _apply_ma(source_open, length_open, open_type)

    # === HAMA High ===
    # SourceHigh = max(high, close)
    source_high = pd.concat([highs, closes], axis=1).max(axis=1)
    hama_high = _apply_ma(source_high, 20, "EMA")  # Pine script uses fixed 20

    # === HAMA Low ===
    # SourceLow = min(low, close)
    source_low = pd.concat([lows, closes], axis=1).min(axis=1)
    hama_low = _apply_ma(source_low, 20, "EMA")  # Pine script uses fixed 20

    # === HAMA Close ===
    # SourceClose = (open + high + low + close) / 4
    source_close = (opens + highs + lows + closes) / 4
    hama_close = _apply_ma(source_close, length_close, close_type)

    # === MA Line (Trend Line) ===
    # Applied to ma_source with ma_line_type
    if ma_source.lower() == "hl2":
        trend_source = (highs + lows) / 2
    elif ma_source.lower() == "ohlc4":
        trend_source = (opens + highs + lows + closes) / 4
    else:
        trend_source = closes

    ma_line = _apply_ma(trend_source, ema_line, ma_line_type)

    # Extract only current period if history was used
    if history_df is not None:
        result_len = len(data)
        hama_open = hama_open.iloc[-result_len:].reset_index(drop=True)
        hama_high = hama_high.iloc[-result_len:].reset_index(drop=True)
        hama_low = hama_low.iloc[-result_len:].reset_index(drop=True)
        hama_close = hama_close.iloc[-result_len:].reset_index(drop=True)
        ma_line = ma_line.iloc[-result_len:].reset_index(drop=True)

    return {
        'close': hama_close.fillna(closes.mean()),  # Default return
        'open': hama_open.fillna(opens.mean()),
        'high': hama_high.fillna(highs.mean()),
        'low': hama_low.fillna(lows.mean()),
        'trend': ma_line.fillna(closes.mean()),  # trend = MA line
    }


def _apply_ma(series: pd.Series, period: int, ma_type: str = "EMA") -> pd.Series:
    """Apply moving average to series."""
    if ma_type.upper() == "EMA":
        return series.ewm(span=period, adjust=False).mean()
    elif ma_type.upper() == "WMA":
        # Weighted Moving Average: weights = 1, 2, 3, ..., period
        weights = pd.Series(range(1, period + 1), dtype=float)
        def wma_func(x):
            return (x * weights[:len(x)]).sum() / weights[:len(x)].sum()
        return series.rolling(period).apply(wma_func, raw=False)
    else:  # SMA
        return series.rolling(period).mean()
