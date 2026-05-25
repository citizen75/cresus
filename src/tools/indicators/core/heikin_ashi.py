"""
Heikin Ashi (HA) and Smooth Heikin Ashi (SHA) Indicators

Industry-standard implementation using pandas-ta library.

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
import pandas_ta_classic as pandas_ta
from typing import Optional, Dict


def calculate(
    data: pd.DataFrame,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> Dict[str, pd.Series]:
    """
    Calculate Heikin Ashi candlesticks using pandas-ta.

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
            - 'ha_green': 1 if close > open, 0 otherwise
            - 'ha_red': 1 if close < open, 0 otherwise
            - 'ha': Heikin Ashi Close (default)
    """
    # Normalize column names
    df = data.copy()
    if "OPEN" in df.columns:
        df.rename(columns={"OPEN": "Open", "HIGH": "High", "LOW": "Low", "CLOSE": "Close"}, inplace=True)

    # Combine with history if provided
    if history_df is not None:
        if "OPEN" in history_df.columns:
            hist = history_df.copy()
            hist.rename(columns={"OPEN": "Open", "HIGH": "High", "LOW": "Low", "CLOSE": "Close"}, inplace=True)
        else:
            hist = history_df.copy()

        df = pd.concat([hist, df], ignore_index=True)

    # Calculate HA using pandas-ta
    ha = pandas_ta.ha(df["Open"], df["High"], df["Low"], df["Close"])

    # Extract only current period
    result_len = len(data)
    ha_open_series = pd.Series(ha["HA_open"].values[-result_len:]).reset_index(drop=True)
    ha_high_series = pd.Series(ha["HA_high"].values[-result_len:]).reset_index(drop=True)
    ha_low_series = pd.Series(ha["HA_low"].values[-result_len:]).reset_index(drop=True)
    ha_close_series = pd.Series(ha["HA_close"].values[-result_len:]).reset_index(drop=True)

    # HA candle color based on HA values
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
    Calculate Smooth Heikin Ashi (canonical: EMA-smoothed HA values) using pandas-ta.

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
            - 'sha': Smooth HA Close (default)
    """
    # Normalize column names
    df = data.copy()
    if "OPEN" in df.columns:
        df.rename(columns={"OPEN": "Open", "HIGH": "High", "LOW": "Low", "CLOSE": "Close"}, inplace=True)

    # Combine with history if provided
    if history_df is not None:
        if "OPEN" in history_df.columns:
            hist = history_df.copy()
            hist.rename(columns={"OPEN": "Open", "HIGH": "High", "LOW": "Low", "CLOSE": "Close"}, inplace=True)
        else:
            hist = history_df.copy()

        df = pd.concat([hist, df], ignore_index=True)

    # Calculate HA using pandas-ta
    ha = pandas_ta.ha(df["Open"], df["High"], df["Low"], df["Close"])

    # Apply EMA smoothing to HA components
    sha_open = pandas_ta.ema(ha["HA_open"], length=period)
    sha_high = pandas_ta.ema(ha["HA_high"], length=period)
    sha_low = pandas_ta.ema(ha["HA_low"], length=period)
    sha_close = pandas_ta.ema(ha["HA_close"], length=period)

    # Extract only current period
    result_len = len(data)
    sha_open_series = pd.Series(sha_open.values[-result_len:]).reset_index(drop=True)
    sha_high_series = pd.Series(sha_high.values[-result_len:]).reset_index(drop=True)
    sha_low_series = pd.Series(sha_low.values[-result_len:]).reset_index(drop=True)
    sha_close_series = pd.Series(sha_close.values[-result_len:]).reset_index(drop=True)

    # SHA candle color based on smoothed HA values
    sha_green = (sha_close_series > sha_open_series).astype(int)
    sha_red = (sha_close_series < sha_open_series).astype(int)

    # Bullish indicator (same logic as green, for consistency)
    sha_bullish = (sha_close_series > sha_open_series).astype(int)

    # Wick indicators: just check bullish/bearish (wick check disabled as always false)
    # Original conditions (low >= open, high <= open) are mathematically impossible in HA
    sha_up = (sha_close_series > sha_open_series).astype(int)
    sha_down = (sha_close_series < sha_open_series).astype(int)

    # Include period in key names for proper formula reference
    period_suffix = f"_{period}" if period else ""
    return {
        f"sha{period_suffix}_open": sha_open_series,
        f"sha{period_suffix}_high": sha_high_series,
        f"sha{period_suffix}_low": sha_low_series,
        f"sha{period_suffix}_close": sha_close_series,
        f"sha{period_suffix}_green": sha_green,
        f"sha{period_suffix}_red": sha_red,
        f"sha{period_suffix}_bullish": sha_bullish,
        f"sha{period_suffix}_up": sha_up,
        f"sha{period_suffix}_down": sha_down,
        f"sha{period_suffix}": sha_close_series,  # Default to close
    }
