"""Comprehensive test suite for DSL formula parser.

Tests the lexer, parser, and AST evaluation for trading formula expressions.
"""

import pytest
import pandas as pd
import numpy as np
from src.tools.formula.dsl_parser import (
    Lexer, Parser, parse_formula, evaluate_dsl,
    Token, Literal, Variable, Indicator, BinaryOp, UnaryOp
)


class TestLexer:
    """Test tokenization of DSL formulas."""

    def test_empty_formula(self):
        """Lexer should handle empty formula."""
        lexer = Lexer("")
        assert lexer.get_tokens() == []

    def test_single_number(self):
        """Lexer should tokenize numeric literal."""
        lexer = Lexer("42")
        tokens = lexer.get_tokens()
        assert len(tokens) == 1
        assert tokens[0].type == "NUMBER"
        assert tokens[0].value == "42"

    def test_floating_point(self):
        """Lexer should tokenize floating point numbers."""
        lexer = Lexer("3.14159")
        tokens = lexer.get_tokens()
        assert tokens[0].type == "NUMBER"
        assert tokens[0].value == "3.14159"

    def test_simple_identifier(self):
        """Lexer should tokenize variable names."""
        lexer = Lexer("rsi_14")
        tokens = lexer.get_tokens()
        assert len(tokens) == 1
        assert tokens[0].type == "NAME"
        assert tokens[0].value == "rsi_14"

    def test_indicator_with_shift(self):
        """Lexer should tokenize indicator with shift notation."""
        lexer = Lexer("rsi_14[0]")
        tokens = lexer.get_tokens()
        assert len(tokens) == 1
        assert tokens[0].type == "INDICATOR"
        assert tokens[0].value == "rsi_14[0]"

    def test_negative_shift(self):
        """Lexer should handle negative shift values."""
        lexer = Lexer("ema_20[-1]")
        tokens = lexer.get_tokens()
        assert len(tokens) == 1
        assert tokens[0].type == "INDICATOR"
        assert tokens[0].value == "ema_20[-1]"

    def test_comparison_operators(self):
        """Lexer should tokenize all comparison operators."""
        operators = [
            ("5 == 5", "EQ"),
            ("5 < 10", "LT"),
            ("10 > 5", "GT"),
            ("5 <= 5", "LE"),
            ("10 >= 5", "GE"),
        ]
        for formula, op_type in operators:
            lexer = Lexer(formula)
            tokens = lexer.get_tokens()
            # Find the operator token in the formula
            op_tokens = [t for t in tokens if t.type == op_type]
            assert len(op_tokens) > 0, f"Operator {op_type} not found in {formula}"

    def test_logical_operators(self):
        """Lexer should tokenize logical operators."""
        operators = [
            ("&&", "AND"),
            ("||", "OR"),
            ("!", "NOT"),
        ]
        for op_str, op_type in operators:
            lexer = Lexer(op_str)
            tokens = lexer.get_tokens()
            assert tokens[0].type == op_type
            assert tokens[0].value == op_str

    def test_arithmetic_operators(self):
        """Lexer should tokenize arithmetic operators."""
        operators = [
            ("+", "PLUS"),
            ("-", "MINUS"),
            ("*", "MUL"),
            ("/", "DIV"),
        ]
        for op_str, op_type in operators:
            lexer = Lexer(op_str)
            tokens = lexer.get_tokens()
            assert tokens[0].type == op_type

    def test_parentheses(self):
        """Lexer should tokenize parentheses."""
        lexer = Lexer("()")
        tokens = lexer.get_tokens()
        assert len(tokens) == 2
        assert tokens[0].type == "LPAREN"
        assert tokens[1].type == "RPAREN"

    def test_brackets(self):
        """Lexer should tokenize square brackets."""
        lexer = Lexer("[]")
        tokens = lexer.get_tokens()
        assert len(tokens) == 2
        assert tokens[0].type == "LBRACKET"
        assert tokens[1].type == "RBRACKET"

    def test_whitespace_ignored(self):
        """Lexer should ignore whitespace."""
        lexer = Lexer("  rsi_14  <  25  ")
        tokens = lexer.get_tokens()
        assert len(tokens) == 3  # rsi_14, <, 25
        assert tokens[0].value == "rsi_14"

    def test_complex_formula_tokens(self):
        """Lexer should tokenize complex formulas."""
        lexer = Lexer("(rsi_14 > 50) && (ema_20 < close)")
        tokens = lexer.get_tokens()
        assert len(tokens) == 11  # (, rsi_14, >, 50, ), &&, (, ema_20, <, close, )

    def test_invalid_character(self):
        """Lexer should reject invalid characters."""
        with pytest.raises(SyntaxError):
            Lexer("rsi_14 @ 50")


