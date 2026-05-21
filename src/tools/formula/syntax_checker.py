"""Syntax validation for formula strings.

Utilities to validate formula syntax and provide detailed error messages.
Supports both DSL and traditional pandas syntax.
"""

from typing import List, Dict, Tuple, Union, Optional
from dataclasses import dataclass
from .dsl_parser import Lexer, Parser
from .dsl_helpers import is_dsl_formula


@dataclass
class FormulaSyntaxError:
    """Represents a formula syntax validation result."""

    formula: str
    is_valid: bool
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    position: Optional[int] = None

    def __str__(self):
        """String representation of error."""
        if self.is_valid:
            return f"✓ Valid: {self.formula}"
        return f"✗ Invalid: {self.formula}\n  Error: {self.error_message}"

    def __bool__(self):
        """Truthy if valid."""
        return self.is_valid


def check_syntax(formula: Union[str, int, float]) -> FormulaSyntaxError:
    """Check the syntax of a single formula.

    Validates both DSL and traditional pandas syntax. Returns detailed
    error information if syntax is invalid.

    Args:
        formula: Formula string to validate (also accepts numeric literals)

    Returns:
        FormulaSyntaxError object with validation details

    Examples:
        >>> result = check_syntax("rsi_14 > 50 && ema_20 < close")
        >>> if result:
        ...     print("Formula is valid")

        >>> result = check_syntax("rsi_14 > 50 @@ invalid")
        >>> if not result:
        ...     print(f"Error: {result.error_message}")

        >>> result = check_syntax(0.001)
        >>> if result:
        ...     print("Numeric literal is valid")
    """
    if formula is None or (isinstance(formula, str) and not formula):
        return FormulaSyntaxError(
            formula=str(formula),
            is_valid=False,
            error_message="Formula is empty or not a string",
            error_type="EmptyFormula"
        )

    # Convert numeric types to strings
    if isinstance(formula, (int, float)):
        formula = str(formula)

    # Try DSL parsing
    if is_dsl_formula(formula):
        return _check_dsl_syntax(formula)

    # Try traditional pandas syntax
    return _check_pandas_syntax(formula)


def check_formulas(formulas: Union[List[str], Dict[str, str]]) -> List[FormulaSyntaxError]:
    """Check syntax of multiple formulas.

    Args:
        formulas: List of formula strings or dict of {name: formula}

    Returns:
        List of FormulaSyntaxError objects (one per formula)

    Examples:
        >>> results = check_formulas([
        ...     "rsi_14 > 50",
        ...     "ema_20 < close",
        ...     "invalid @@ formula"
        ... ])
        >>> for result in results:
        ...     print(result)
    """
    if isinstance(formulas, dict):
        formula_list = list(formulas.values())
    else:
        formula_list = formulas if formulas else []

    return [check_syntax(formula) for formula in formula_list]


def validate_formulas(formulas: Union[List[str], Dict[str, str]]) -> Tuple[bool, List[FormulaSyntaxError]]:
    """Validate all formulas and return summary.

    Args:
        formulas: List or dict of formulas to validate

    Returns:
        Tuple of (all_valid, error_list)
        - all_valid: True if all formulas are syntactically correct
        - error_list: List of FormulaSyntaxError objects (only invalid ones)

    Examples:
        >>> formulas = ["rsi_14 > 50", "invalid @@"]
        >>> all_valid, errors = validate_formulas(formulas)
        >>> if not all_valid:
        ...     for error in errors:
        ...         print(f"Found error: {error.error_message}")
    """
    results = check_formulas(formulas)
    invalid_results = [r for r in results if not r.is_valid]
    all_valid = len(invalid_results) == 0
    return all_valid, invalid_results


def check_syntax_detailed(formula: str) -> Dict[str, any]:
    """Check syntax and return detailed analysis.

    More comprehensive analysis including syntax type detection.

    Args:
        formula: Formula string to analyze

    Returns:
        Dict with detailed syntax information

    Examples:
        >>> result = check_syntax_detailed("rsi_14 > 50 && ema_20 < close")
        >>> print(result['syntax_type'])  # 'dsl'
        >>> print(result['is_valid'])     # True
    """
    result = check_syntax(formula)

    return {
        "formula": formula,
        "is_valid": result.is_valid,
        "syntax_type": "dsl" if is_dsl_formula(formula) else "pandas",
        "error_message": result.error_message,
        "error_type": result.error_type,
        "error_position": result.position,
    }


def format_validation_report(formulas: Union[List[str], Dict[str, str]],
                            verbose: bool = False) -> str:
    """Generate a formatted validation report.

    Args:
        formulas: Formulas to validate
        verbose: Include detailed error information

    Returns:
        Formatted string report

    Examples:
        >>> formulas = ["rsi_14 > 50", "invalid @@", "ema_20 < close"]
        >>> report = format_validation_report(formulas)
        >>> print(report)
    """
    results = check_formulas(formulas)
    valid_count = sum(1 for r in results if r.is_valid)
    invalid_count = len(results) - valid_count

    lines = []
    lines.append(f"Formula Validation Report")
    lines.append(f"=" * 50)
    lines.append(f"Total:   {len(results)}")
    lines.append(f"Valid:   {valid_count} ✓")
    lines.append(f"Invalid: {invalid_count} ✗")
    lines.append("")

    if invalid_count > 0:
        lines.append("Invalid Formulas:")
        lines.append("-" * 50)
        for result in results:
            if not result.is_valid:
                lines.append(f"✗ {result.formula}")
                if verbose:
                    lines.append(f"  Error: {result.error_message}")
                    if result.error_type:
                        lines.append(f"  Type:  {result.error_type}")
                    if result.position is not None:
                        lines.append(f"  Position: {result.position}")
                    lines.append("")

    if valid_count > 0 and verbose:
        lines.append("Valid Formulas:")
        lines.append("-" * 50)
        for result in results:
            if result.is_valid:
                lines.append(f"✓ {result.formula}")

    return "\n".join(lines)


# ============================================================================
# Internal Helper Functions
# ============================================================================


def _check_dsl_syntax(formula: str) -> FormulaSyntaxError:
    """Check DSL formula syntax."""
    try:
        lexer = Lexer(formula)
        parser = Parser(lexer.get_tokens())
        parser.parse()
        return FormulaSyntaxError(formula=formula, is_valid=True)
    except Exception as e:
        error_msg = str(e)
        position = _extract_position_from_error(error_msg)
        return FormulaSyntaxError(
            formula=formula,
            is_valid=False,
            error_message=error_msg,
            error_type="SyntaxError",
            position=position
        )


def _check_pandas_syntax(formula: str) -> FormulaSyntaxError:
    """Check traditional pandas formula syntax."""
    try:
        # Try to compile the formula as Python code
        compile(formula, '<formula>', 'eval')
        return FormulaSyntaxError(formula=formula, is_valid=True)
    except BaseException as e:
        # Catch Python's built-in SyntaxError from compile()
        error_msg = str(e)
        position = None
        if hasattr(e, 'offset'):
            position = e.offset
        return FormulaSyntaxError(
            formula=formula,
            is_valid=False,
            error_message=error_msg,
            error_type=type(e).__name__,
            position=position
        )


def _extract_position_from_error(error_msg: str) -> Optional[int]:
    """Extract position information from error message."""
    import re
    match = re.search(r'position (\d+)', error_msg)
    if match:
        return int(match.group(1))
    return None
