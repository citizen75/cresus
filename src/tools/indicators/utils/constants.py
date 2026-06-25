"""
Constants for indicators DSL engine.

Magic Numbers & Thresholds:
  - ADX_STRONG_DOWN_THRESHOLD = 20: ADX below this indicates weak downtrend
  - ADX_STRONG_UP_THRESHOLD = 25: ADX above this indicates strong uptrend
  - SHA_WICK_TOLERANCE = 0.005: 0.5% of price for no-wick detection
  - PARKINSON_CONSTANT = 1/(4*ln(2)) ≈ 0.3607: Mathematical constant in formula
  - MFI_OVERBOUGHT = 80: MFI threshold for overbought condition
  - MFI_OVERSOLD = 20: MFI threshold for oversold condition
  - RSI_OVERBOUGHT = 70: RSI threshold for overbought condition
  - RSI_OVERSOLD = 30: RSI threshold for oversold condition
"""

# Supported OHLCV columns (normalized to uppercase)
REQUIRED_COLUMNS = ["OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"]

# ============================================================================
# ADX Thresholds (Average Directional Index)
# ============================================================================
ADX_WEAK_DOWN_THRESHOLD = 20     # ADX < 20: Weak downtrend
ADX_STRONG_UP_THRESHOLD = 25     # ADX > 25: Strong uptrend

# ============================================================================
# SHA (Smooth Heikin Ashi) Wick Tolerance
# ============================================================================
SHA_WICK_TOLERANCE = 0.005       # 0.5% of price for detecting "no wick" condition

# ============================================================================
# Parkinson Volatility Constant
# ============================================================================
# c = 1 / (4 * ln(2)) ≈ 0.3607
# Used in formula: Parkinson = sqrt(c / n * sum(ln(H/L)^2))
PARKINSON_CONSTANT = 1 / (4 * __import__('math').log(2))

# ============================================================================
# RSI Thresholds (Relative Strength Index)
# ============================================================================
RSI_OVERBOUGHT = 70              # RSI > 70: Overbought condition
RSI_OVERSOLD = 30                # RSI < 30: Oversold condition

# ============================================================================
# MFI Thresholds (Money Flow Index)
# ============================================================================
MFI_OVERBOUGHT = 80              # MFI > 80: Overbought condition
MFI_OVERSOLD = 20                # MFI < 20: Oversold condition

# Indicator categories and their parameters
INDICATOR_PARAMS = {
    # Momentum indicators
    "rsi": {"params": ["period"], "defaults": {"period": 14}},
    "macd": {"params": ["fast", "slow", "signal"], "defaults": {"fast": 12, "slow": 26, "signal": 9}},
    "roc": {"params": ["period"], "defaults": {"period": 12}},
    "mom": {"params": ["period"], "defaults": {"period": 12}},

    # Trend indicators
    "ema": {"params": ["period"], "defaults": {"period": 20}},
    "sma": {"params": ["period"], "defaults": {"period": 20}},
    "adx": {"params": ["period"], "defaults": {"period": 14}},
    "dmi": {"params": ["period"], "defaults": {"period": 14}},
    "hama": {
        "params": ["length_open", "length_close", "ema_line"],
        "defaults": {"length_open": 25, "length_close": 20, "ema_line": 55},
        "flexible": True,  # Allow 1, 2, or 3 params - parser handles mapping
    },

    # Volatility indicators
    "atr": {"params": ["period"], "defaults": {"period": 14}},
    "bb": {"params": ["period", "std_dev"], "defaults": {"period": 20, "std_dev": 2}},
    "bollinger_bands": {"params": ["period", "std_dev"], "defaults": {"period": 20, "std_dev": 2}},
    "dc": {"params": ["period"], "defaults": {"period": 20}},  # Donchian Channel
    "parkinson": {"params": ["period"], "defaults": {"period": 14}},
    "garman_klass": {"params": ["period"], "defaults": {"period": 14}},
    "rs": {"params": ["period"], "defaults": {"period": 14}},  # Rogers-Satchell

    # Volume indicators
    "obv": {"params": [], "defaults": {}},
    "mfi": {"params": ["period"], "defaults": {"period": 14}},
    "cmf": {"params": ["period"], "defaults": {"period": 20}},
    "vratio": {"params": ["period"], "defaults": {"period": 20}},
    "pvt": {"params": [], "defaults": {}},  # Price-Volume Trend
    "vwap": {"params": ["anchor"], "defaults": {"anchor": None}},  # Volume Weighted Average Price
    "dv_up_volume": {"params": [], "defaults": {}},  # Directional volume - up days
    "dv_down_volume": {"params": [], "defaults": {}},  # Directional volume - down days
    "volume_sma_20": {"params": [], "defaults": {}},  # Volume SMA (20-period hardcoded alias)
    "volume_20ma": {"params": [], "defaults": {}},  # Volume 20-period MA (alias)

    # Support/Resistance
    "support": {"params": ["period"], "defaults": {"period": 14}},
    "resistance": {"params": ["period"], "defaults": {"period": 14}},
    "pivot": {"params": ["method"], "defaults": {"method": "classic"}},
    "lowest": {"params": ["period"], "defaults": {"period": 14}},
    "highest": {"params": ["period"], "defaults": {"period": 14}},

    # Change indicators
    "chgpct": {"params": ["period"], "defaults": {"period": 1}},
    "chglog": {"params": ["period"], "defaults": {"period": 1}},

    # Compound trend-change indicators
    "ema_chgpct": {"params": ["ema_period", "change_period"], "defaults": {"ema_period": 20, "change_period": 5}},

    # Core indicators
    "ha": {"params": [], "defaults": {}},  # Heikin Ashi
    "sha": {"params": ["period"], "defaults": {"period": 14}},  # Smooth Heikin Ashi
    "sha_green": {"params": ["period"], "defaults": {"period": 14}},  # SHA bullish candle
    "sha_red": {"params": ["period"], "defaults": {"period": 14}},  # SHA bearish candle
    "sha_up": {"params": ["period"], "defaults": {"period": 14}},  # SHA bullish without bottom wick
    "sha_down": {"params": ["period"], "defaults": {"period": 14}},  # SHA bearish without top wick
}

# Indicator return types
RETURN_SINGLE = {"rsi", "macd_line", "macd_signal", "macd_histogram", "obv", "mfi", "cmf", "vwap"}
RETURN_DICT = {"macd", "bb", "bollinger_bands", "dc", "dmi", "pivot", "ha", "sha", "hama", "adx"}  # Return multiple series

# Default periods if not specified
DEFAULT_FAST_PERIOD = 12
DEFAULT_SLOW_PERIOD = 26
DEFAULT_SIGNAL_PERIOD = 9
