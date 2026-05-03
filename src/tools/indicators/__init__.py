"""
Indicators DSL Engine - Calculate technical indicators from DSL formulas.

Main API:
    calculate(formulas, data, history_df=None) -> Dict[str, Series]

Example:
    >>> from src.tools.finance.indicators import calculate
    >>> results = calculate(["rsi_14", "ema_20"], data)
    >>> print(results["rsi_14"])
"""

from .indicators import (
    calculate,
    indicator,
    register_indicator,
    get_registered_indicator,
    list_available_indicators,
)
from .parser import parse_formula, validate_formula
from .validator import DataValidator
from .features import (
    FEATURE_REQUIREMENTS,
    infer_base_indicators,
    precompute_indicators,
    extract_features_from_indicators,
)
from .utils import (
    IndicatorError,
    InvalidFormulaError,
    MissingParameterError,
    ColumnError,
    InsufficientDataError,
    IndicatorNotFoundError,
)

__all__ = [
    # Main API
    "calculate",
    "indicator",
    "register_indicator",
    "get_registered_indicator",
    "list_available_indicators",
    # Parser
    "parse_formula",
    "validate_formula",
    # Validator
    "DataValidator",
    # Features
    "FEATURE_REQUIREMENTS",
    "infer_base_indicators",
    "precompute_indicators",
    "extract_features_from_indicators",
    # Errors
    "IndicatorError",
    "InvalidFormulaError",
    "MissingParameterError",
    "ColumnError",
    "InsufficientDataError",
    "IndicatorNotFoundError",
]
