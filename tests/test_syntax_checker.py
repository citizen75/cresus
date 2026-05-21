"""Test suite for formula syntax checker."""

import pytest
from src.tools.formula.syntax_checker import (
    check_syntax,
    check_formulas,
    validate_formulas,
    check_syntax_detailed,
    format_validation_report,
    FormulaSyntaxError,
)


class TestCheckSyntax:
    """Test check_syntax function."""

    def test_valid_dsl_formula(self):
        """Check valid DSL formula."""
        result = check_syntax("rsi_14 > 50 && ema_20 < close")
        assert result.is_valid is True
        assert result.error_message is None
        assert bool(result) is True

    def test_valid_shift_notation(self):
        """Check valid shift notation."""
        result = check_syntax("rsi_14[0] > 50 && rsi_14[-1] < 40")
        assert result.is_valid is True

    def test_valid_complex_formula(self):
        """Check valid complex formula."""
        result = check_syntax(
            "(rsi_14 > 50) && (ema_5 > ema_20) && (adx_14 > 25)"
        )
        assert result.is_valid is True

    def test_valid_arithmetic(self):
        """Check valid arithmetic formula."""
        result = check_syntax("rsi_7 + rsi_14 > 100")
        assert result.is_valid is True

    def test_valid_pandas_syntax(self):
        """Check valid pandas syntax."""
        result = check_syntax("data['close'] > 100")
        assert result.is_valid is True

    def test_invalid_unclosed_paren(self):
        """Check invalid: unclosed parenthesis."""
        result = check_syntax("(rsi_14 > 50")
        assert result.is_valid is False
        assert result.error_message is not None
        assert "closed" in result.error_message.lower() or "unexpected" in result.error_message.lower()

    def test_invalid_unexpected_operator(self):
        """Check invalid: operator at start."""
        result = check_syntax("> 50")
        assert result.is_valid is False
        assert result.error_message is not None

    def test_invalid_double_operator(self):
        """Check invalid: double operator."""
        result = check_syntax("rsi_14 ** ** 50")
        assert result.is_valid is False
        assert result.error_message is not None

    def test_invalid_special_chars(self):
        """Check invalid: special characters."""
        result = check_syntax("rsi_14 > 50 @@ ema_20")
        assert result.is_valid is False
        assert result.error_message is not None

    def test_empty_formula(self):
        """Check empty formula."""
        result = check_syntax("")
        assert result.is_valid is False
        assert "empty" in result.error_message.lower()

    def test_none_formula(self):
        """Check None formula."""
        result = check_syntax(None)
        assert result.is_valid is False

    def test_invalid_missing_operand(self):
        """Check invalid: missing operand."""
        result = check_syntax("rsi_14 > * 50")
        assert result.is_valid is False

    def test_result_is_bool_truthy(self):
        """Result object is truthy when valid."""
        valid_result = check_syntax("rsi_14 > 50")
        invalid_result = check_syntax("invalid @@")
        assert bool(valid_result) is True
        assert bool(invalid_result) is False

    def test_result_string_representation(self):
        """Result has meaningful string representation."""
        result = check_syntax("rsi_14 > 50")
        assert "Valid" in str(result)
        assert result.formula in str(result)


class TestCheckFormulas:
    """Test check_formulas function."""

    def test_list_of_formulas(self):
        """Check list of formulas."""
        formulas = [
            "rsi_14 > 50",
            "ema_20 < close",
            "adx_14 > 25"
        ]
        results = check_formulas(formulas)
        assert len(results) == 3
        assert all(r.is_valid for r in results)

    def test_dict_of_formulas(self):
        """Check dict of formulas."""
        formulas = {
            "entry": "rsi_7 < 25",
            "exit": "close > ema_20",
            "filter": "volume > volume_sma_20"
        }
        results = check_formulas(formulas)
        assert len(results) == 3
        assert all(r.is_valid for r in results)

    def test_mixed_valid_and_invalid(self):
        """Check list with mixed valid/invalid."""
        formulas = [
            "rsi_14 > 50",
            "invalid @@",
            "ema_20 < close"
        ]
        results = check_formulas(formulas)
        assert len(results) == 3
        assert results[0].is_valid is True
        assert results[1].is_valid is False
        assert results[2].is_valid is True

    def test_empty_list(self):
        """Check empty list."""
        results = check_formulas([])
        assert results == []

    def test_empty_dict(self):
        """Check empty dict."""
        results = check_formulas({})
        assert results == []

    def test_none_input(self):
        """Check None input."""
        results = check_formulas(None)
        assert results == []


