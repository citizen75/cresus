"""Extract indicators and columns from formula strings.

Utility functions to analyze formula dependencies and extract references
to indicators, columns, and variables.
"""

import re
from typing import Set, List, Dict, Union
from .dsl_parser import Lexer, Parser, Indicator, Variable, BinaryOp, UnaryOp, Literal


def extract_indicators(formula: str) -> Set[str]:
    """Extract all indicator/column names from a formula.

    Parses a formula and returns all referenced indicators and columns,
    including those with shift notation (e.g., "rsi_14[0]", "close[-1]").

    Args:
        formula: Formula string (DSL or traditional syntax)

    Returns:
        Set of unique indicator/column names (without shift notation)

    Examples:
        >>> extract_indicators("rsi_14 > 50 && ema_20 < close")
        {'rsi_14', 'ema_20', 'close'}

        >>> extract_indicators("rsi_14[0] > 50 || rsi_14[-1] < 40")
        {'rsi_14'}

        >>> extract_indicators("data['close'] * 1.05")
        {'close'}
    """
    if not formula or not isinstance(formula, str):
        return set()

    try:
        # Parse the formula to AST
        lexer = Lexer(formula)
        parser = Parser(lexer.get_tokens())
        ast = parser.parse()

        # Extract indicators from AST
        return _extract_from_ast(ast)

    except Exception:
        # If parsing fails, try regex extraction as fallback
        return _extract_by_regex(formula)


def extract_indicators_from_formulas(formulas: Union[List[str], Dict[str, str]]) -> Set[str]:
    """Extract all indicators from multiple formulas.

    Args:
        formulas: List of formula strings or dict of {name: formula}

    Returns:
        Set of all unique indicators referenced in all formulas

    Examples:
        >>> formulas = [
        ...     "rsi_14 > 50 && ema_20 < close",
        ...     "adx_14 > 25",
        ...     "volume > volume_sma_20"
        ... ]
        >>> extract_indicators_from_formulas(formulas)
        {'rsi_14', 'ema_20', 'close', 'adx_14', 'volume', 'volume_sma_20'}

        >>> formula_dict = {
        ...     "entry": "rsi_7 < 25 && close < bb_20_lower",
        ...     "exit": "close > bb_20_upper || rsi_7 > 75"
        ... }
        >>> extract_indicators_from_formulas(formula_dict)
        {'rsi_7', 'close', 'bb_20_lower', 'bb_20_upper'}
    """
    if isinstance(formulas, dict):
        formula_list = list(formulas.values())
    else:
        formula_list = formulas if formulas else []

    all_indicators = set()
    for formula in formula_list:
        all_indicators.update(extract_indicators(formula))

    return all_indicators


def get_indicator_dependencies(formula: str) -> Dict[str, List[int]]:
    """Get indicators and their shift values from a formula.

    Returns a dict mapping indicator names to lists of shift values used
    for that indicator in the formula.

    Args:
        formula: Formula string

    Returns:
        Dict of {indicator: [shifts]} where shifts are used in the formula

    Examples:
        >>> get_indicator_dependencies("rsi_14[0] > 50 && rsi_14[-1] < 40")
        {'rsi_14': [0, -1]}

        >>> get_indicator_dependencies("ema_5 > ema_20 && close > bb_upper")
        {'ema_5': [0], 'ema_20': [0], 'close': [0], 'bb_upper': [0]}
    """
    if not formula or not isinstance(formula, str):
        return {}

    try:
        lexer = Lexer(formula)
        parser = Parser(lexer.get_tokens())
        ast = parser.parse()
        return _extract_dependencies_from_ast(ast)
    except Exception:
        # Fallback to regex extraction
        dependencies = {}
        # Match indicator[shift] or bare indicators
        pattern = r'([a-z_][a-z0-9_]*)\[(-?\d+)\]|([a-z_][a-z0-9_]*)(?![a-z0-9_\[])'
        for match in re.finditer(pattern, formula, re.IGNORECASE):
            if match.group(1):  # indicator[shift] format
                indicator = match.group(1)
                shift = int(match.group(2))
                if indicator not in dependencies:
                    dependencies[indicator] = []
                if shift not in dependencies[indicator]:
                    dependencies[indicator].append(shift)
            elif match.group(3):  # bare indicator
                indicator = match.group(3)
                # Skip if it's a keyword or function name
                if indicator.lower() not in ['data', 'abs', 'round', 'max', 'min', 'int', 'float', 'and', 'or', 'not']:
                    if indicator not in dependencies:
                        dependencies[indicator] = [0]
                    elif 0 not in dependencies[indicator]:
                        dependencies[indicator].append(0)
        return dependencies


