"""
Indicators DSL Engine - Main entry point for calculating technical indicators.

Usage:
    >>> import pandas as pd
    >>> from src.tools.finance.indicators import calculate
    >>>
    >>> data = pd.DataFrame({
    ...     'Open': [...],
    ...     'High': [...],
    ...     'Low': [...],
    ...     'Close': [...],
    ...     'Volume': [...]
    ... })
    >>>
    >>> # Calculate single indicator
    >>> rsi = calculate(["rsi_14"], data)
    >>> print(rsi["rsi_14"])
    >>>
    >>> # Calculate multiple indicators
    >>> results = calculate(["rsi_14", "ema_20", "sma_50"], data)
    >>> print(results.keys())  # dict_keys(['rsi_14', 'ema_20', 'sma_50'])
    >>>
    >>> # With historical lookback context
    >>> results = calculate(["bb_20_2"], data, history_df=historical_data)
"""

import pandas as pd
from typing import List, Dict, Optional, Any, Callable
from .parser import parse_formula
from .validator import DataValidator
from .utils.errors import (
    InvalidFormulaError,
    IndicatorNotFoundError,
    ColumnError,
    InsufficientDataError,
)
from .utils.constants import RETURN_DICT


# Registry mapping indicator names to implementations
_INDICATOR_REGISTRY: Dict[str, Callable] = {}


def register_indicator(name: str, func: Callable) -> None:
    """
    Register an indicator implementation.

    Args:
        name: Indicator name (e.g., "rsi", "ema", "bb")
        func: Indicator function that takes (data, **params) -> Series or Dict[str, Series]
    """
    _INDICATOR_REGISTRY[name] = func


def get_registered_indicator(name: str) -> Optional[Callable]:
    """Get a registered indicator function."""
    return _INDICATOR_REGISTRY.get(name)


def calculate(
    formulas: List[str],
    data: pd.DataFrame,
    history_df: Optional[pd.DataFrame] = None
) -> Dict[str, pd.Series]:
    """
    Calculate technical indicators from DSL formulas.

    Args:
        formulas: List of DSL formula strings
                 Examples: ["rsi_14", "ema_20", "bb_20_2", "macd_12_26_9"]
        data: OHLCV DataFrame with columns [open, high, low, close, volume]
        history_df: Optional historical OHLCV data for lookback context
                   Used to avoid reloading data when calculations need more history

    Returns:
        Dictionary mapping formula strings to calculated Series
        Examples:
            {"rsi_14": Series(...), "ema_20": Series(...)}

    Raises:
        InvalidFormulaError: If formula syntax is invalid
        ColumnError: If required OHLCV columns are missing
        InsufficientDataError: If data is empty or insufficient
        IndicatorNotFoundError: If indicator not implemented

    Example:
        >>> data = pd.read_csv("AAPL.csv")
        >>> results = calculate(["rsi_14", "ema_20", "sma_50"], data)
        >>> print(results["rsi_14"])
    """
    # Validate inputs
    if not formulas:
        raise InvalidFormulaError("Formulas list cannot be empty")

    if not isinstance(formulas, list):
        raise InvalidFormulaError("Formulas must be a list of strings")

    # Normalize and validate data
    DataValidator.validate_data(data, min_rows=2)
    data = DataValidator.normalize_data(data)

    # Normalize history_df if provided
    if history_df is not None:
        DataValidator.validate_data(history_df, min_rows=2)
        history_df = DataValidator.normalize_data(history_df)

    # Parse formulas and group by indicator
    formula_map = {}  # Maps formula_string -> (indicator_name, params)
    indicators_to_calc = {}  # Maps indicator_name -> params (to avoid duplicates)

    for formula in formulas:
        try:
            indicator_name, params = parse_formula(formula)
        except InvalidFormulaError as e:
            raise InvalidFormulaError(f"Invalid formula '{formula}': {str(e)}")

        formula_map[formula] = (indicator_name, params)

        # Track indicators to calculate (avoid duplicate calculations)
        # Remove __component__ from param_key since it doesn't affect calculation
        params_for_calc = {k: v for k, v in params.items() if k != '__component__'}
        param_key = tuple(sorted(params_for_calc.items()))
        indicator_key = (indicator_name, param_key)

        if indicator_key not in indicators_to_calc:
            indicators_to_calc[indicator_key] = (indicator_name, params_for_calc)

    # Calculate indicators
    calc_results = {}  # Maps (indicator_name, param_tuple) -> result (Series or Dict)
    for (indicator_name, param_tuple), (ind_name, params) in indicators_to_calc.items():
        try:
            result = _calculate_indicator(ind_name, data, history_df, **params)
            calc_results[(indicator_name, param_tuple)] = result
        except Exception as e:
            raise IndicatorNotFoundError(
                f"Error calculating {indicator_name} with params {params}: {str(e)}"
            )

    # Map results back to formula strings
    results = {}
    for formula, (indicator_name, params_orig) in formula_map.items():
        # Create a copy and extract component if present (for multi-return indicators)
        params = params_orig.copy()
        component = params.pop('__component__', None)

        param_key = tuple(sorted(params.items()))
        indicator_key = (indicator_name, param_key)

        calc_result = calc_results[indicator_key]

        # If indicator returns multiple Series (Dict), pick the right one
        if isinstance(calc_result, dict):
            # If component specified, use it to select from dict
            if component:
                # Try to find matching key: component, indicator_component, indicator_params_component
                possible_keys = [
                    component,
                    f"{indicator_name}_{component}",
                    f"bb_{component}",  # For Bollinger Bands
                    f"macd_{component}",  # For MACD
                    f"ha_{component}",  # For Heikin Ashi
                    f"sha_{component}",  # For Smooth Heikin Ashi
                ]
                found = False
                for key in possible_keys:
                    if key in calc_result:
                        results[formula] = calc_result[key]
                        found = True
                        break

                if not found:
                    # Fallback: try to match any key containing the component
                    for key in calc_result.keys():
                        if component in key:
                            results[formula] = calc_result[key]
                            found = True
                            break

                if not found:
                    raise IndicatorNotFoundError(
                        f"Component '{component}' not found in {indicator_name} result. "
                        f"Available: {list(calc_result.keys())}"
                    )
            # No component specified - try formula or indicator name match
            elif formula in calc_result:
                results[formula] = calc_result[formula]
            elif indicator_name in calc_result:
                results[formula] = calc_result[indicator_name]
            else:
                # Use first Series from dict
                results[formula] = next(iter(calc_result.values()))
        else:
            results[formula] = calc_result

    return results


