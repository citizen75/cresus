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

# Documentation: Indicator Registry
# ============================================================================
# The indicator registry maps indicator names to their implementation functions.
# Indicators are lazily loaded via register_indicators_for_formulas() which is
# called when calculate() is invoked, avoiding unnecessary imports.
#
# Registration Workflow:
#   1. User calls calculate(["rsi_14", "ema_20"], data)
#   2. Formulas are parsed to extract indicator names ["rsi", "ema"]
#   3. register_indicators_for_formulas() is called with these names
#   4. _register_indicator_modules() imports and registers only needed indicators
#   5. Each indicator's calculate() function is called with parsed parameters
#
# All indicator modules are in subdirectories:
#   - momentum/: rsi.py, macd.py, roc.py
#   - trend/: ema.py, sma.py, adx.py, hama.py, ema_chgpct.py
#   - volatility/: atr.py, bb*.py, parkinson.py, rogers_satchell.py
#   - volume/: ad.py, obv.py, mfi.py, cmf.py, vwap.py, volume_*.py
#   - support/: levels.py, pivots.py, extremes.py
#   - change/: change_pct.py, change_log.py
#   - core/: heikin_ashi.py, sha_*.py


def register_indicator(name: str, func: Callable) -> None:
    """
    Register an indicator implementation.

    Args:
        name: Indicator name (e.g., "rsi", "ema", "bb")
        func: Indicator function that takes (data, **params) -> Series or Dict[str, Series]

    Usage:
        >>> from .momentum import rsi
        >>> register_indicator("rsi", rsi.calculate)
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
    from loguru import logger

    # Validate inputs
    if not formulas:
        raise InvalidFormulaError("Formulas list cannot be empty")

    if not isinstance(formulas, list):
        raise InvalidFormulaError("Formulas must be a list of strings")

    # Normalize and validate data
    DataValidator.validate_data(data, min_rows=2)
    data = DataValidator.normalize_data(data)

    # Try to load cached indicators
    from .cache import IndicatorCache
    from loguru import logger

    ticker = None
    if "TICKER" in data.columns:
        ticker_col = data["TICKER"]
        if not ticker_col.empty:
            ticker = ticker_col.iloc[0]

    cached_indicators = {}
    if ticker:
        cache = IndicatorCache(ticker)
        cached_indicators = cache.get_cached_indicators(data)

    # Track original data order - system expects newest-first, but indicators need oldest-first
    was_reversed = False
    data_for_calc = data.copy()  # Work with a copy to avoid modifying input

    # Find date column (could be 'DATE', 'date', 'timestamp', etc.)
    date_col = None
    for col in data_for_calc.columns:
        col_lower = str(col).lower()
        if col_lower in ('date', 'timestamp', 'datetime'):
            date_col = col
            break

    if date_col:
        # Check if data is sorted newest-first (descending)
        if len(data_for_calc) > 1:
            first_date = pd.to_datetime(data_for_calc[date_col].iloc[0])
            last_date = pd.to_datetime(data_for_calc[date_col].iloc[-1])
            if first_date > last_date:
                # Data is newest-first, reverse for indicator calculation
                data_for_calc = data_for_calc.sort_values(date_col, ascending=True).reset_index(drop=True)
                was_reversed = True

    # Normalize history_df if provided
    if history_df is not None:
        DataValidator.validate_data(history_df, min_rows=2)
        history_df = DataValidator.normalize_data(history_df)
        # Ensure history is also sorted oldest-first for calculations
        date_col_hist = None
        for col in history_df.columns:
            col_lower = str(col).lower()
            if col_lower in ('date', 'timestamp', 'datetime'):
                date_col_hist = col
                break
        if date_col_hist:
            if len(history_df) > 1:
                first_date = pd.to_datetime(history_df[date_col_hist].iloc[0])
                last_date = pd.to_datetime(history_df[date_col_hist].iloc[-1])
                if first_date > last_date:
                    history_df = history_df.sort_values(date_col_hist, ascending=True).reset_index(drop=True)

    # Register needed indicators
    register_indicators_for_formulas(formulas)

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

    # Calculate indicators (skip cached ones)
    calc_results = {}  # Maps (indicator_name, param_tuple) -> result (Series or Dict)
    newly_calculated = {}  # Track newly calculated indicators for caching

    for (indicator_name, param_tuple), (ind_name, params) in indicators_to_calc.items():
        # Check if this indicator is already cached. Belt-and-suspenders length
        # check alongside the cache's own hash validation: a cached Series whose
        # length doesn't match the current data is stale regardless of why, and
        # must never be merged onto a differently-sized DataFrame downstream.
        if ind_name in cached_indicators and len(cached_indicators[ind_name]) == len(data):
            calc_results[(indicator_name, param_tuple)] = cached_indicators[ind_name]
            continue

        try:
            result = _calculate_indicator(ind_name, data_for_calc, history_df, **params)
            calc_results[(indicator_name, param_tuple)] = result

            # If result is a dict (multi-return indicator), flatten it for caching
            if isinstance(result, dict):
                for key, val in result.items():
                    if isinstance(val, pd.Series):
                        newly_calculated[key] = val
            else:
                newly_calculated[ind_name] = result
        except Exception as e:
            raise IndicatorNotFoundError(
                f"Error calculating {indicator_name} with params {params}: {str(e)}"
            )

    # Save newly calculated indicators to cache
    if newly_calculated and ticker:
        cache = IndicatorCache(ticker)
        cache.save_indicators(newly_calculated, data)

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
                period = params.get("period", "")
                possible_keys = [
                    component,
                    f"{indicator_name}_{period}_{component}" if period else None,
                    f"{indicator_name}_{component}",
                    f"bb_{period}_{component}" if period else None,  # For Bollinger Bands with period
                    f"macd_{component}",  # For MACD
                    f"ha_{component}",  # For Heikin Ashi
                    f"sha_{component}",  # For Smooth Heikin Ashi
                ]
                possible_keys = [k for k in possible_keys if k]
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
            # No component specified - check if this is a multi-return indicator
            else:
                # For multi-return indicators (SHA, HA) without component specified,
                # return all related columns as separate entries
                prefix_candidates = [
                    f"{formula}_",  # For parameterized like 'sha_10' -> 'sha_10_*'
                    f"{indicator_name}_",  # For indicators like 'sha' -> 'sha_*'
                ]

                matched_keys = []
                for prefix in prefix_candidates:
                    matched_keys = [k for k in calc_result.keys() if k.startswith(prefix)]
                    if matched_keys:
                        break

                # If we found multiple keys with the same prefix, add all of them
                if matched_keys and len(matched_keys) > 1:
                    for key in matched_keys:
                        results[key] = calc_result[key]
                elif formula in calc_result:
                    # Single formula match
                    results[formula] = calc_result[formula]
                elif indicator_name in calc_result:
                    # Indicator name match
                    results[formula] = calc_result[indicator_name]
                else:
                    # Use first Series from dict as fallback
                    results[formula] = next(iter(calc_result.values()))
        else:
            results[formula] = calc_result

    # If we reversed data for calculation, reverse indicator results back to newest-first order
    if was_reversed:
        for key in results:
            if isinstance(results[key], pd.Series):
                results[key] = results[key].reset_index(drop=True).iloc[::-1].reset_index(drop=True)

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
        from .trend import ema, sma, adx, hama, ema_chgpct
        register_indicator("ema", ema.calculate)
        register_indicator("sma", sma.calculate)
        register_indicator("adx", adx.calculate)
        register_indicator("hama", hama.calculate)
        register_indicator("ema_chgpct", ema_chgpct.calculate)
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
        from .volume import ad, obv, mfi, cmf, volume_ratio, vwap, volume_ma, dv_up_volume, dv_down_volume
        register_indicator("ad", ad.calculate)
        register_indicator("obv", obv.calculate)
        register_indicator("mfi", mfi.calculate)
        register_indicator("cmf", cmf.calculate)
        register_indicator("vratio", volume_ratio.calculate)
        register_indicator("vwap", vwap.calculate)
        register_indicator("volume_sma_20", lambda df: volume_ma.calculate(df, period=20))
        register_indicator("dv_up_volume", dv_up_volume.calculate)
        register_indicator("dv_down_volume", dv_down_volume.calculate)

    except ImportError:
        pass

    try:
        # Support/Resistance indicators
        from .support import levels, pivots, extremes
        register_indicator("support", levels.calculate)
        register_indicator("resistance", levels.calculate)
        register_indicator("pivot", pivots.calculate)
        register_indicator("lowest", extremes.calculate_lowest)
        register_indicator("highest", extremes.calculate_highest)
    except ImportError:
        pass

    try:
        # Change indicators
        from .change import change_pct, change_log
        register_indicator("chgpct", change_pct.calculate)
        register_indicator("change_pct", change_pct.calculate)
        register_indicator("chglog", change_log.calculate)
    except ImportError:
        pass

    try:
        # Core indicators
        from .core import heikin_ashi, sha_green, sha_red, sha_up, sha_down
        register_indicator("ha", heikin_ashi.calculate)
        register_indicator("sha", heikin_ashi.calculate_smooth)
        register_indicator("sha_green", sha_green.calculate)
        register_indicator("sha_red", sha_red.calculate)
        register_indicator("sha_up", sha_up.calculate)
        register_indicator("sha_down", sha_down.calculate)
    except ImportError:
        pass


def register_indicators_for_formulas(formulas: List[str]) -> None:
	"""Dynamically register only the indicators needed for specific formulas.
	
	Parses the given indicator formulas and registers only the required indicators.
	This is more efficient than registering all indicators upfront.
	
	Args:
		formulas: List of indicator formulas (e.g., ["rsi_14", "ema_20", "bb_20_2"])
	"""
	if not formulas:
		return
	
	# Extract unique indicator names from formulas
	indicators_needed = set()
	for formula in formulas:
		try:
			indicator_name, _ = parse_formula(formula)
			indicators_needed.add(indicator_name)
		except:
			# If formula parsing fails, skip it
			pass
	
	# Map of indicator names to their registration logic
	_register_indicator_modules(indicators_needed)


def _register_indicator_modules(indicator_names: set) -> None:
	"""Register only the requested indicator modules.
	
	Args:
		indicator_names: Set of indicator names to register (e.g., {"rsi", "ema", "bb"})
	"""
	if not indicator_names:
		return
	
	# Momentum indicators
	if any(ind in indicator_names for ind in ["rsi", "macd", "roc", "mom"]):
		try:
			from .momentum import rsi, macd, roc
			if "rsi" in indicator_names:
				register_indicator("rsi", rsi.calculate)
			if "macd" in indicator_names:
				register_indicator("macd", macd.calculate)
			if "roc" in indicator_names:
				register_indicator("roc", roc.calculate)
		except ImportError:
			pass
	
	# Trend indicators
	if any(ind in indicator_names for ind in ["ema", "sma", "adx", "dmi", "hama", "ema_chgpct"]):
		try:
			from .trend import ema, sma, adx, hama, ema_chgpct
			if "ema" in indicator_names:
				register_indicator("ema", ema.calculate)
			if "sma" in indicator_names:
				register_indicator("sma", sma.calculate)
			if "adx" in indicator_names or "dmi" in indicator_names:
				register_indicator("adx", adx.calculate)
			if "hama" in indicator_names:
				register_indicator("hama", hama.calculate)
			if "ema_chgpct" in indicator_names:
				register_indicator("ema_chgpct", ema_chgpct.calculate)
		except ImportError:
			pass
	
	# Volatility indicators
	if any(ind in indicator_names for ind in ["atr", "bb", "bollinger_bands", "parkinson", "rs"]):
		try:
			from .volatility import atr, bb, parkinson, rogers_satchell
			if "atr" in indicator_names:
				register_indicator("atr", atr.calculate)
			if "bb" in indicator_names or "bollinger_bands" in indicator_names:
				register_indicator("bb", bb.calculate)
				register_indicator("bollinger_bands", bb.calculate)
			if "parkinson" in indicator_names:
				register_indicator("parkinson", parkinson.calculate)
			if "rs" in indicator_names:
				register_indicator("rs", rogers_satchell.calculate)
		except ImportError:
			pass
	
	# Volume indicators
	if any(ind in indicator_names for ind in ["ad", "obv", "mfi", "cmf", "vratio", "vwap", "volume_sma", "dv_up_volume", "dv_down_volume"]):
		try:
			from .volume import ad, obv, mfi, cmf, volume_ratio, vwap, volume_ma, dv_up_volume, dv_down_volume
			if "ad" in indicator_names:
				register_indicator("ad", ad.calculate)
			if "obv" in indicator_names:
				register_indicator("obv", obv.calculate)
			if "mfi" in indicator_names:
				register_indicator("mfi", mfi.calculate)
			if "cmf" in indicator_names:
				register_indicator("cmf", cmf.calculate)
			if "vratio" in indicator_names:
				register_indicator("vratio", volume_ratio.calculate)
			if "vwap" in indicator_names:
				register_indicator("vwap", vwap.calculate)
			if any(ind in indicator_names for ind in ["volume_sma_20", "volume_20ma"]):
				register_indicator("volume_sma_20", lambda df: volume_ma.calculate(df, period=20))
				register_indicator("volume_20ma", lambda df: volume_ma.calculate(df, period=20))
			if "dv_up_volume" in indicator_names:
				register_indicator("dv_up_volume", dv_up_volume.calculate)
			if "dv_down_volume" in indicator_names:
				register_indicator("dv_down_volume", dv_down_volume.calculate)
		except ImportError:
			pass
	
	# Support/Resistance indicators
	if any(ind in indicator_names for ind in ["support", "resistance", "pivot", "lowest", "highest"]):
		try:
			from .support import levels, pivots, extremes
			if "support" in indicator_names:
				register_indicator("support", levels.calculate)
			if "resistance" in indicator_names:
				register_indicator("resistance", levels.calculate)
			if "pivot" in indicator_names:
				register_indicator("pivot", pivots.calculate)
			if "lowest" in indicator_names:
				register_indicator("lowest", extremes.calculate_lowest)
			if "highest" in indicator_names:
				register_indicator("highest", extremes.calculate_highest)
		except ImportError:
			pass
	
	# Change indicators
	if any(ind in indicator_names for ind in ["chgpct", "change_pct", "chglog"]):
		try:
			from .change import change_pct, change_log
			if "chgpct" in indicator_names:
				register_indicator("chgpct", change_pct.calculate)
			if "change_pct" in indicator_names:
				register_indicator("change_pct", change_pct.calculate)
			if "chglog" in indicator_names:
				register_indicator("chglog", change_log.calculate)
		except ImportError:
			pass
	
	# Core indicators
	if any(ind in indicator_names for ind in ["ha", "sha", "sha_green", "sha_red", "sha_up", "sha_down"]):
		try:
			from .core import heikin_ashi, sha_green, sha_red, sha_up, sha_down
			if "ha" in indicator_names:
				register_indicator("ha", heikin_ashi.calculate)
			if "sha" in indicator_names:
				register_indicator("sha", heikin_ashi.calculate_smooth)
			if "sha_green" in indicator_names:
				register_indicator("sha_green", sha_green.calculate)
			if "sha_red" in indicator_names:
				register_indicator("sha_red", sha_red.calculate)
			if "sha_up" in indicator_names:
				register_indicator("sha_up", sha_up.calculate)
			if "sha_down" in indicator_names:
				register_indicator("sha_down", sha_down.calculate)
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
