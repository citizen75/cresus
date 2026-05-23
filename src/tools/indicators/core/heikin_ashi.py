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
import numpy as np
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
    ha_open = np.zeros(n)

    # To prevent HA Open from drifting over 4000+ bars, use simple (open+close)/2 for old bars
    # and proper HA recursion only for recent bars (last 200)
    lookback_limit = 200

    if n <= lookback_limit:
        # Small dataset: use full proper HA calculation
        ha_open[0] = (o[0] + c[0]) / 2.0
        for i in range(1, n):
            ha_open[i] = (ha_open[i - 1] + ha_close[i - 1]) / 2.0
    else:
        # Large dataset: split into old and recent
        transition_idx = n - lookback_limit

        # Old bars (before transition): use simple (open + close) / 2 to prevent drift
        ha_open[:transition_idx] = (o[:transition_idx] + c[:transition_idx]) / 2.0

        # Recent bars (last 200): use proper HA recursion anchored at transition point
        ha_open[transition_idx] = (o[transition_idx] + c[transition_idx]) / 2.0
        for i in range(transition_idx + 1, n):
            ha_open[i] = (ha_open[i - 1] + ha_close[i - 1]) / 2.0
    
    ha_high = pd.Series(h).combine(pd.Series(ha_open), max).combine(pd.Series(ha_close), max).values
    ha_low = pd.Series(l).combine(pd.Series(ha_open), min).combine(pd.Series(ha_close), min).values

    # Extract only current period
    result_len = len(data)
    ha_open_series = pd.Series(ha_open[-result_len:]).reset_index(drop=True)
    ha_high_series = pd.Series(ha_high[-result_len:]).reset_index(drop=True)
    ha_low_series = pd.Series(ha_low[-result_len:]).reset_index(drop=True)
    ha_close_series = pd.Series(ha_close[-result_len:]).reset_index(drop=True)

    # Use raw open/close for green/red to match actual chart colors
    # (HA open can drift, but raw close vs open always matches the visual candle)
    o_current = o[-result_len:]
    c_current = c[-result_len:]

    return {
        "ha_open": ha_open_series,
        "ha_high": ha_high_series,
        "ha_low": ha_low_series,
        "ha_close": ha_close_series,
        "ha_green": pd.Series((c_current > o_current).astype(int), index=ha_close_series.index),
        "ha_red": pd.Series((c_current < o_current).astype(int), index=ha_close_series.index),
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
    # Normalize column names to extract raw open/close for green/red signals
    df = data.copy()
    if "OPEN" in df.columns:
        df.rename(columns={"OPEN": "Open", "HIGH": "High", "LOW": "Low", "CLOSE": "Close"}, inplace=True)
    raw_close = df["Close"].values
    raw_open = df["Open"].values

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

    # Ensure basic geometric validity
    sha_high = pd.concat([sha_open, sha_high_ema, sha_close], axis=1).max(axis=1)
    sha_low = pd.concat([sha_open, sha_low_ema, sha_close], axis=1).min(axis=1)

    # Prevent inverted wicks: wicks should follow the candle body direction
    # Bullish candle (close > open): Low should not go below Open (no bottom wick below body)
    # Bearish candle (close < open): High should not go above Open (no top wick above body)
    is_bullish = sha_close > sha_open
    is_bearish = sha_close < sha_open

    sha_low_fixed = sha_low.copy()
    sha_high_fixed = sha_high.copy()

    # For bullish candles: ensure low >= open (remove inverted bottom wick)
    sha_low_fixed = pd.Series(
        [max(sha_low.iloc[i], sha_open.iloc[i]) if is_bullish.iloc[i] else sha_low.iloc[i]
         for i in range(len(sha_low))],
        index=sha_low.index
    )

    # For bearish candles: ensure high <= open (remove inverted top wick)
    sha_high_fixed = pd.Series(
        [min(sha_high.iloc[i], sha_open.iloc[i]) if is_bearish.iloc[i] else sha_high.iloc[i]
         for i in range(len(sha_high))],
        index=sha_high.index
    )

    sha_high = sha_high_fixed
    sha_low = sha_low_fixed

    # Calculate color indicators using RAW close vs open (matches actual candle colors)
    # This avoids the issue where smoothed HA values can drift and invert signals
    sha_green = pd.Series((raw_close > raw_open).astype(int), index=sha_close.index)
    sha_red = pd.Series((raw_close < raw_open).astype(int), index=sha_close.index)

    # Calculate bullish indicator: any upward candle (close > open)
    # For reversal signals, any bullish candle qualifies
    sha_bullish = pd.Series(
        (raw_close > raw_open).astype(int),
        index=sha_close.index
    )

    # Calculate wick indicators
    # sha_up: Bullish candle with no bottom wick (close > open AND low >= open)
    sha_up = pd.Series(
        ((sha_close > sha_open) & (sha_low >= sha_open)).astype(int),
        index=sha_close.index
    )

    # sha_down: Bearish candle with no top wick (close < open AND high <= open)
    sha_down = pd.Series(
        ((sha_close < sha_open) & (sha_high <= sha_open)).astype(int),
        index=sha_close.index
    )

    # Include period in key names for proper formula reference
    period_suffix = f"_{period}" if period else ""
    return {
        f"sha{period_suffix}_open": sha_open,
        f"sha{period_suffix}_high": sha_high,
        f"sha{period_suffix}_low": sha_low,
        f"sha{period_suffix}_close": sha_close,
        f"sha{period_suffix}_green": sha_green,
        f"sha{period_suffix}_red": sha_red,
        f"sha{period_suffix}_bullish": sha_bullish,
        f"sha{period_suffix}_up": sha_up,
        f"sha{period_suffix}_down": sha_down,
        f"sha{period_suffix}": sha_close,  # Default to close
    }
