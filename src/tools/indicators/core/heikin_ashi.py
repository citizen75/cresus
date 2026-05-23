"""
Heikin Ashi (HA) and Smooth Heikin Ashi (SHA) Indicators

Canonical implementation following standard quantitative finance formulas.

Syntax:
  - ha for Heikin Ashi
  - sha_<period> for Smooth Heikin Ashi with EMA smoothing (default period: 14)

Examples:
  - ha
  - sha_14

Heikin Ashi provides smoothed candlesticks that reduce noise and make trends clearer.

Formulas (Canonical):

Regular HA:
  HA Close = (Open + High + Low + Close) / 4
  HA Open = (previous HA Open + previous HA Close) / 2
  HA High = max(High, HA Open, HA Close)
  HA Low = min(Low, HA Open, HA Close)

Smooth HA (SHA):
  1. Calculate HA candles (as above)
  2. Apply EMA smoothing to each HA component:
     SHA Open = EMA(HA Open, period)
     SHA Close = EMA(HA Close, period)
     SHA High = EMA(HA High, period)
     SHA Low = EMA(HA Low, period)

Color signals:
  HA Green = HA Close > HA Open
  HA Red = HA Close < HA Open
  SHA Green = SHA Close > SHA Open
  SHA Red = SHA Close < SHA Open

Wick signals (trend strength):
  SHA Up = (SHA Close > SHA Open) AND (SHA Low >= SHA Open)
  SHA Down = (SHA Close < SHA Open) AND (SHA High <= SHA Open)
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

    # Calculate Heikin Ashi (canonical recursive formulas)
    n = len(o)
    ha_close = (o + h + l + c) / 4.0
    ha_open = np.zeros(n)

    # Canonical HA recursion (no truncation or drift prevention)
    ha_open[0] = (o[0] + c[0]) / 2.0
    for i in range(1, n):
        ha_open[i] = (ha_open[i - 1] + ha_close[i - 1]) / 2.0

    ha_high = np.maximum(np.maximum(h, ha_open), ha_close)
    ha_low = np.minimum(np.minimum(l, ha_open), ha_close)

    # Extract only current period
    result_len = len(data)
    ha_open_series = pd.Series(ha_open[-result_len:]).reset_index(drop=True)
    ha_high_series = pd.Series(ha_high[-result_len:]).reset_index(drop=True)
    ha_low_series = pd.Series(ha_low[-result_len:]).reset_index(drop=True)
    ha_close_series = pd.Series(ha_close[-result_len:]).reset_index(drop=True)

    # HA candle color based on HA values (not raw)
    ha_green = (ha_close_series > ha_open_series).astype(int)
    ha_red = (ha_close_series < ha_open_series).astype(int)

    return {
        "ha_open": ha_open_series,
        "ha_high": ha_high_series,
        "ha_low": ha_low_series,
        "ha_close": ha_close_series,
        "ha_green": ha_green,
        "ha_red": ha_red,
        "ha": ha_close_series,  # Default to close
    }


def calculate_smooth(
    data: pd.DataFrame,
    period: int = 14,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> Dict[str, pd.Series]:
    """
    Calculate Smooth Heikin Ashi (canonical: EMA-smoothed HA values).

    Args:
        data: OHLCV DataFrame
        period: EMA period for smoothing (default: 14)
        history_df: Optional historical data for extended lookback
        **kwargs: Additional parameters

    Returns:
        Dict with keys:
            - 'sha_open': Smooth HA Open (EMA of HA open)
            - 'sha_high': Smooth HA High (EMA of HA high)
            - 'sha_low': Smooth HA Low (EMA of HA low)
            - 'sha_close': Smooth HA Close (EMA of HA close)
            - 'sha_green': 1 if sha_close > sha_open, 0 otherwise
            - 'sha_red': 1 if sha_close < sha_open, 0 otherwise
            - 'sha_bullish': 1 if sha_close > sha_open (same as green)
            - 'sha_up': 1 if bullish with no bottom wick
            - 'sha_down': 1 if bearish with no top wick
    """
    # First calculate regular Heikin Ashi
    ha_dict = calculate(data, history_df=history_df, **kwargs)

    # Extract HA values
    ha_open = ha_dict["ha_open"]
    ha_high = ha_dict["ha_high"]
    ha_low = ha_dict["ha_low"]
    ha_close = ha_dict["ha_close"]

    # Apply canonical EMA smoothing to HA components
    sha_open = ha_open.ewm(span=period, adjust=False).mean()
    sha_high = ha_high.ewm(span=period, adjust=False).mean()
    sha_low = ha_low.ewm(span=period, adjust=False).mean()
    sha_close = ha_close.ewm(span=period, adjust=False).mean()

    # SHA candle color based on smoothed HA values
    sha_green = (sha_close > sha_open).astype(int)
    sha_red = (sha_close < sha_open).astype(int)

    # Bullish indicator (same logic as green, for consistency)
    sha_bullish = (sha_close > sha_open).astype(int)

    # Wick indicators: trend strength without counter-trend wicks
    # sha_up: Bullish candle (close > open) with no lower wick (low >= open)
    # sha_down: Bearish candle (close < open) with no upper wick (high <= open)
    sha_up = ((sha_close > sha_open) & (sha_low >= sha_open)).astype(int)
    sha_down = ((sha_close < sha_open) & (sha_high <= sha_open)).astype(int)

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
