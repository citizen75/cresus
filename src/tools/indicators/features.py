"""Feature computation utilities for indicators.

Maps features to their required base indicators and provides functions to
compute and extract feature values from indicator data.
"""

from typing import Dict, List, Optional
import pandas as pd
import numpy as np

from .indicators import calculate


# Feature requirements mapping - which base indicators each feature needs
FEATURE_REQUIREMENTS = {
    # Direct indicators
    "rsi_14": ["rsi_14"],
    "ema_20": ["ema_20"],
    "ema_50": ["ema_50"],
    "ema_200": ["ema_200"],
    "sma_20": ["sma_20"],
    "sma_50": ["sma_50"],
    "sma_200": ["sma_200"],
    "vratio_20": ["vratio_20"],
    "adx_14": ["adx_14"],
    # Derived features - differences
    "rsi_14_delta": ["rsi_14"],
    "close_minus_ema20": ["ema_20"],
    "close_minus_ema200": ["ema_200"],
    "close_minus_open": [],
    "ema_20_minus_50": ["ema_20", "ema_50"],
    "ema_50_minus_200": ["ema_50", "ema_200"],
    # Derived features - slopes and rates
    "ema20_slope": ["ema_20"],
    "trend_strength": ["adx_14"],
    # Normalized distances
    "distance_from_mean": ["sma_20"],
    "volume_spike_score": [],
    "ema_distance": ["ema_20"],
    "oversold_score": ["rsi_14"],
    # Aliases
    "volume_ratio": ["vratio_20"],
    # Forward returns (computed from future close prices)
    # NOTE: return_20d creates leakage when predicting future_return_15d
    # Use derived features instead: volatility, momentum acceleration, etc.
    "return_5d": [],
    "return_10d": [],
    "return_20d": [],  # For reference only - DO NOT use in training

    # Derived features (avoid direct overlap with future_return_15d)
    "volatility_20d": [],  # 20-day volatility (std of returns)
    "return_vol_ratio": [],  # return_20d / volatility_20d (risk-adjusted return)
    "momentum_accel": [],  # return_5d - return_20d (fast momentum - slow momentum)
    "momentum_accel_fast": [],  # return_5d - return_10d (ultra-fast acceleration)
    "zscore_return_20d": [],  # Cross-sectional z-score of returns
    "rel_return_20d": [],  # Relative to market (placeholder)
    # Breakout and relative strength
    "breakout_20d": [],  # close / max(close[-20:])
    "close_vs_open": [],  # (close - open) / close (intraday direction)
    # Boolean signals as floats
    "strong_momentum": ["rsi_14", "ema_20", "vratio_20"],
    "strong_uptrend": ["ema_20", "ema_50", "ema_200", "rsi_14"],
    "bullish_volume": ["vratio_20"],
}


def infer_base_indicators(features: List[str]) -> List[str]:
    """Infer which base indicators are needed to compute the requested features.

    Args:
        features: List of feature names to compute

    Returns:
        Sorted list of base indicator names needed
    """
    required = set()
    for feature in features:
        if feature in FEATURE_REQUIREMENTS:
            required.update(FEATURE_REQUIREMENTS[feature])
    return sorted(list(required))


def precompute_indicators(
    ticker_df: pd.DataFrame,
    feature_names: List[str],
    history_df: pd.DataFrame = None
) -> Dict[str, pd.Series]:
    """Pre-compute all base indicators for a ticker's entire history.

    Called once per ticker, returns dict of indicator_name → Series.
    Much faster than computing indicators repeatedly for each date.

    Args:
        ticker_df: Full OHLCV data for one ticker
        feature_names: Features that will be requested from this ticker
        history_df: Optional extended historical data

    Returns:
        Dict mapping base_indicator_name → pd.Series (full length)
    """
    if ticker_df.empty or len(ticker_df) < 2:
        return {}

    # Normalize column names
    df_norm = ticker_df.copy()
    df_norm.columns = df_norm.columns.str.lower()

    # Get all base indicators needed
    base_indicators = infer_base_indicators(feature_names)

    if not base_indicators:
        return {}

    indicator_dict = {}

    # Compute all base indicators using calculate()
    try:
        calc_results = calculate(base_indicators, df_norm, history_df=history_df)
        indicator_dict.update(calc_results)
    except Exception as e:
        import traceback
        print(f"ERROR in precompute_indicators: {e}")
        traceback.print_exc()
        # Return empty dict so caller knows it failed

    return indicator_dict