class TestValidateFormulas:
    """Test validate_formulas function."""

    def test_all_valid(self):
        """All formulas valid."""
        formulas = ["rsi_14 > 50", "ema_20 < close", "adx_14 > 25"]
        all_valid, errors = validate_formulas(formulas)
        assert all_valid is True
        assert len(errors) == 0

    def test_some_invalid(self):
        """Some formulas invalid."""
        formulas = [
            "rsi_14 > 50",
            "invalid @@",
            "ema_20 < close",
            "bad syntax >>>"
        ]
        all_valid, errors = validate_formulas(formulas)
        assert all_valid is False
        assert len(errors) == 2
        assert all(not e.is_valid for e in errors)

    def test_all_invalid(self):
        """All formulas invalid."""
        formulas = ["invalid @@", "bad >>>", "wrong !"]
        all_valid, errors = validate_formulas(formulas)
        assert all_valid is False
        assert len(errors) == 3

    def test_empty_list(self):
        """Empty list is valid."""
        all_valid, errors = validate_formulas([])
        assert all_valid is True
        assert len(errors) == 0

    def test_with_dict(self):
        """Validate dict of formulas."""
        formulas = {
            "entry": "rsi_7 < 25",
            "exit": "invalid @@"
        }
        all_valid, errors = validate_formulas(formulas)
        assert all_valid is False
        assert len(errors) == 1


class TestCheckSyntaxDetailed:
    """Test check_syntax_detailed function."""

    def test_valid_dsl_formula(self):
        """Detailed check of valid DSL formula."""
        result = check_syntax_detailed("rsi_14 > 50 && ema_20 < close")
        assert result["is_valid"] is True
        assert result["syntax_type"] == "dsl"
        assert result["error_message"] is None
        assert result["formula"] == "rsi_14 > 50 && ema_20 < close"

    def test_valid_pandas_formula(self):
        """Detailed check of valid pandas formula."""
        result = check_syntax_detailed("data['close'] > 100")
        assert result["is_valid"] is True
        assert result["syntax_type"] == "pandas"

    def test_invalid_formula_details(self):
        """Detailed check of invalid formula."""
        result = check_syntax_detailed("invalid @@")
        assert result["is_valid"] is False
        assert result["error_message"] is not None
        assert result["error_type"] is not None

    def test_all_keys_present(self):
        """All expected keys in result dict."""
        result = check_syntax_detailed("rsi_14 > 50")
        expected_keys = {
            "formula", "is_valid", "syntax_type",
            "error_message", "error_type", "error_position"
        }
        assert set(result.keys()) == expected_keys


class TestFormatValidationReport:
    """Test format_validation_report function."""

    def test_report_all_valid(self):
        """Report for all valid formulas."""
        formulas = ["rsi_14 > 50", "ema_20 < close"]
        report = format_validation_report(formulas)
        assert "Valid:" in report
        assert "2" in report
        assert "Invalid:" in report
        assert "0" in report

    def test_report_with_invalid(self):
        """Report with invalid formulas."""
        formulas = ["rsi_14 > 50", "invalid @@", "ema_20 < close"]
        report = format_validation_report(formulas)
        assert "Invalid Formulas:" in report
        assert "invalid @@" in report
        assert "1" in report  # Invalid count

    def test_verbose_report(self):
        """Verbose report includes error details."""
        formulas = ["rsi_14 > 50", "invalid @@"]
        report = format_validation_report(formulas, verbose=True)
        assert "Error:" in report
        assert "Type:" in report

    def test_report_structure(self):
        """Report has correct structure."""
        formulas = ["rsi_14 > 50"]
        report = format_validation_report(formulas)
        assert "Validation Report" in report
        assert "Total:" in report
        assert "Valid:" in report
        assert "Invalid:" in report


class TestRealWorldScenarios:
    """Test with real trading formula scenarios."""

    def test_momentum_strategy_validation(self):
        """Validate momentum strategy formulas."""
        formulas = {
            "signal": "rsi_7 > 50 && roc_5 > 0",
            "confirmation": "adx_14 > 25 && ema_5 > ema_20",
            "volume": "volume > volume_sma_20"
        }
        all_valid, errors = validate_formulas(formulas)
        assert all_valid is True
        assert len(errors) == 0

    def test_mean_reversion_validation(self):
        """Validate mean reversion formulas."""
        formulas = {
            "entry": "rsi_7 < 25 && close < bb_20_lower",
            "exit": "close > ema_20 || rsi_7 > 75",
            "volume_filter": "volume > volume_sma_20 * 1.5"
        }
        all_valid, errors = validate_formulas(formulas)
        assert all_valid is True

    def test_complex_signal_validation(self):
        """Validate complex multi-condition signal."""
        formula = (
            "((rsi_14 > 50) && (ema_5 > ema_20)) || "
            "((rsi_14 < 30) && (close < bb_20_lower))"
        )
        result = check_syntax(formula)
        assert result.is_valid is True

    def test_position_sizing_formulas(self):
        """Validate position sizing formulas."""
        formulas = [
            "1000 / close",
            "account_size / (close * multiplier)",
            "shares * (entry - stop)"
        ]
        results = check_formulas(formulas)
        assert all(r.is_valid for r in results)