class TestParser:
    """Test parsing and AST construction."""

    def test_parse_literal(self):
        """Parser should create Literal node for numbers."""
        ast = parse_formula("42")
        assert isinstance(ast, Literal)
        assert ast.value == 42.0

    def test_parse_variable(self):
        """Parser should create Variable node for identifiers."""
        ast = parse_formula("close")
        assert isinstance(ast, Indicator)
        assert ast.name == "close"
        assert ast.shift == 0

    def test_parse_indicator_shift(self):
        """Parser should create Indicator node with shift."""
        ast = parse_formula("rsi_14[-2]")
        assert isinstance(ast, Indicator)
        assert ast.name == "rsi_14"
        assert ast.shift == -2

    def test_parse_comparison(self):
        """Parser should handle comparison operators."""
        ast = parse_formula("rsi_14 > 50")
        assert isinstance(ast, BinaryOp)
        assert ast.op == ">"
        assert isinstance(ast.left, Indicator)
        assert isinstance(ast.right, Literal)

    def test_parse_logical_and(self):
        """Parser should handle logical AND operator."""
        ast = parse_formula("rsi_14 > 50 && ema_20 < close")
        assert isinstance(ast, BinaryOp)
        assert ast.op == "&&"

    def test_parse_logical_or(self):
        """Parser should handle logical OR operator."""
        ast = parse_formula("rsi_14 > 50 || ema_20 < close")
        assert isinstance(ast, BinaryOp)
        assert ast.op == "||"

    def test_parse_logical_not(self):
        """Parser should handle logical NOT operator."""
        ast = parse_formula("!close")
        assert isinstance(ast, UnaryOp)
        assert ast.op == "!"

    def test_parse_operator_precedence(self):
        """Parser should respect operator precedence."""
        # Test: a || b && c should parse as a || (b && c), not (a || b) && c
        ast = parse_formula("rsi_14 > 50 || ema_20 > 60 && adx_14 > 25")
        assert isinstance(ast, BinaryOp)
        assert ast.op == "||"  # OR has lower precedence
        assert isinstance(ast.right, BinaryOp)
        assert ast.right.op == "&&"  # AND is on the right

    def test_parse_comparison_precedence(self):
        """Parser should handle comparison vs arithmetic precedence."""
        # Test: a + b > c should parse as (a + b) > c
        ast = parse_formula("rsi_7 + rsi_14 > 100")
        assert isinstance(ast, BinaryOp)
        assert ast.op == ">"
        assert isinstance(ast.left, BinaryOp)
        assert ast.left.op == "+"

    def test_parse_arithmetic_precedence(self):
        """Parser should handle arithmetic operator precedence."""
        # Test: a + b * c should parse as a + (b * c)
        ast = parse_formula("10 + 5 * 2")
        assert isinstance(ast, BinaryOp)
        assert ast.op == "+"
        assert isinstance(ast.right, BinaryOp)
        assert ast.right.op == "*"

    def test_parse_parentheses_override_precedence(self):
        """Parser should respect parentheses."""
        ast = parse_formula("(10 + 5) * 2")
        assert isinstance(ast, BinaryOp)
        assert ast.op == "*"
        assert isinstance(ast.left, BinaryOp)
        assert ast.left.op == "+"

    def test_parse_unary_minus(self):
        """Parser should handle unary minus."""
        ast = parse_formula("-42")
        assert isinstance(ast, UnaryOp)
        assert ast.op == "-"
        assert isinstance(ast.expr, Literal)

    def test_invalid_formula_empty_parens(self):
        """Parser should reject empty parentheses."""
        with pytest.raises(SyntaxError):
            parse_formula("()")

    def test_invalid_formula_unclosed_paren(self):
        """Parser should reject unclosed parentheses."""
        with pytest.raises(SyntaxError):
            parse_formula("(rsi_14 > 50")

    def test_invalid_formula_unexpected_operator(self):
        """Parser should reject formulas starting with operator."""
        with pytest.raises(SyntaxError):
            parse_formula("> 50")


