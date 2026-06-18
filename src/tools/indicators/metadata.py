"""
Indicator Metadata Registry

Provides centralized information about all indicators including:
- Category (momentum, trend, volatility, volume, support/resistance)
- Parameters and their defaults
- Return type (single Series vs Dict of Series)
- Valid output range
- Description and usage examples
"""

from typing import Dict, Any, Tuple, Optional, List

# Indicator metadata: name -> (category, return_type, params, min_value, max_value, description)
INDICATOR_META: Dict[str, Dict[str, Any]] = {
    # ========================================================================
    # MOMENTUM INDICATORS
    # ========================================================================
    "rsi": {
        "category": "momentum",
        "returns": "Series",
        "params": ["period"],
        "defaults": {"period": 14},
        "range": (0, 100),
        "description": "Relative Strength Index - Overbought/oversold momentum indicator",
        "examples": ["rsi_14", "rsi_7"],
        "thresholds": {"overbought": 70, "oversold": 30},
    },
    "macd": {
        "category": "momentum",
        "returns": "Dict",
        "params": ["fast", "slow", "signal"],
        "defaults": {"fast": 12, "slow": 26, "signal": 9},
        "range": (None, None),
        "components": ["macd", "signal", "histogram"],
        "description": "MACD - Trend following momentum indicator",
        "examples": ["macd_12_26_9", "macd_12_26_9_line", "macd_12_26_9_signal"],
    },
    "roc": {
        "category": "momentum",
        "returns": "Series",
        "params": ["period"],
        "defaults": {"period": 12},
        "range": (None, None),
        "description": "Rate of Change - Momentum oscillator",
        "examples": ["roc_12", "roc_20"],
    },

    # ========================================================================
    # TREND INDICATORS
    # ========================================================================
    "ema": {
        "category": "trend",
        "returns": "Series",
        "params": ["period"],
        "defaults": {"period": 20},
        "range": (None, None),
        "description": "Exponential Moving Average - Price following trend line",
        "examples": ["ema_20", "ema_50", "ema_200"],
    },
    "sma": {
        "category": "trend",
        "returns": "Series",
        "params": ["period"],
        "defaults": {"period": 20},
        "range": (None, None),
        "description": "Simple Moving Average - Price following trend line",
        "examples": ["sma_20", "sma_50", "sma_200"],
    },
    "adx": {
        "category": "trend",
        "returns": "Dict",
        "params": ["period"],
        "defaults": {"period": 14},
        "range": (0, 100),
        "components": ["adx", "force"],
        "description": "Average Directional Index - Trend strength indicator",
        "examples": ["adx_14", "adx_14_force"],
        "thresholds": {"weak_trend": 20, "strong_trend": 25},
    },
    "hama": {
        "category": "trend",
        "returns": "Dict",
        "params": ["length_open", "length_close", "ema_line"],
        "defaults": {"length_open": 25, "length_close": 20, "ema_line": 55},
        "range": (None, None),
        "components": ["open", "high", "low", "close", "trend"],
        "description": "Heikin-Ashi Moving Average (NST Version) - Smoothed OHLC values",
        "examples": ["hama_25_20_55"],
    },
    "ema_chgpct": {
        "category": "trend",
        "returns": "Series",
        "params": ["ema_period", "change_period"],
        "defaults": {"ema_period": 20, "change_period": 5},
        "range": (None, None),
        "description": "Percentage change of EMA over lookback period",
        "examples": ["ema_20_chgpct_5"],
    },

    # ========================================================================
    # VOLATILITY INDICATORS
    # ========================================================================
    "atr": {
        "category": "volatility",
        "returns": "Series",
        "params": ["period"],
        "defaults": {"period": 14},
        "range": (0, None),
        "description": "Average True Range - Volatility measurement",
        "examples": ["atr_14"],
    },
    "bb": {
        "category": "volatility",
        "returns": "Dict",
        "params": ["period", "std_dev"],
        "defaults": {"period": 20, "std_dev": 2},
        "range": (None, None),
        "components": ["upper", "middle", "lower"],
        "description": "Bollinger Bands - Volatility and support/resistance",
        "examples": ["bb_20_2", "bb_20_2_upper", "bb_20_2_middle"],
    },
    "parkinson": {
        "category": "volatility",
        "returns": "Series",
        "params": ["period"],
        "defaults": {"period": 14},
        "range": (0, None),
        "description": "Parkinson Volatility Estimator - Range-based volatility",
        "examples": ["parkinson_14"],
    },
    "rs": {
        "category": "volatility",
        "returns": "Series",
        "params": ["period"],
        "defaults": {"period": 14},
        "range": (0, None),
        "description": "Rogers-Satchell Volatility Estimator - Gap-aware volatility",
        "examples": ["rs_14"],
    },

    # ========================================================================
    # VOLUME INDICATORS
    # ========================================================================
    "ad": {
        "category": "volume",
        "returns": "Series",
        "params": [],
        "defaults": {},
        "range": (None, None),
        "description": "Accumulation/Distribution Line - Volume momentum",
        "examples": ["ad"],
    },
    "obv": {
        "category": "volume",
        "returns": "Series",
        "params": [],
        "defaults": {},
        "range": (None, None),
        "description": "On-Balance Volume - Cumulative volume indicator",
        "examples": ["obv"],
    },
    "mfi": {
        "category": "volume",
        "returns": "Series",
        "params": ["period"],
        "defaults": {"period": 14},
        "range": (0, 100),
        "description": "Money Flow Index - Volume-weighted RSI",
        "examples": ["mfi_14"],
        "thresholds": {"overbought": 80, "oversold": 20},
    },
    "cmf": {
        "category": "volume",
        "returns": "Series",
        "params": ["period"],
        "defaults": {"period": 20},
        "range": (-1, 1),
        "description": "Chaikin Money Flow - Accumulation/distribution oscillator",
        "examples": ["cmf_20"],
    },
    "vwap": {
        "category": "volume",
        "returns": "Series",
        "params": ["anchor"],
        "defaults": {"anchor": None},
        "range": (None, None),
        "description": "Volume Weighted Average Price - Intraday fair value",
        "examples": ["vwap", "vwap_10", "vwap_2024-01-15"],
    },
    "dv_up_volume": {
        "category": "volume",
        "returns": "Series",
        "params": [],
        "defaults": {},
        "range": (0, None),
        "description": "Directional Volume Up - Volume on days where Close > Open",
        "examples": ["dv_up_volume"],
    },
    "dv_down_volume": {
        "category": "volume",
        "returns": "Series",
        "params": [],
        "defaults": {},
        "range": (0, None),
        "description": "Directional Volume Down - Volume on days where Close < Open",
        "examples": ["dv_down_volume"],
    },

    # ========================================================================
    # CORE INDICATORS
    # ========================================================================
    "ha": {
        "category": "core",
        "returns": "Dict",
        "params": [],
        "defaults": {},
        "range": (None, None),
        "components": ["open", "high", "low", "close"],
        "description": "Heikin-Ashi Candles - Smoothed OHLC",
        "examples": ["ha"],
    },
    "sha": {
        "category": "core",
        "returns": "Dict",
        "params": ["period"],
        "defaults": {"period": 14},
        "range": (None, None),
        "components": ["open", "high", "low", "close"],
        "description": "Smooth Heikin-Ashi - EMA-smoothed OHLC",
        "examples": ["sha_14", "sha_14_open"],
    },
    "sha_green": {
        "category": "core",
        "returns": "Series",
        "params": ["period"],
        "defaults": {"period": 14},
        "range": (0, 1),
        "description": "SHA Bullish Candle - Binary indicator (1=bullish, 0=other)",
        "examples": ["sha_14_green"],
    },
    "sha_red": {
        "category": "core",
        "returns": "Series",
        "params": ["period"],
        "defaults": {"period": 14},
        "range": (0, 1),
        "description": "SHA Bearish Candle - Binary indicator (1=bearish, 0=other)",
        "examples": ["sha_14_red"],
    },
    "sha_up": {
        "category": "core",
        "returns": "Series",
        "params": ["period"],
        "defaults": {"period": 14},
        "range": (0, 1),
        "description": "SHA Bullish Without Bottom Wick - Binary indicator",
        "examples": ["sha_14_up"],
    },
    "sha_down": {
        "category": "core",
        "returns": "Series",
        "params": ["period"],
        "defaults": {"period": 14},
        "range": (0, 1),
        "description": "SHA Bearish Without Top Wick - Binary indicator",
        "examples": ["sha_14_down"],
    },

    # ========================================================================
    # CHANGE INDICATORS
    # ========================================================================
    "chgpct": {
        "category": "change",
        "returns": "Series",
        "params": ["period"],
        "defaults": {"period": 1},
        "range": (None, None),
        "description": "Percentage Change - ROC as percentage",
        "examples": ["chgpct_1", "chgpct_5"],
    },
    "change_pct": {
        "category": "change",
        "returns": "Series",
        "params": ["period"],
        "defaults": {"period": 1},
        "range": (None, None),
        "description": "Percentage Change - Alias for chgpct",
        "examples": ["change_pct_1", "change_pct_5"],
    },
    "chglog": {
        "category": "change",
        "returns": "Series",
        "params": ["period"],
        "defaults": {"period": 1},
        "range": (None, None),
        "description": "Log Change - Logarithmic price change",
        "examples": ["chglog_1", "chglog_5"],
    },
}


def get_indicator_meta(name: str) -> Optional[Dict[str, Any]]:
    """Get metadata for a specific indicator.

    Args:
        name: Indicator name (e.g., "rsi", "ema", "bb")

    Returns:
        Indicator metadata dict or None if not found
    """
    return INDICATOR_META.get(name)


def get_indicator_by_category(category: str) -> List[str]:
    """Get all indicators in a specific category.

    Args:
        category: Category name (e.g., "momentum", "trend", "volatility")

    Returns:
        List of indicator names
    """
    return [name for name, meta in INDICATOR_META.items() if meta.get("category") == category]


def list_categories() -> List[str]:
    """List all available indicator categories."""
    categories = set()
    for meta in INDICATOR_META.values():
        cat = meta.get("category")
        if cat:
            categories.add(cat)
    return sorted(categories)


def validate_indicator_exists(name: str) -> bool:
    """Check if an indicator is registered in metadata.

    Args:
        name: Indicator name

    Returns:
        True if indicator exists, False otherwise
    """
    return name in INDICATOR_META