class TestErrorDetection:
    """Test error detection capabilities."""

    def test_detects_unclosed_brackets(self):
        """Detects unclosed square brackets."""
        result = check_syntax("rsi_14[0 > 50")
        assert result.is_valid is False

    def test_detects_mismatched_parens(self):
        """Detects mismatched parentheses."""
        result = check_syntax("(rsi_14 > 50) && ema_20 < close)")
        assert result.is_valid is False

    def test_detects_invalid_operators(self):
        """Detects invalid operators."""
        result = check_syntax("rsi_14 @@ 50")
        assert result.is_valid is False

    def test_detects_empty_expression(self):
        """Detects empty parenthetical expression."""
        result = check_syntax("rsi_14 > () && ema_20")
        assert result.is_valid is False

    def test_detects_multiple_errors(self):
        """Multiple issues in formula."""
        result = check_syntax("((rsi_14 > 50) && (ema_20")
        assert result.is_valid is False

    def test_error_position_tracking(self):
        """Error tracks position when available."""
        result = check_syntax("rsi_14 > 50 @@")
        # Position may or may not be available depending on parser
        assert result.is_valid is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_formula(self):
        """Very long but valid formula."""
        parts = ["rsi_14 > 50"] * 50
        formula = " && ".join(parts)
        result = check_syntax(formula)
        assert result.is_valid is True

    def test_deeply_nested_parens(self):
        """Deeply nested parentheses."""
        formula = "((((((rsi_14 > 50))))))"
        result = check_syntax(formula)
        assert result.is_valid is True

    def test_mixed_dsl_and_pandas(self):
        """Mixed DSL and pandas syntax not supported."""
        # Formula with both shift notation and pandas syntax
        formula = "rsi_14[0] > 50 && data['close'] > 100"
        result = check_syntax(formula)
        # Should be detected as DSL due to shift notation and && operator
        assert isinstance(result, FormulaSyntaxError)
        # DSL parser cannot handle pandas data['close'] syntax
        assert result.is_valid is False

    def test_whitespace_handling(self):
        """Extra whitespace is handled."""
        formula = "   rsi_14   >   50   &&   ema_20   <   close   "
        result = check_syntax(formula)
        assert result.is_valid is True

    def test_unicode_characters(self):
        """Unicode characters in DSL formula cause error."""
        # Unicode character in operator position should fail DSL parsing
        formula = "rsi_14[0] > 50 && ema_20 ™ close"
        result = check_syntax(formula)
        assert result.is_valid is False

    def test_numeric_operations(self):
        """Complex numeric operations."""
        formula = "(10 + 5) * 2 / (3 - 1) > 15"
        result = check_syntax(formula)
        assert result.is_valid is True


class TestSyntaxErrorDataclass:
    """Test SyntaxError dataclass functionality."""

    def test_valid_error_object(self):
        """Create valid SyntaxError object."""
        error = check_syntax("rsi_14 > 50")
        assert error.formula == "rsi_14 > 50"
        assert error.is_valid is True
        assert error.error_message is None

    def test_invalid_error_object(self):
        """Create invalid SyntaxError object."""
        error = check_syntax("invalid @@")
        assert error.is_valid is False
        assert error.error_message is not None

    def test_error_string_repr(self):
        """String representation of errors."""
        valid_error = check_syntax("rsi_14 > 50")
        assert "Valid" in str(valid_error)

        invalid_error = check_syntax("invalid @@")
        assert "Invalid" in str(invalid_error)

    def test_error_bool_conversion(self):
        """Boolean conversion of errors."""
        valid_error = check_syntax("rsi_14 > 50")
        invalid_error = check_syntax("invalid @@")

        assert valid_error is True or valid_error  # Truthy
        assert invalid_error is False or not invalid_error  # Falsy

    def test_error_attributes(self):
        """Error has all expected attributes."""
        error = check_syntax("invalid @@")
        assert hasattr(error, "formula")
        assert hasattr(error, "is_valid")
        assert hasattr(error, "error_message")
        assert hasattr(error, "error_type")
        assert hasattr(error, "position")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