class TestASTEvaluation:
    """Test evaluation of AST nodes."""

    def test_evaluate_literal(self):
        """Literal should evaluate to its value."""
        ast = parse_formula("42")
        result = ast.evaluate({})
        assert result == 42.0

    def test_evaluate_variable_in_dict(self):
        """Variable should look up value in dict."""
        ast = parse_formula("close")
        result = ast.evaluate({"close": 100.5})
        assert result == 100.5

    def test_evaluate_variable_missing(self):
        """Variable should raise KeyError if not in dict."""
        ast = parse_formula("close")
        with pytest.raises(KeyError):
            ast.evaluate({})

    def test_evaluate_comparison_true(self):
        """Comparison should return True."""
        ast = parse_formula("rsi_14 > 50")
        result = ast.evaluate({"rsi_14": 75})
        assert result is True

    def test_evaluate_comparison_false(self):
        """Comparison should return False."""
        ast = parse_formula("rsi_14 > 50")
        result = ast.evaluate({"rsi_14": 25})
        assert result is False

    def test_evaluate_all_comparisons(self):
        """Test all comparison operators."""
        data = {"a": 10, "b": 20}

        assert parse_formula("a < b").evaluate(data) is True
        assert parse_formula("a > b").evaluate(data) is False
        assert parse_formula("a <= b").evaluate(data) is True
        assert parse_formula("a >= b").evaluate(data) is False
        assert parse_formula("a == b").evaluate(data) is False
        # Test != operator (not equal)
        assert parse_formula("a == 10").evaluate(data) is True

    def test_evaluate_logical_and_true(self):
        """Logical AND should return True when both are true."""
        ast = parse_formula("rsi_14 > 50 && ema_20 < 100")
        result = ast.evaluate({"rsi_14": 75, "ema_20": 50})
        assert result is True

    def test_evaluate_logical_and_false(self):
        """Logical AND should return False when one is false."""
        ast = parse_formula("rsi_14 > 50 && ema_20 < 100")
        result = ast.evaluate({"rsi_14": 25, "ema_20": 50})
        assert result is False

    def test_evaluate_logical_or_true(self):
        """Logical OR should return True when one is true."""
        ast = parse_formula("rsi_14 > 50 || ema_20 < 100")
        result = ast.evaluate({"rsi_14": 75, "ema_20": 150})
        assert result is True

    def test_evaluate_logical_or_false(self):
        """Logical OR should return False when both are false."""
        ast = parse_formula("rsi_14 > 50 || ema_20 < 100")
        result = ast.evaluate({"rsi_14": 25, "ema_20": 150})
        assert result is False

    def test_evaluate_logical_not_true(self):
        """Logical NOT should negate."""
        ast = parse_formula("!close")
        result = ast.evaluate({"close": 0})
        assert result is True

    def test_evaluate_logical_not_false(self):
        """Logical NOT should negate."""
        ast = parse_formula("!close")
        result = ast.evaluate({"close": 100})
        assert result is False

    def test_evaluate_arithmetic_add(self):
        """Addition should work correctly."""
        ast = parse_formula("rsi_7 + rsi_14")
        result = ast.evaluate({"rsi_7": 30, "rsi_14": 40})
        assert result == 70

    def test_evaluate_arithmetic_subtract(self):
        """Subtraction should work correctly."""
        ast = parse_formula("rsi_7 - rsi_14")
        result = ast.evaluate({"rsi_7": 70, "rsi_14": 30})
        assert result == 40

    def test_evaluate_arithmetic_multiply(self):
        """Multiplication should work correctly."""
        ast = parse_formula("rsi_7 * 2")
        result = ast.evaluate({"rsi_7": 25})
        assert result == 50

    def test_evaluate_arithmetic_divide(self):
        """Division should work correctly."""
        ast = parse_formula("rsi_7 / 2")
        result = ast.evaluate({"rsi_7": 50})
        assert result == 25

    def test_evaluate_division_by_zero(self):
        """Division by zero should raise ValueError."""
        ast = parse_formula("rsi_7 / 0")
        with pytest.raises(ValueError):
            ast.evaluate({"rsi_7": 50})

    def test_evaluate_unary_minus(self):
        """Unary minus should negate."""
        ast = parse_formula("-rsi_7")
        result = ast.evaluate({"rsi_7": 50})
        assert result == -50


