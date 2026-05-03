"""
Error classes for indicators DSL engine.
"""


class IndicatorError(Exception):
    """Base exception for indicator errors."""
    pass


class InvalidFormulaError(IndicatorError):
    """Raised when DSL formula syntax is invalid."""
    pass


class MissingParameterError(IndicatorError):
    """Raised when required parameters are missing from formula."""
    pass


class ColumnError(IndicatorError):
    """Raised when required OHLCV columns are missing."""
    pass


class InsufficientDataError(IndicatorError):
    """Raised when data is insufficient for calculation."""
    pass


class IndicatorNotFoundError(IndicatorError):
    """Raised when indicator implementation not found."""
    pass