def extract_features_from_indicators(
    feature_names: List[str],
    indicator_dict: Dict[str, pd.Series],
    data_idx: int,
    df: pd.DataFrame
) -> Dict[str, Optional[float]]:
    """Extract feature values from pre-computed indicator series at a specific index.

    Fast O(n_features) operation after indicators are pre-computed once.
    Handles both direct indicators and derived features.

    Args:
        feature_names: Features to extract
        indicator_dict: Pre-computed indicator series (from precompute_indicators)
        data_idx: Index in the series (for the observation date)
        df: Original OHLCV DataFrame (for derived feature calculations)

    Returns:
        Dict mapping feature_name → float value (None if unavailable)
    """
    result = {}
    df_norm = df.copy()
    df_norm.columns = df_norm.columns.str.lower()

    for feature in feature_names:
        try:
            # Handle direct indicators and aliases
            if feature == "volume_ratio" and "vratio_20" in indicator_dict and len(indicator_dict["vratio_20"]) > data_idx:
                val = indicator_dict["vratio_20"].iloc[data_idx]
                result[feature] = None if pd.isna(val) else float(val)
            elif feature == "trend_strength" and "adx_14" in indicator_dict and len(indicator_dict["adx_14"]) > data_idx:
                val = indicator_dict["adx_14"].iloc[data_idx]
                result[feature] = None if pd.isna(val) else float(val)
            # Direct indicators
            elif feature in indicator_dict and len(indicator_dict[feature]) > data_idx:
                val = indicator_dict[feature].iloc[data_idx]
                result[feature] = None if pd.isna(val) else float(val)

            # Derived: Delta (1-period change)
            elif feature == "rsi_14_delta":
                if "rsi_14" in indicator_dict and len(indicator_dict["rsi_14"]) > data_idx:
                    if data_idx > 0:
                        val = indicator_dict["rsi_14"].iloc[data_idx] - indicator_dict["rsi_14"].iloc[data_idx - 1]
                        result[feature] = None if pd.isna(val) else float(val)
                    else:
                        result[feature] = None
                else:
                    result[feature] = None

            # Derived: Close minus EMA
            elif feature == "close_minus_ema20":
                if "ema_20" in indicator_dict and len(indicator_dict["ema_20"]) > data_idx:
                    close = df_norm["close"].iloc[data_idx]
                    ema = indicator_dict["ema_20"].iloc[data_idx]
                    result[feature] = float(close - ema)
                else:
                    result[feature] = None

            elif feature == "close_minus_ema200":
                if "ema_200" in indicator_dict and len(indicator_dict["ema_200"]) > data_idx:
                    close = df_norm["close"].iloc[data_idx]
                    ema = indicator_dict["ema_200"].iloc[data_idx]
                    result[feature] = float(close - ema)
                else:
                    result[feature] = None

            # Derived: Close minus Open
            elif feature == "close_minus_open":
                close = df_norm["close"].iloc[data_idx]
                open_ = df_norm["open"].iloc[data_idx]
                result[feature] = float(close - open_)

            # Derived: EMA differences
            elif feature == "ema_20_minus_50":
                if all(k in indicator_dict and len(indicator_dict[k]) > data_idx for k in ["ema_20", "ema_50"]):
                    result[feature] = float(indicator_dict["ema_20"].iloc[data_idx] - indicator_dict["ema_50"].iloc[data_idx])
                else:
                    result[feature] = None

            elif feature == "ema_50_minus_200":
                if all(k in indicator_dict and len(indicator_dict[k]) > data_idx for k in ["ema_50", "ema_200"]):
                    result[feature] = float(indicator_dict["ema_50"].iloc[data_idx] - indicator_dict["ema_200"].iloc[data_idx])
                else:
                    result[feature] = None

            # Derived: Slope (rate of change)
            elif feature == "ema20_slope":
                if "ema_20" in indicator_dict and len(indicator_dict["ema_20"]) > data_idx:
                    if data_idx > 0:
                        val = indicator_dict["ema_20"].iloc[data_idx] - indicator_dict["ema_20"].iloc[data_idx - 1]
                        result[feature] = None if pd.isna(val) else float(val)
                    else:
                        result[feature] = None
                else:
                    result[feature] = None

            # Derived: Distance from mean
            elif feature == "distance_from_mean":
                if "sma_20" in indicator_dict and len(indicator_dict["sma_20"]) > data_idx:
                    sma = indicator_dict["sma_20"].iloc[data_idx]
                    close = df_norm["close"].iloc[data_idx]
                    result[feature] = float((close - sma) / sma) if sma != 0 else None
                else:
                    result[feature] = None

            # Derived: Volume spike score (z-score of volume)
            elif feature == "volume_spike_score":
                if len(df_norm) >= 20 and data_idx >= 19:
                    vol = df_norm["volume"].iloc[data_idx - 19:data_idx + 1].values
                    mean_vol = np.mean(vol)
                    std_vol = np.std(vol)
                    if std_vol > 0:
                        result[feature] = float((df_norm["volume"].iloc[data_idx] - mean_vol) / std_vol)
                    else:
                        result[feature] = 0.0
                else:
                    result[feature] = None

            # Derived: Distance from EMA20 (normalized)
            elif feature == "ema_distance":
                if "ema_20" in indicator_dict and len(indicator_dict["ema_20"]) > data_idx:
                    close = df_norm["close"].iloc[data_idx]
                    ema = indicator_dict["ema_20"].iloc[data_idx]
                    result[feature] = float((close - ema) / ema) if ema != 0 else None
                else:
                    result[feature] = None

            # Derived: Oversold score (RSI below 30)
            elif feature == "oversold_score":
                if "rsi_14" in indicator_dict and len(indicator_dict["rsi_14"]) > data_idx:
                    rsi = indicator_dict["rsi_14"].iloc[data_idx]
                    result[feature] = float(1.0 if rsi < 30 else 0.0)
                else:
                    result[feature] = None

            # Derived: Max drawdown over 10 days (backward-looking)
            elif feature == "max_drawdown_10d":
                if data_idx >= 10:
                    close_vals = df_norm["close"].iloc[max(0, data_idx-9):data_idx+1].values
                    if len(close_vals) > 0:
                        min_close = np.min(close_vals)
                        current_close = df_norm["close"].iloc[data_idx]
                        result[feature] = float((min_close - current_close) / current_close)
                    else:
                        result[feature] = None
                else:
                    result[feature] = None

            # Derived: Max upside over 10 days (backward-looking)
            elif feature == "max_upside_10d":
                if data_idx >= 10:
                    close_vals = df_norm["close"].iloc[max(0, data_idx-9):data_idx+1].values
                    if len(close_vals) > 0:
                        max_close = np.max(close_vals)
                        current_close = df_norm["close"].iloc[data_idx]
                        result[feature] = float((max_close - current_close) / current_close)
                    else:
                        result[feature] = None
                else:
                    result[feature] = None

            # Derived: Boolean signals as floats
            elif feature == "strong_momentum":
                if all(k in indicator_dict and len(indicator_dict[k]) > data_idx for k in ["ema_20", "rsi_14", "vratio_20"]):
                    close = df_norm["close"].iloc[data_idx]
                    ema20 = indicator_dict["ema_20"].iloc[data_idx]
                    rsi14 = indicator_dict["rsi_14"].iloc[data_idx]
                    vratio = indicator_dict["vratio_20"].iloc[data_idx]
                    result[feature] = float((close > ema20) and (rsi14 > 55) and (vratio > 1.0))
                else:
                    result[feature] = None

            elif feature == "strong_uptrend":
                if all(k in indicator_dict and len(indicator_dict[k]) > data_idx for k in ["ema_20", "ema_50", "ema_200", "rsi_14"]):
                    ema20 = indicator_dict["ema_20"].iloc[data_idx]
                    ema50 = indicator_dict["ema_50"].iloc[data_idx]
                    ema200 = indicator_dict["ema_200"].iloc[data_idx]
                    rsi14 = indicator_dict["rsi_14"].iloc[data_idx]
                    result[feature] = float((ema20 > ema50) and (ema50 > ema200) and (rsi14 > 50))
                else:
                    result[feature] = None

            elif feature == "bullish_volume":
                if "vratio_20" in indicator_dict and len(indicator_dict["vratio_20"]) > data_idx:
                    vratio = indicator_dict["vratio_20"].iloc[data_idx]
                    close = df_norm["close"].iloc[data_idx]
                    open_ = df_norm["open"].iloc[data_idx]
                    result[feature] = float((vratio > 1.5) and (close > open_))
                else:
                    result[feature] = None

            # Forward returns (n-day returns computed from future close prices)
            elif feature == "return_5d":
                # BACKWARD-LOOKING: 5-day momentum (NOT future return)
                # Momentum = (close[t] - close[t-5]) / close[t-5]
                close_today = df_norm["close"].iloc[data_idx]
                if data_idx >= 5:
                    close_past = df_norm["close"].iloc[data_idx - 5]
                    result[feature] = float((close_today - close_past) / close_past)
                else:
                    result[feature] = None

            elif feature == "return_10d":
                # BACKWARD-LOOKING: 10-day momentum (NOT future return)
                close_today = df_norm["close"].iloc[data_idx]
                if data_idx >= 10:
                    close_past = df_norm["close"].iloc[data_idx - 10]
                    result[feature] = float((close_today - close_past) / close_past)
                else:
                    result[feature] = None

            elif feature == "return_20d":
                # BACKWARD-LOOKING: 20-day momentum (NOT future return)
                # NOTE: This is historical momentum, not a predictor of future returns
                # Use this ONLY as a feature, never as a target
                close_today = df_norm["close"].iloc[data_idx]
                if data_idx >= 20:
                    close_past = df_norm["close"].iloc[data_idx - 20]
                    result[feature] = float((close_today - close_past) / close_past)
                else:
                    result[feature] = None

            elif feature == "rel_return_20d":
                # Return_20d as a relative feature (same as return_20d in isolation)
                # In practice this would be normalized by market return, but without market data
                # we just compute 20-day return
                close_today = df_norm["close"].iloc[data_idx]
                if len(df_norm) > data_idx + 20:
                    close_future = df_norm["close"].iloc[data_idx + 20]
                    result[feature] = float((close_future - close_today) / close_today)
                else:
                    result[feature] = None

            elif feature == "volatility_20d":
                # 20-day rolling standard deviation of daily returns (backward-looking)
                if data_idx >= 20:
                    close_vals = df_norm["close"].iloc[max(0, data_idx-19):data_idx+1].values
                    if len(close_vals) >= 2:
                        daily_returns = np.diff(close_vals) / close_vals[:-1]
                        result[feature] = float(np.std(daily_returns))
                    else:
                        result[feature] = None
                else:
                    result[feature] = None

            elif feature == "return_vol_ratio":
                # Risk-adjusted momentum: past_momentum_20d / volatility_20d
                close_today = df_norm["close"].iloc[data_idx]
                if data_idx >= 20:
                    close_past = df_norm["close"].iloc[data_idx - 20]
                    ret_20d = (close_today - close_past) / close_past
                    # Compute volatility from past 20 days
                    close_vals = df_norm["close"].iloc[max(0, data_idx-19):data_idx+1].values
                    if len(close_vals) >= 2:
                        daily_returns = np.diff(close_vals) / close_vals[:-1]
                        vol = np.std(daily_returns)
                        if vol > 0:
                            result[feature] = float(ret_20d / vol)
                        else:
                            result[feature] = None
                    else:
                        result[feature] = None
                else:
                    result[feature] = None

            elif feature == "momentum_accel":
                # Momentum acceleration: return_5d - return_20d
                # (fast momentum - slow momentum = acceleration)
                # Both backward-looking, so no lookahead bias
                close_today = df_norm["close"].iloc[data_idx]
                ret_5d = None
                ret_20d = None

                if data_idx >= 5:
                    close_5d_past = df_norm["close"].iloc[data_idx - 5]
                    ret_5d = (close_today - close_5d_past) / close_5d_past

                if data_idx >= 20:
                    close_20d_past = df_norm["close"].iloc[data_idx - 20]
                    ret_20d = (close_today - close_20d_past) / close_20d_past

                if ret_5d is not None and ret_20d is not None:
                    result[feature] = float(ret_5d - ret_20d)
                else:
                    result[feature] = None

            elif feature == "momentum_accel_fast":
                # Ultra-fast momentum acceleration: return_5d - return_10d
                close_today = df_norm["close"].iloc[data_idx]
                ret_5d = None
                ret_10d = None

                if data_idx >= 5:
                    close_5d_past = df_norm["close"].iloc[data_idx - 5]
                    ret_5d = (close_today - close_5d_past) / close_5d_past

                if data_idx >= 10:
                    close_10d_past = df_norm["close"].iloc[data_idx - 10]
                    ret_10d = (close_today - close_10d_past) / close_10d_past

                if ret_5d is not None and ret_10d is not None:
                    result[feature] = float(ret_5d - ret_10d)
                else:
                    result[feature] = None

            elif feature == "breakout_20d":
                # Breakout: close relative to 20-day high
                close = df_norm["close"].iloc[data_idx]
                if data_idx >= 20:
                    close_vals = df_norm["close"].iloc[max(0, data_idx-19):data_idx+1].values
                    if len(close_vals) > 0:
                        max_close = np.max(close_vals)
                        if max_close > 0:
                            result[feature] = float(close / max_close)
                        else:
                            result[feature] = None
                    else:
                        result[feature] = None
                else:
                    result[feature] = None

            elif feature == "close_vs_open":
                # Intraday direction: (close - open) / close
                close = df_norm["close"].iloc[data_idx]
                open_ = df_norm["open"].iloc[data_idx]
                if close != 0:
                    result[feature] = float((close - open_) / close)
                else:
                    result[feature] = None

            elif feature == "zscore_return_20d":
                # Z-score of 20-day backward momentum (computed during cross-sectional normalization)
                # For now, just return the 20-day momentum
                close_today = df_norm["close"].iloc[data_idx]
                if data_idx >= 20:
                    close_past = df_norm["close"].iloc[data_idx - 20]
                    result[feature] = float((close_today - close_past) / close_past)
                else:
                    result[feature] = None

            elif feature == "rel_return_20d":
                # Relative 20-day momentum (without market index, just use past momentum)
                close_today = df_norm["close"].iloc[data_idx]
                if data_idx >= 20:
                    close_past = df_norm["close"].iloc[data_idx - 20]
                    result[feature] = float((close_today - close_past) / close_past)
                else:
                    result[feature] = None

            else:
                result[feature] = None

        except Exception:
            result[feature] = None

    return result