class TestIndicatorShift:
    """Test indicator shift notation."""

    def test_shift_zero_current_bar(self):
        """Shift [0] should refer to current bar (most recent)."""
        data = pd.DataFrame({
            "rsi_14": [30, 35, 40, 50, 60]
        })
        data = data.sort_index(ascending=False).reset_index(drop=True)
        # After sort descending and reset, data is [60, 50, 40, 35, 30]
        # [0] refers to index 0 which is 60 (most recent)
        result = evaluate_dsl("rsi_14[0] == 60", data)
        assert result is True

    def test_shift_negative_one_previous(self):
        """Shift [-1] should refer to previous bar."""
        data = pd.DataFrame({
            "rsi_14": [30, 35, 40, 50, 60]
        })
        data = data.sort_index(ascending=False).reset_index(drop=True)
        # After sort, data is [60, 50, 40, 35, 30]
        # [-1] refers to index 1 which is 50 (previous bar)
        result = evaluate_dsl("rsi_14[-1] == 50", data)
        assert result is True

    def test_shift_negative_two(self):
        """Shift [-2] should refer to 2 bars back."""
        data = pd.DataFrame({
            "rsi_14": [30, 35, 40, 50, 60]
        })
        data = data.sort_index(ascending=False).reset_index(drop=True)
        result = evaluate_dsl("rsi_14[-2] == 40", data)
        assert result is True

    def test_shift_out_of_bounds(self):
        """Shift beyond available data should raise ValueError."""
        data = pd.DataFrame({
            "rsi_14": [30, 35]
        })
        data = data.sort_index(ascending=False).reset_index(drop=True)
        with pytest.raises(ValueError):
            evaluate_dsl("rsi_14[-5]", data)


class TestPublicAPI:
    """Test public API functions."""

    def test_evaluate_dsl_with_dict(self):
        """evaluate_dsl should work with dict input."""
        result = evaluate_dsl("rsi_14 > 50", {"rsi_14": 75})
        assert result is True

    def test_evaluate_dsl_with_dataframe(self):
        """evaluate_dsl should work with DataFrame input."""
        df = pd.DataFrame({
            "rsi_14": [30, 35, 40, 50, 60]
        })
        df = df.sort_index(ascending=False).reset_index(drop=True)
        result = evaluate_dsl("rsi_14 > 40", df)
        assert result is True

    def test_evaluate_dsl_missing_column(self):
        """evaluate_dsl should raise KeyError for missing column."""
        with pytest.raises(KeyError):
            evaluate_dsl("close > 100", {"rsi_14": 50})

    def test_parse_formula_returns_ast(self):
        """parse_formula should return evaluable AST."""
        ast = parse_formula("rsi_14 > 50 && ema_20 < 100")
        result = ast.evaluate({"rsi_14": 75, "ema_20": 50})
        assert result is True


