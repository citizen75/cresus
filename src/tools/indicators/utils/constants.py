"""
Constants for indicators DSL engine.
"""

# Supported OHLCV columns (normalized to uppercase)
REQUIRED_COLUMNS = ["OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"]

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

    # Volatility indicators
    "atr": {"params": ["period"], "defaults": {"period": 14}},
    "bb": {"params": ["period", "std_dev"], "defaults": {"period": 20, "std_dev": 2}},
    "bollinger_bands": {"params": ["period", "std_dev"], "defaults": {"period": 20, "std_dev": 2}},
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

    # Support/Resistance
    "support": {"params": ["period"], "defaults": {"period": 14}},
    "resistance": {"params": ["period"], "defaults": {"period": 14}},
    "pivot": {"params": ["method"], "defaults": {"method": "classic"}},

    # Change indicators
    "chgpct": {"params": ["period"], "defaults": {"period": 1}},
    "chglog": {"params": ["period"], "defaults": {"period": 1}},

    # Core indicators
    "ha": {"params": [], "defaults": {}},  # Heikin Ashi
    "sha": {"params": ["period"], "defaults": {"period": 14}},  # Smooth Heikin Ashi
}

# Indicator return types
RETURN_SINGLE = {"rsi", "macd_line", "macd_signal", "macd_histogram", "adx", "obv", "mfi", "cmf", "vwap"}
RETURN_DICT = {"macd", "bb", "bollinger_bands", "dmi", "pivot", "ha", "sha"}  # Return multiple series

# Default periods if not specified
DEFAULT_FAST_PERIOD = 12
DEFAULT_SLOW_PERIOD = 26
DEFAULT_SIGNAL_PERIOD = 9