def validate_indicators_available(formula: str, available_indicators: Set[str]) -> tuple[bool, Set[str]]:
    """Check if all indicators referenced in a formula are available.

    Args:
        formula: Formula string
        available_indicators: Set of available indicator names

    Returns:
        Tuple of (is_valid, missing_indicators)
        - is_valid: True if all indicators are available
        - missing_indicators: Set of indicators not in available_indicators

    Examples:
        >>> formula = "rsi_14 > 50 && ema_20 < close"
        >>> available = {"rsi_14", "ema_20", "close"}
        >>> validate_indicators_available(formula, available)
        (True, set())

        >>> available = {"rsi_14", "close"}  # missing ema_20
        >>> validate_indicators_available(formula, available)
        (False, {'ema_20'})
    """
    required = extract_indicators(formula)
    missing = required - available_indicators
    return (len(missing) == 0, missing)


# ============================================================================
# Internal Helper Functions
# ============================================================================


def _extract_from_ast(node) -> Set[str]:
    """Recursively extract indicators from AST node."""
    if node is None:
        return set()

    indicators = set()

    # Handle Indicator nodes (with shift notation)
    if isinstance(node, Indicator):
        indicators.add(node.name)

    # Handle Variable nodes (bare identifiers)
    elif isinstance(node, Variable):
        indicators.add(node.name)

    # Handle Binary operations (recursively)
    elif isinstance(node, BinaryOp):
        indicators.update(_extract_from_ast(node.left))
        indicators.update(_extract_from_ast(node.right))

    # Handle Unary operations (recursively)
    elif isinstance(node, UnaryOp):
        indicators.update(_extract_from_ast(node.expr))

    # Literals don't have indicators
    elif isinstance(node, Literal):
        pass

    return indicators


def _extract_dependencies_from_ast(node) -> Dict[str, List[int]]:
    """Recursively extract indicators and their shifts from AST."""
    if node is None:
        return {}

    dependencies = {}

    if isinstance(node, Indicator):
        if node.name not in dependencies:
            dependencies[node.name] = []
        if node.shift not in dependencies[node.name]:
            dependencies[node.name].append(node.shift)

    elif isinstance(node, Variable):
        if node.name not in dependencies:
            dependencies[node.name] = [0]
        elif 0 not in dependencies[node.name]:
            dependencies[node.name].append(0)

    elif isinstance(node, BinaryOp):
        left_deps = _extract_dependencies_from_ast(node.left)
        right_deps = _extract_dependencies_from_ast(node.right)
        # Merge dependencies
        for indicator, shifts in left_deps.items():
            if indicator not in dependencies:
                dependencies[indicator] = []
            for shift in shifts:
                if shift not in dependencies[indicator]:
                    dependencies[indicator].append(shift)
        for indicator, shifts in right_deps.items():
            if indicator not in dependencies:
                dependencies[indicator] = []
            for shift in shifts:
                if shift not in dependencies[indicator]:
                    dependencies[indicator].append(shift)

    elif isinstance(node, UnaryOp):
        dependencies.update(_extract_dependencies_from_ast(node.expr))

    return dependencies


def _extract_by_regex(formula: str) -> Set[str]:
    """Fallback regex-based indicator extraction."""
    indicators = set()

    # Match indicator[shift] or bare identifiers
    # Pattern: identifier with optional [number]
    pattern = r'([a-z_][a-z0-9_]*)\[(-?\d+)\]|([a-z_][a-z0-9_]*)(?![a-z0-9_\[])'

    for match in re.finditer(pattern, formula, re.IGNORECASE):
        if match.group(1):  # indicator[shift]
            indicators.add(match.group(1))
        elif match.group(3):  # bare indicator
            indicator = match.group(3)
            # Filter out keywords and function names
            if indicator.lower() not in ['data', 'abs', 'round', 'max', 'min', 'int', 'float', 'and', 'or', 'not']:
                indicators.add(indicator)

    return indicators