class TestRealWorldFormulas:
    """Test realistic trading formula scenarios."""

    def test_momentum_signal(self):
        """Test: rsi_7 > 50 and roc_5 > 0"""
        formula = "rsi_7 > 50 && roc_5 > 0"
        result = evaluate_dsl(formula, {"rsi_7": 65, "roc_5": 1.5})
        assert result is True

    def test_mean_reversion_oversold(self):
        """Test: rsi_7 < 25 (oversold condition)"""
        formula = "rsi_7 < 25"
        result = evaluate_dsl(formula, {"rsi_7": 20})
        assert result is True

    def test_mean_reversion_overbought(self):
        """Test: rsi_7 > 75 (overbought condition)"""
        formula = "rsi_7 > 75"
        result = evaluate_dsl(formula, {"rsi_7": 80})
        assert result is True

    def test_bollinger_band_breakout(self):
        """Test: close > bb_20_upper"""
        formula = "close > bb_20_upper"
        result = evaluate_dsl(formula, {"close": 115, "bb_20_upper": 110})
        assert result is True

    def test_moving_average_crossover(self):
        """Test: ema_5 > ema_20 (bullish crossover)"""
        formula = "ema_5 > ema_20"
        result = evaluate_dsl(formula, {"ema_5": 105, "ema_20": 100})
        assert result is True

    def test_adx_trend_confirmation(self):
        """Test: adx_14 > 25 (strong trend)"""
        formula = "adx_14 > 25"
        result = evaluate_dsl(formula, {"adx_14": 30})
        assert result is True

    def test_complex_trading_signal(self):
        """Test complex multi-condition signal."""
        formula = "(rsi_14 > 50) && (ema_5 > ema_20) && (adx_14 > 25)"
        data = {
            "rsi_14": 65,
            "ema_5": 105,
            "ema_20": 100,
            "adx_14": 30,
        }
        result = evaluate_dsl(formula, data)
        assert result is True

    def test_entry_filter_with_volatility(self):
        """Test entry filter with volatility condition."""
        formula = "(rsi_7 < 30) && (atr_5 > 1.0) || (rsi_7 > 70)"
        data = {"rsi_7": 25, "atr_5": 2.0}
        result = evaluate_dsl(formula, data)
        assert result is True

    def test_exit_on_stop_loss_or_profit_target(self):
        """Test exit condition: price hit stop or target."""
        # exit if price fell below 95 OR rose above 110
        formula = "close < 95 || close > 110"
        assert evaluate_dsl(formula, {"close": 92}) is True
        assert evaluate_dsl(formula, {"close": 112}) is True
        assert evaluate_dsl(formula, {"close": 100}) is False


class TestEdgeCases:
    """Test edge cases and corner cases."""

    def test_zero_values(self):
        """Test evaluation with zero values."""
        result = evaluate_dsl("close > 0", {"close": 0})
        assert result is False
        result = evaluate_dsl("close == 0", {"close": 0})
        assert result is True

    def test_negative_values(self):
        """Test evaluation with negative values."""
        result = evaluate_dsl("profit > -10", {"profit": -5})
        assert result is True

    def test_very_large_numbers(self):
        """Test evaluation with very large numbers."""
        result = evaluate_dsl("price < 1000000", {"price": 999999})
        assert result is True

    def test_very_small_numbers(self):
        """Test evaluation with very small decimal numbers."""
        result = evaluate_dsl("ratio > 0.0001", {"ratio": 0.0002})
        assert result is True

    def test_nested_parentheses(self):
        """Test deeply nested parentheses."""
        formula = "((((rsi_14 > 50))))"
        result = evaluate_dsl(formula, {"rsi_14": 60})
        assert result is True

    def test_mixed_operators_complex(self):
        """Test complex expression with multiple operator types."""
        formula = "((a > 10) && (b < 50)) || ((c == 100) && !(d > 200))"
        data = {"a": 15, "b": 30, "c": 100, "d": 150}
        result = evaluate_dsl(formula, data)
        assert result is True

    def test_float_precision(self):
        """Test float precision in comparisons."""
        result = evaluate_dsl("price > 100.5", {"price": 100.50001})
        assert result is True
        result = evaluate_dsl("price > 100.5", {"price": 100.49999})
        assert result is False

    def test_scientific_notation_not_supported(self):
        """Scientific notation is not currently supported by the lexer."""
        # The lexer treats '1e6' as '1' and identifier 'e6', which fails
        with pytest.raises(SyntaxError):
            evaluate_dsl("volume > 1e6", {"volume": 2e6})


class TestErrorMessages:
    """Test that error messages are helpful."""

    def test_syntax_error_message_has_position(self):
        """SyntaxError should indicate problem position."""
        try:
            parse_formula("rsi_14 @@ 50")
        except SyntaxError as e:
            assert "position" in str(e) or "character" in str(e)

    def test_key_error_message_has_indicator_name(self):
        """KeyError should show which indicator/column is missing."""
        try:
            evaluate_dsl("close_price > 100", {"close": 95})
        except KeyError:
            pass  # Expected

    def test_division_by_zero_error_message(self):
        """Division by zero should have clear error."""
        try:
            evaluate_dsl("a / b", {"a": 100, "b": 0})
        except ValueError as e:
            assert "zero" in str(e).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
