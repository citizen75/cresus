"""
DSL Formula Parser - Extract indicator names and parameters from DSL syntax.

Syntax examples:
  rsi_14              -> indicator="rsi", params={"period": 14}
  ema_20              -> indicator="ema", params={"period": 20}
  bb_20_2             -> indicator="bb", params={"period": 20, "std_dev": 2}
  macd_12_26_9        -> indicator="macd", params={"fast": 12, "slow": 26, "signal": 9}
  obv                 -> indicator="obv", params={}
  pivot_classic       -> indicator="pivot", params={"method": "classic"}
"""

import re
from typing import Tuple, Dict, Any, Optional
from .utils.errors import InvalidFormulaError
from .utils.constants import INDICATOR_PARAMS


class FormulaParser:
    """Parse DSL formulas into indicator names and parameters."""

    # Regex pattern for DSL formula: indicator_param1_param2_...
    PATTERN = r'^([a-z_]+?)(?:_(.+))?$'

    # Known component suffixes for multi-return indicators
    COMPONENT_SUFFIXES = {
        'upper', 'lower', 'middle',  # Bollinger Bands
        'line', 'signal', 'histogram',  # MACD
        'plus', 'minus',  # DMI
        'open', 'high', 'low', 'close',  # Heikin Ashi, Smooth Heikin Ashi
    }

    @staticmethod
    def parse(formula: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse DSL formula into indicator name and parameters.

        Args:
            formula: DSL formula string (e.g., "rsi_14", "bb_20_2", "obv", "bb_20_2_lower", "bollinger_bands_20_2_lower")

        Returns:
            Tuple of (indicator_name, parameters_dict)

        Raises:
            InvalidFormulaError: If formula syntax is invalid or parameters missing
        """
        if not formula or not isinstance(formula, str):
            raise InvalidFormulaError("Formula must be a non-empty string")

        # Normalize to lowercase
        formula = formula.strip().lower()

        # Extract indicator name and parameter string
        match = re.match(FormulaParser.PATTERN, formula)
        if not match:
            raise InvalidFormulaError(f"Invalid formula syntax: {formula}")

        indicator_name_guess = match.group(1)
        param_str = match.group(2)

        # Check for component suffix (e.g., _lower, _upper, _signal)
        component = FormulaParser._extract_component(param_str)
        if component:
            # Remove component from param_str
            param_str = param_str[:-len(component)-1]  # -1 for underscore

        # Find the actual indicator name by trying progressively
        # For multi-word indicators like "bollinger_bands", we need to check
        # against the defined indicators in INDICATOR_PARAMS
        indicator_name, remaining_param_str = FormulaParser._find_indicator_name(indicator_name_guess, param_str)

        if not indicator_name:
            raise InvalidFormulaError(f"Unknown indicator: {indicator_name_guess}")

        # Parse parameters (use remaining_param_str to skip the consumed indicator name parts)
        params = FormulaParser._parse_params(indicator_name, remaining_param_str)

        # Store component suffix in params if present
        if component:
            params['__component__'] = component

        return indicator_name, params

    @staticmethod
    def _find_indicator_name(indicator_guess: str, param_str: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Find the actual indicator name by checking against defined indicators.

        Handles multi-word indicators like "bollinger_bands" by trying to match
        the longest possible indicator name in the guess.

        Args:
            indicator_guess: Initial indicator name guess (e.g., "bollinger")
            param_str: Parameter string (e.g., "bands_20_2" or "20_2")

        Returns:
            Tuple of (matched_indicator_name, remaining_param_str), or (None, None) if not found
        """
        # First, try the guess directly
        if indicator_guess in INDICATOR_PARAMS:
            return indicator_guess, param_str

        # If guess not found and param_str exists, try progressively longer indicators
        # by moving parts from param_str to indicator_name
        if param_str:
            parts = param_str.split('_')
            # Try combining indicator_guess with param parts to find multi-word indicator
            # Go in reverse order to find longest match first
            for i in range(len(parts) - 1, -1, -1):
                # Try: indicator_guess_part1, indicator_guess_part1_part2, etc.
                potential_name = indicator_guess + '_' + '_'.join(parts[:i+1])
                if potential_name in INDICATOR_PARAMS:
                    # Return the matched name and remaining params
                    remaining_params = '_'.join(parts[i+1:]) if i+1 < len(parts) else None
                    return potential_name, remaining_params

        return None, None

    @staticmethod
    def _extract_component(param_str: Optional[str]) -> Optional[str]:
        """
        Extract component suffix from parameter string.

        Checks if param_str ends with a known component suffix (e.g., _lower, _upper, _signal).

        Args:
            param_str: Parameter string (e.g., "20_2_lower")

        Returns:
            Component name if found (e.g., "lower"), otherwise None
        """
        if not param_str:
            return None

        # Get the last part after the final underscore
        parts = param_str.split('_')
        if not parts:
            return None

        last_part = parts[-1]
        if last_part in FormulaParser.COMPONENT_SUFFIXES:
            return last_part

        return None

    @staticmethod
    def _parse_params(
        indicator_name: str,
        param_str: Optional[str]
    ) -> Dict[str, Any]:
        """
        Parse parameter string into dictionary.

        Args:
            indicator_name: Indicator name to look up parameter order
            param_str: Parameter string (e.g., "14", "20_2", "12_26_9", "classic")

        Returns:
            Dictionary of parameters

        Raises:
            InvalidFormulaError: If parameters invalid or missing required params
        """
        indicator_config = INDICATOR_PARAMS.get(indicator_name, {})
        param_names = indicator_config.get("params", [])
        defaults = indicator_config.get("defaults", {})

        # If no parameters expected, return defaults
        if not param_names:
            return defaults.copy()

        # If no parameter string provided, use defaults
        if not param_str:
            return defaults.copy()

        # Split parameter string
        parts = param_str.split("_")

        # Validate count
        if len(parts) > len(param_names):
            raise InvalidFormulaError(
                f"Too many parameters for {indicator_name}: "
                f"expected {len(param_names)}, got {len(parts)}"
            )

        # Build parameters dictionary
        params = defaults.copy()
        for i, part in enumerate(parts):
            param_name = param_names[i]

            # Try to parse as number, otherwise keep as string
            try:
                # Try int first
                if "." not in part:
                    params[param_name] = int(part)
                else:
                    params[param_name] = float(part)
            except ValueError:
                # Keep as string (e.g., "classic" for pivot method)
                params[param_name] = part

        return params

    @staticmethod
    def validate(formula: str) -> Tuple[bool, str]:
        """
        Validate formula syntax without parsing.

        Args:
            formula: DSL formula string

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            FormulaParser.parse(formula)
            return True, ""
        except InvalidFormulaError as e:
            return False, str(e)


def parse_formula(formula: str) -> Tuple[str, Dict[str, Any]]:
    """
    Convenience function to parse a DSL formula.

    Args:
        formula: DSL formula string (e.g., "rsi_14")

    Returns:
        Tuple of (indicator_name, parameters)

    Raises:
        InvalidFormulaError: If formula is invalid

    Example:
        >>> indicator, params = parse_formula("rsi_14")
        >>> print(indicator)  # "rsi"
        >>> print(params)     # {"period": 14}

        >>> indicator, params = parse_formula("bb_20_2")
        >>> print(indicator)  # "bb"
        >>> print(params)     # {"period": 20, "std_dev": 2}
    """
    return FormulaParser.parse(formula)


def validate_formula(formula: str) -> bool:
    """
    Check if a formula is valid.

    Args:
        formula: DSL formula string

    Returns:
        True if valid, False otherwise
    """
    is_valid, _ = FormulaParser.validate(formula)
    return is_valid