def _calculate_indicator(
    indicator_name: str,
    data: pd.DataFrame,
    history_df: Optional[pd.DataFrame],
    **params: Any
) -> Any:
    """
    Calculate a single indicator.

    Args:
        indicator_name: Indicator name (e.g., "rsi", "ema")
        data: Current OHLCV data
        history_df: Optional historical data for lookback
        **params: Indicator parameters (e.g., period=14)

    Returns:
        Calculated result (Series or Dict[str, Series])

    Raises:
        IndicatorNotFoundError: If indicator not registered
    """
    indicator_func = get_registered_indicator(indicator_name)

    if indicator_func is None:
        raise IndicatorNotFoundError(f"Indicator '{indicator_name}' not implemented")

    # Call indicator function
    if history_df is not None:
        # Pass both current and historical data
        result = indicator_func(data, history_df=history_df, **params)
    else:
        result = indicator_func(data, **params)

    return result


def list_available_indicators() -> List[str]:
    """List all available indicators."""
    return sorted(_INDICATOR_REGISTRY.keys())


# ============================================================================
# Import and register all indicator implementations
# ============================================================================

def _register_all_indicators():
    """Import and register all indicator implementations."""
    # This will be called at module init to register all indicators
    # Indicators will be lazily imported to avoid circular dependencies

    try:
        # Momentum indicators
        from .momentum import rsi, macd, roc
        register_indicator("rsi", rsi.calculate)
        register_indicator("macd", macd.calculate)
        register_indicator("roc", roc.calculate)
    except ImportError:
        pass  # Indicator not yet implemented

    try:
        # Trend indicators
        from .trend import ema, sma, adx
        register_indicator("ema", ema.calculate)
        register_indicator("sma", sma.calculate)
        register_indicator("adx", adx.calculate)
    except ImportError:
        pass

    try:
        # Volatility indicators
        from .volatility import atr, bb, parkinson, rogers_satchell
        register_indicator("atr", atr.calculate)
        register_indicator("bb", bb.calculate)
        register_indicator("bollinger_bands", bb.calculate)
        register_indicator("parkinson", parkinson.calculate)
        register_indicator("rs", rogers_satchell.calculate)
    except ImportError:
        pass

    try:
        # Volume indicators
        from .volume import obv, mfi, cmf, volume_ratio, vwap, volume_ma
        register_indicator("obv", obv.calculate)
        register_indicator("mfi", mfi.calculate)
        register_indicator("cmf", cmf.calculate)
        register_indicator("vratio", volume_ratio.calculate)
        register_indicator("vwap", vwap.calculate)
        register_indicator("volume_sma_20", lambda df: volume_ma.calculate(df, period=20))
        # Backwards compatibility alias
        register_indicator("volume_20ma", lambda df: volume_ma.calculate(df, period=20))
    except ImportError:
        pass

    try:
        # Support/Resistance indicators
        from .support import levels, pivots
        register_indicator("support", levels.calculate)
        register_indicator("resistance", levels.calculate)
        register_indicator("pivot", pivots.calculate)
    except ImportError:
        pass

    try:
        # Change indicators
        from .change import change_pct, change_log
        register_indicator("chgpct", change_pct.calculate)
        register_indicator("chglog", change_log.calculate)
    except ImportError:
        pass

    try:
        # Core indicators
        from .core import heikin_ashi
        register_indicator("ha", heikin_ashi.calculate)
        register_indicator("sha", heikin_ashi.calculate_smooth)
    except ImportError:
        pass


def indicator(
    name: str,
    data: pd.DataFrame = None,
    history_df: Optional[pd.DataFrame] = None,
    **params: Any
) -> Optional[float]:
    """
    Compute a single technical indicator and return the latest value.

    This is a convenience wrapper around calculate() for computing a single indicator.

    Args:
        name: Indicator name with optional parameters
              Examples: "rsi_14", "ema_20", "sma_50", "bb_20_2"
        data: OHLCV DataFrame (required if not using history_df)
        history_df: Optional historical data for lookback context
        **params: Additional indicator parameters

    Returns:
        Latest indicator value (float) or None if calculation failed

    Example:
        >>> import pandas as pd
        >>> from src.tools.finance.indicators import indicator
        >>> df = pd.DataFrame({'close': [100, 101, 102], ...})
        >>> rsi_value = indicator("rsi_14", df)
        >>> ema_value = indicator("ema_20", df)
    """
    try:
        if data is None or data.empty:
            return None

        # Calculate the indicator
        results = calculate([name], data, history_df=history_df)

        # Return the latest value from the Series
        if name in results:
            series = results[name]
            if isinstance(series, pd.Series) and len(series) > 0:
                value = series.iloc[-1]
                # Handle NaN values
                if pd.isna(value):
                    return None
                return float(value)

        return None

    except Exception as e:
        # Silently return None on error (indicator may not be available)
        return None


# Register indicators on module import
_register_all_indicators()
