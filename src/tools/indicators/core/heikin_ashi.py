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

Wick signals (trend strength - no bottom/top wick):
  SHA Up = (SHA Close > SHA Open) AND (SHA Low >= SHA Open)
  SHA Down = (SHA Close < SHA Open) AND (SHA High <= SHA Open)
"""

import pandas as pd
import pandas_ta_classic as pandas_ta
import numpy as np
from typing import Optional, Dict, Literal


def _alma(series: pd.Series, length: int = 14, sigma: float = 6.0, offset: float = 0.85) -> pd.Series:
    """
    Arnaud Legoux Moving Average (ALMA) - smoother, more responsive than EMA.

    Args:
        series: Input price series
        length: MA period
        sigma: Smoothness parameter (higher = smoother)
        offset: Balance between responsiveness and smoothness (0-1, default 0.85)

    Returns:
        ALMA values
    """
    m = offset * (length - 1)
    s = length / sigma

    w = np.exp(-((np.arange(length) - m) ** 2) / (2 * s ** 2))
    w /= w.sum()

    alma_values = []
    for i in range(len(series)):
        if i < length - 1:
            alma_values.append(np.nan)
        else:
            alma_values.append(np.dot(series.iloc[i - length + 1:i + 1].values, w))

    return pd.Series(alma_values, index=series.index)


def _apply_ma(series: pd.Series, ma_type: str, length: int, sigma: float = 6.0, offset: float = 0.85) -> pd.Series:
    """Apply moving average with configurable type."""
    if ma_type.lower() == "alma":
        return _alma(series, length, sigma, offset)
    elif ma_type.lower() == "ema":
        return pandas_ta.ema(series, length=length)
    elif ma_type.lower() == "sma":
        return pandas_ta.sma(series, length=length)
    else:
        # Default to EMA
        return pandas_ta.ema(series, length=length)


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
    elif "open" in df.columns:
        df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"}, inplace=True)

    # Combine with history if provided
    if history_df is not None:
        if "OPEN" in history_df.columns:
            hist = history_df.copy()
            hist.rename(columns={"OPEN": "Open", "HIGH": "High", "LOW": "Low", "CLOSE": "Close"}, inplace=True)
        elif "open" in history_df.columns:
            hist = history_df.copy()
            hist.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"}, inplace=True)
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

    # Wick indicators for regular HA (exact equality possible with raw HA)
    ha_up = ((ha_close_series > ha_open_series) & (ha_low_series == ha_open_series)).astype(int)
    ha_down = ((ha_close_series < ha_open_series) & (ha_high_series == ha_open_series)).astype(int)

    return {
        "ha_open": ha_open_series,
        "ha_high": ha_high_series,
        "ha_low": ha_low_series,
        "ha_close": ha_close_series,
        "ha_green": ha_green,
        "ha_red": ha_red,
        "ha_up": ha_up,
        "ha_down": ha_down,
        "ha": ha_close_series,  # Default to close
    }


def calculate_smooth(
    data: pd.DataFrame,
    period: int = 14,
    history_df: Optional[pd.DataFrame] = None,
    pre_smooth_type: str = "none",
    pre_smooth_length: int = 14,
    post_smooth_type: str = "ema",
    post_smooth_length: int = 14,
    alma_sigma: float = 6.0,
    alma_offset: float = 0.85,
    **kwargs
) -> Dict[str, pd.Series]:
    """
    Calculate Smooth Heikin Ashi with TradingView-style parameters.

    Args:
        data: OHLCV DataFrame
        period: Deprecated - use post_smooth_length instead
        history_df: Optional historical data for extended lookback
        pre_smooth_type: Pre-smooth OHLC before HA calculation: "none", "ema", "alma", "sma" (default: "none")
        pre_smooth_length: Pre-smoothing period (default: 14)
        post_smooth_type: Post-smooth HA components: "ema", "alma", "sma" (default: "ema")
        post_smooth_length: Post-smoothing period (default: 14)
        alma_sigma: ALMA smoothness parameter (default: 6.0)
        alma_offset: ALMA responsiveness parameter 0-1 (default: 0.85)
        **kwargs: Additional parameters

    Returns:
        Dict with keys:
            - 'sha_open': Smooth HA Open
            - 'sha_high': Smooth HA High
            - 'sha_low': Smooth HA Low
            - 'sha_close': Smooth HA Close
            - 'sha_green': 1 if sha_close > sha_open, 0 otherwise
            - 'sha_red': 1 if sha_close < sha_open, 0 otherwise
            - 'sha_bullish': 1 if sha_close > sha_open (same as green)
            - 'sha_up': 1 if bullish AND sha_low >= sha_open (no bottom wick)
            - 'sha_down': 1 if bearish AND sha_high <= sha_open (no top wick)
            - 'sha': Smooth HA Close (default)
    """
    # Use post_smooth_length if provided, else fall back to period
    post_length = post_smooth_length if post_smooth_length != 14 else period

    # Normalize column names
    df = data.copy()
    if "OPEN" in df.columns:
        df.rename(columns={"OPEN": "Open", "HIGH": "High", "LOW": "Low", "CLOSE": "Close"}, inplace=True)
    elif "open" in df.columns:
        df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"}, inplace=True)

    # Combine with history if provided
    if history_df is not None:
        if "OPEN" in history_df.columns:
            hist = history_df.copy()
            hist.rename(columns={"OPEN": "Open", "HIGH": "High", "LOW": "Low", "CLOSE": "Close"}, inplace=True)
        elif "open" in history_df.columns:
            hist = history_df.copy()
            hist.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"}, inplace=True)
        else:
            hist = history_df.copy()

        df = pd.concat([hist, df], ignore_index=True)

    # Step 1: Pre-smooth OHLC if requested (TradingView style)
    if pre_smooth_type.lower() != "none":
        df["Open"] = _apply_ma(df["Open"], pre_smooth_type, pre_smooth_length, alma_sigma, alma_offset)
        df["High"] = _apply_ma(df["High"], pre_smooth_type, pre_smooth_length, alma_sigma, alma_offset)
        df["Low"] = _apply_ma(df["Low"], pre_smooth_type, pre_smooth_length, alma_sigma, alma_offset)
        df["Close"] = _apply_ma(df["Close"], pre_smooth_type, pre_smooth_length, alma_sigma, alma_offset)

    # Step 2: Calculate HA using pandas-ta
    ha = pandas_ta.ha(df["Open"], df["High"], df["Low"], df["Close"])

    # Step 3: Post-smooth HA components
    sha_open = _apply_ma(pd.Series(ha["HA_open"]), post_smooth_type, post_length, alma_sigma, alma_offset)
    sha_high = _apply_ma(pd.Series(ha["HA_high"]), post_smooth_type, post_length, alma_sigma, alma_offset)
    sha_low = _apply_ma(pd.Series(ha["HA_low"]), post_smooth_type, post_length, alma_sigma, alma_offset)
    sha_close = _apply_ma(pd.Series(ha["HA_close"]), post_smooth_type, post_length, alma_sigma, alma_offset)

    # Extract only current period
    result_len = len(data)
    sha_open_series = pd.Series(sha_open.values[-result_len:]).reset_index(drop=True)
    sha_high_series = pd.Series(sha_high.values[-result_len:]).reset_index(drop=True)
    sha_low_series = pd.Series(sha_low.values[-result_len:]).reset_index(drop=True)
    sha_close_series = pd.Series(sha_close.values[-result_len:]).reset_index(drop=True)

    # SHA candle color based on smoothed HA values
    sha_green = (sha_close_series > sha_open_series).astype(int)
    sha_red = (sha_close_series < sha_open_series).astype(int)

    # Bullish indicator (same logic as green)
    sha_bullish = (sha_close_series > sha_open_series).astype(int)

    # Wick indicators: bullish/bearish with minimal wicks
    # For smoothed HA, exact equality is impossible due to EMA smoothing
    # Use practical epsilon tolerance of 0.5% as percentage of price
    # sha_up: bullish candle (close > open) AND bottom wick small (open - low < epsilon)
    # sha_down: bearish candle (close < open) AND top wick small (high - open < epsilon)

    epsilon_pct = 0.005  # 0.5% tolerance (typical bid-ask spread)
    avg_price = (sha_close_series + sha_open_series) / 2
    epsilon = avg_price * epsilon_pct

    sha_up = ((sha_close_series > sha_open_series) & ((sha_open_series - sha_low_series) < epsilon)).astype(int)
    sha_down = ((sha_close_series < sha_open_series) & ((sha_high_series - sha_open_series) < epsilon)).astype(int)

    # Include period in key names for proper formula reference
    period_suffix = f"_{post_length}" if post_length else ""
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
