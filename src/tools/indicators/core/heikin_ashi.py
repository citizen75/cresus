"""
Heikin Ashi (HA) and Smooth Heikin Ashi (SHA) Indicators

Syntax: 
  - ha for Heikin Ashi
  - sha_<period> for Smooth Heikin Ashi with EMA smoothing (default period: 14)
  
Examples: 
  - ha
  - sha_14

Heikin Ashi provides smoothed candlesticks that reduce noise and make trends clearer.

Formula:
  HA Close = (Open + High + Low + Close) / 4
  HA Open = (previous HA Open + previous HA Close) / 2
  HA High = max(High, HA Open, HA Close)
  HA Low = min(Low, HA Open, HA Close)
  
  Smooth HA: Apply EMA smoothing to HA values
"""

import pandas as pd
from typing import Optional, Dict


def calculate(
    data: pd.DataFrame,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> Dict[str, pd.Series]:
    """
    Calculate Heikin Ashi candlesticks.

    Args:
        data: OHLCV DataFrame with columns: Open, High, Low, Close (or OPEN, HIGH, LOW, CLOSE)
        history_df: Optional historical data for extended lookback
        **kwargs: Additional parameters

    Returns:
        Dict with keys:
            - 'ha_open': Heikin Ashi Open
            - 'ha_high': Heikin Ashi High
            - 'ha_low': Heikin Ashi Low
            - 'ha_close': Heikin Ashi Close
    """
    # Normalize column names
    df = data.copy()
    if "OPEN" in df.columns:
        df.rename(columns={"OPEN": "Open", "HIGH": "High", "LOW": "Low", "CLOSE": "Close"}, inplace=True)

    # Extract OHLC
    o = df["Open"].values
    h = df["High"].values
    l = df["Low"].values
    c = df["Close"].values

    # Combine with history if provided
    if history_df is not None:
        if "OPEN" in history_df.columns:
            hist = history_df.copy()
            hist.rename(columns={"OPEN": "Open", "HIGH": "High", "LOW": "Low", "CLOSE": "Close"}, inplace=True)
        else:
            hist = history_df.copy()
        
        hist_o = hist["Open"].values
        hist_h = hist["High"].values
        hist_l = hist["Low"].values
        hist_c = hist["Close"].values
        
        o = pd.concat([pd.Series(hist_o), pd.Series(o)], ignore_index=True).values
        h = pd.concat([pd.Series(hist_h), pd.Series(h)], ignore_index=True).values
        l = pd.concat([pd.Series(hist_l), pd.Series(l)], ignore_index=True).values
        c = pd.concat([pd.Series(hist_c), pd.Series(c)], ignore_index=True).values

    # Calculate Heikin Ashi
    n = len(o)
    ha_close = (o + h + l + c) / 4.0
    ha_open = pd.Series(ha_close).shift(1).fillna(ha_close[0]).values
    ha_open[0] = (o[0] + c[0]) / 2.0
    
    # Forward-fill HA Open to match logic: HA_Open[i] = (HA_Open[i-1] + HA_Close[i-1]) / 2
    for i in range(1, n):
        ha_open[i] = (ha_open[i - 1] + ha_close[i - 1]) / 2.0
    
    ha_high = pd.Series(h).combine(pd.Series(ha_open), max).combine(pd.Series(ha_close), max).values
    ha_low = pd.Series(l).combine(pd.Series(ha_open), min).combine(pd.Series(ha_close), min).values

    # Extract only current period
    result_len = len(data)
    ha_open_series = pd.Series(ha_open[-result_len:]).reset_index(drop=True)
    ha_high_series = pd.Series(ha_high[-result_len:]).reset_index(drop=True)
    ha_low_series = pd.Series(ha_low[-result_len:]).reset_index(drop=True)
    ha_close_series = pd.Series(ha_close[-result_len:]).reset_index(drop=True)

    return {
        "ha_open": ha_open_series,
        "ha_high": ha_high_series,
        "ha_low": ha_low_series,
        "ha_close": ha_close_series,
        "ha_green": pd.Series((ha_close_series > ha_open_series).astype(int), index=ha_close_series.index),
        "ha_red": pd.Series((ha_close_series < ha_open_series).astype(int), index=ha_close_series.index),
        "ha": ha_close_series,  # Default to close
    }


def calculate_smooth(
    data: pd.DataFrame,
    period: int = 14,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> Dict[str, pd.Series]:
    """
    Calculate Smooth Heikin Ashi (with EMA smoothing).

    Args:
        data: OHLCV DataFrame
        period: EMA period for smoothing (default: 14)
        history_df: Optional historical data for extended lookback
        **kwargs: Additional parameters

    Returns:
        Dict with keys:
            - 'sha_open': Smooth HA Open
            - 'sha_high': Smooth HA High
            - 'sha_low': Smooth HA Low
            - 'sha_close': Smooth HA Close
            - 'sha_green': 1 if close > open (bullish), 0 otherwise
            - 'sha_red': 1 if close < open (bearish), 0 otherwise
    """
    # First calculate regular Heikin Ashi
    ha_dict = calculate(data, history_df=history_df, **kwargs)
    
    # Extract HA values
    ha_open = ha_dict["ha_open"]
    ha_high = ha_dict["ha_high"]
    ha_low = ha_dict["ha_low"]
    ha_close = ha_dict["ha_close"]
    
    # Apply EMA smoothing to all components
    sha_open = ha_open.ewm(span=period, adjust=False).mean()
    sha_high_ema = ha_high.ewm(span=period, adjust=False).mean()
    sha_low_ema = ha_low.ewm(span=period, adjust=False).mean()
    sha_close = ha_close.ewm(span=period, adjust=False).mean()

    # Constrain wicks to maintain valid candlestick geometry
    # High must be >= max(open, close), Low must be <= min(open, close)
    sha_high = pd.concat([sha_open, sha_high_ema, sha_close], axis=1).max(axis=1)
    sha_low = pd.concat([sha_open, sha_low_ema, sha_close], axis=1).min(axis=1)

    # Calculate color indicators
    sha_green = pd.Series((sha_close > sha_open).astype(int), index=sha_close.index)
    sha_red = pd.Series((sha_close < sha_open).astype(int), index=sha_close.index)

    # Calculate bullish indicator: strong upward movement (close in upper portion of range)
    # For EMA-smoothed data, "bullish" means close > open AND close is in the upper half of the range
    # This indicates sustained buying pressure, not just a tiny green wick
    range_size = sha_high - sha_low
    range_size = pd.Series(range_size).clip(lower=0.1)
    midpoint = sha_low + range_size * 0.5
    sha_bullish = pd.Series(
        ((sha_close > sha_open) & (sha_close > midpoint)).astype(int),
        index=sha_close.index
    )

    return {
        "sha_open": sha_open,
        "sha_high": sha_high,
        "sha_low": sha_low,
        "sha_close": sha_close,
        "sha_green": sha_green,
        "sha_red": sha_red,
        "sha_bullish": sha_bullish,
        "sha": sha_close,  # Default to close
    }
