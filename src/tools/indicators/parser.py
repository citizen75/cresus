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

    @staticmethod
    def parse(formula: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse DSL formula into indicator name and parameters.

        Args:
            formula: DSL formula string (e.g., "rsi_14", "bb_20_2", "obv")

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

        indicator_name = match.group(1)
        param_str = match.group(2)

        # Validate indicator exists
        if indicator_name not in INDICATOR_PARAMS:
            raise InvalidFormulaError(f"Unknown indicator: {indicator_name}")

        # Parse parameters
        params = FormulaParser._parse_params(indicator_name, param_str)

        return indicator_name, params

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
