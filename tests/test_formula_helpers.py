"""Test suite for formula helpers and public API.

Tests calculator.py, dsl_helpers.py, and numeric_evaluator.py
"""

import pytest
import pandas as pd
import numpy as np
from src.tools.formula.calculator import evaluate
from src.tools.formula.dsl_helpers import is_dsl_formula, simplify_formula
from src.tools.formula.numeric_evaluator import evaluate_numeric_formula, evaluate_position_size


class TestDSLHelpers:
    """Test DSL helper functions."""

    def test_is_dsl_formula_with_shift_notation(self):
        """is_dsl_formula should detect shift notation."""
        assert is_dsl_formula("rsi_14[0]") is True
        assert is_dsl_formula("ema_20[-1]") is True
        assert is_dsl_formula("close[5]") is True

    def test_is_dsl_formula_with_dsl_operators(self):
        """is_dsl_formula should detect DSL operators."""
        assert is_dsl_formula("rsi_14 && ema_20") is True
        assert is_dsl_formula("rsi_14 || ema_20") is True
        assert is_dsl_formula("!close") is True

    def test_is_dsl_formula_negative(self):
        """is_dsl_formula should return False for non-DSL formulas."""
        assert is_dsl_formula("rsi_14 > 50") is False
        assert is_dsl_formula("close") is False
        assert is_dsl_formula("100") is False

    def test_is_dsl_formula_edge_cases(self):
        """is_dsl_formula should handle edge cases."""
        assert is_dsl_formula("") is False
        assert is_dsl_formula("data['close']") is False


class TestSimplifyFormula:
    """Test formula simplification from DSL to pandas syntax."""

    def test_simplify_shift_zero(self):
        """simplify_formula should convert indicator[0] to data['indicator']."""
        result = simplify_formula("rsi_14[0]")
        assert "data['rsi_14']" in result

    def test_simplify_shift_negative(self):
        """simplify_formula should convert indicator[-1] to data.shift(1)['indicator']."""
        result = simplify_formula("rsi_14[-1]")
        assert "shift(1)" in result
        assert "rsi_14" in result

    def test_simplify_shift_negative_two(self):
        """simplify_formula should handle deeper shifts."""
        result = simplify_formula("rsi_14[-2]")
        assert "shift(2)" in result

    def test_simplify_multiple_indicators(self):
        """simplify_formula should handle multiple indicators."""
        result = simplify_formula("rsi_14[0] < ema_20[-1]")
        assert "data['rsi_14']" in result
        assert "ema_20" in result
        assert "shift" in result

    def test_simplify_does_not_break_pandas_syntax(self):
        """simplify_formula should leave pandas syntax unchanged."""
        original = "data['close'] > 100"
        result = simplify_formula(original)
        assert result == original


class TestCalculator:
    """Test public evaluate() function."""

    def test_evaluate_dsl_formula_with_shift(self):
        """evaluate() should handle DSL formulas with shift notation."""
        df = pd.DataFrame({"rsi_14": [30, 35, 40, 50, 60]})
        df = df.sort_index(ascending=False).reset_index(drop=True)
        # Use shift notation to trigger DSL path
        result = evaluate("rsi_14[0] > 50", df)
        assert result is True

    def test_evaluate_dsl_formula_with_operators(self):
        """evaluate() should handle DSL formulas with && and ||."""
        data = {"rsi_7": 35, "rsi_14": 45}
        # Use && operator to trigger DSL path
        result = evaluate("rsi_7 < 40 && rsi_14 > 40", data)
        assert result is True

    def test_evaluate_traditional_pandas_syntax(self):
        """evaluate() should support traditional pandas syntax."""
        result = evaluate("data['close'] > 100", {"close": 150})
        assert result is True

    def test_evaluate_empty_formula(self):
        """evaluate() should reject empty formulas."""
        with pytest.raises(ValueError):
            evaluate("", {"close": 100})

    def test_evaluate_with_dict_input(self):
        """evaluate() should work with dict input."""
        data = {"rsi_7": 35, "rsi_14": 45, "ema_20": 100, "close": 95}
        # Use && to trigger DSL path
        result = evaluate("rsi_7 < 40 && rsi_14 < 50", data)
        assert isinstance(result, bool)

    def test_evaluate_with_dataframe_input(self):
        """evaluate() should work with DataFrame input."""
        df = pd.DataFrame({
            "rsi_14": [30, 35, 40, 50, 60],
            "close": [95, 100, 105, 110, 115],
        })
        df = df.sort_index(ascending=False).reset_index(drop=True)
        # Use shift notation to trigger DSL path
        result = evaluate("rsi_14[0] > 25", df)
        assert result is True

    def test_evaluate_complex_condition(self):
        """evaluate() should handle complex conditions."""
        data = {
            "rsi_14": 65,
            "ema_5": 105,
            "ema_20": 100,
            "adx_14": 30,
        }
        formula = "(rsi_14 > 50) && (ema_5 > ema_20) && (adx_14 > 25)"
        result = evaluate(formula, data)
        assert result is True

    def test_evaluate_returns_boolean(self):
        """evaluate() should return boolean."""
        # Use && to trigger DSL path which evaluates to bool
        result = evaluate("10 > 5 && 20 > 15", {})
        assert isinstance(result, bool)


class TestNumericEvaluator:
    """Test numeric formula evaluation."""

    def test_evaluate_numeric_formula_simple(self):
        """evaluate_numeric_formula should return float."""
        result = evaluate_numeric_formula("100 * 1.5", {})
        assert result == 150.0

    def test_evaluate_numeric_formula_with_data(self):
        """evaluate_numeric_formula should use data values."""
        result = evaluate_numeric_formula("data['close'] * 1.05", {"close": 100})
        assert result == 105.0

    def test_evaluate_numeric_formula_dsl_conversion(self):
        """evaluate_numeric_formula should convert DSL syntax."""
        result = evaluate_numeric_formula("close[0] * 2", {"close": 50})
        assert result == 100.0

    def test_evaluate_numeric_formula_division(self):
        """evaluate_numeric_formula should handle division."""
        result = evaluate_numeric_formula("1000 / data['close']", {"close": 10})
        assert result == 100.0

    def test_evaluate_numeric_formula_with_functions(self):
        """evaluate_numeric_formula should support allowed functions."""
        result = evaluate_numeric_formula("max(100, 150)", {})
        assert result == 150.0

        result = evaluate_numeric_formula("min(100, 150)", {})
        assert result == 100.0

        result = evaluate_numeric_formula("abs(-50)", {})
        assert result == 50.0

    def test_evaluate_numeric_formula_rounding(self):
        """evaluate_numeric_formula should support rounding."""
        result = evaluate_numeric_formula("round(3.7)", {})
        assert result == 4.0

    def test_evaluate_numeric_formula_disabled_false(self):
        """evaluate_numeric_formula should return None for 'false'."""
        result = evaluate_numeric_formula("false", {})
        assert result is None

    def test_evaluate_numeric_formula_empty(self):
        """evaluate_numeric_formula should return None for empty."""
        result = evaluate_numeric_formula("", {})
        assert result is None

    def test_evaluate_numeric_formula_with_dataframe(self):
        """evaluate_numeric_formula should work with DataFrame."""
        df = pd.DataFrame({
            "close": [95, 100, 105],
            "atr": [2, 2.5, 3],
        })
        df = df.sort_index(ascending=False).reset_index(drop=True)
        result = evaluate_numeric_formula("data['close'] * 1.05", df)
        # After sort descending, first row is largest value (105)
        assert result == pytest.approx(105 * 1.05)

    def test_evaluate_numeric_formula_dict_case_sensitivity(self):
        """evaluate_numeric_formula handles dicts as-is (case sensitive)."""
        # Dict keys are case-sensitive (not normalized for dict input)
        result = evaluate_numeric_formula("data['close'] * 2", {"close": 50})
        assert result == 100.0

        # Uppercase keys require uppercase references
        result = evaluate_numeric_formula("data['CLOSE'] * 2", {"CLOSE": 50})
        assert result == 100.0

    def test_evaluate_position_size_basic(self):
        """evaluate_position_size should return integer shares."""
        result = evaluate_position_size("1000 / data['close']", {"close": 50})
        assert result == 20
        assert isinstance(result, int)

    def test_evaluate_position_size_max_limit(self):
        """evaluate_position_size should respect max_shares limit."""
        result = evaluate_position_size("10000 / data['close']", {"close": 10}, max_shares=100)
        assert result == 100

    def test_evaluate_position_size_nan_result(self):
        """evaluate_position_size should return None for NaN."""
        result = evaluate_position_size("float('nan')", {})
        assert result is None

    def test_evaluate_position_size_inf_result(self):
        """evaluate_position_size should return None for Inf."""
        result = evaluate_position_size("float('inf')", {})
        assert result is None

    def test_evaluate_position_size_negative_result(self):
        """evaluate_position_size should ensure non-negative."""
        result = evaluate_position_size("-100", {})
        assert result == 0

    def test_evaluate_position_size_zero_result(self):
        """evaluate_position_size should handle zero."""
        result = evaluate_position_size("0", {})
        assert result == 0


class TestRealWorldNumericFormulas:
    """Test realistic numeric formula scenarios."""

    def test_position_sizing_formula(self):
        """Test: shares = account_size / price"""
        result = evaluate_position_size("10000 / data['close']", {"close": 50})
        assert result == 200

    def test_stop_loss_price_formula(self):
        """Test: stop_loss = entry_price * (1 - 0.02)"""
        result = evaluate_numeric_formula("data['entry'] * (1 - 0.02)", {"entry": 100})
        assert result == pytest.approx(98.0)

    def test_take_profit_formula(self):
        """Test: target = entry_price * (1 + 0.05)"""
        result = evaluate_numeric_formula("data['entry'] * (1 + 0.05)", {"entry": 100})
        assert result == pytest.approx(105.0)

    def test_risk_reward_ratio_formula(self):
        """Test: risk_reward = (target - entry) / (entry - stop)"""
        result = evaluate_numeric_formula(
            "(data['target'] - data['entry']) / (data['entry'] - data['stop'])",
            {"target": 110, "entry": 100, "stop": 95}
        )
        assert result == pytest.approx(2.0)  # (10) / (5) = 2

    def test_position_risk_formula(self):
        """Test: risk_usd = position_size * (entry - stop)"""
        result = evaluate_numeric_formula(
            "data['shares'] * (data['entry'] - data['stop'])",
            {"shares": 100, "entry": 100, "stop": 98}
        )
        assert result == 200.0

    def test_atr_based_stop_loss(self):
        """Test: stop_loss = close - (2 * atr)"""
        result = evaluate_numeric_formula(
            "data['close'] - (2 * data['atr'])",
            {"close": 100, "atr": 2.5}
        )
        assert result == 95.0

    def test_volatility_adjustment_formula(self):
        """Test: adjusted_position = base_size / (atr / close)"""
        result = evaluate_numeric_formula(
            "1000 / (data['atr'] / data['close'])",
            {"atr": 2, "close": 100}
        )
        assert result == 50000.0  # 1000 / (2/100) = 1000 / 0.02 = 50000


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_signal_calculation_pipeline(self):
        """Test complete signal calculation workflow."""
        # Calculate entry signal
        data = {
            "rsi_7": 22,      # Oversold
            "rsi_14": 28,     # Near oversold
            "bb_lower": 95,
            "close": 94,      # Below lower BB
            "ema_20": 105,    # Below trend
        }

        # Entry signal: oversold + below BB (use && to trigger DSL path)
        entry_signal = evaluate(
            "rsi_7 < 25 && close < bb_lower",
            data
        )
        assert entry_signal is True

        # Exit signal: recovered above EMA (use && to trigger DSL path)
        exit_signal = evaluate(
            "close > ema_20 || rsi_7 < 15",
            data
        )
        assert exit_signal is False

    def test_position_sizing_workflow(self):
        """Test complete position sizing workflow."""
        data = {
            "close": 50,
            "atr": 2,
        }

        # Calculate position size using DSL syntax
        account_size = 10000
        stop_distance = evaluate_numeric_formula("2 * data['atr']", data)
        position_size = evaluate_position_size(
            f"{account_size} / {stop_distance}",
            data,
            max_shares=200
        )

        assert position_size > 0
        assert position_size <= 200

    def test_multi_strategy_signals(self):
        """Test multiple strategies with different formulas."""
        data = {
            "rsi_7": 20,
            "rsi_14": 35,
            "ema_5": 105,
            "ema_20": 100,
            "adx_14": 40,
        }

        # Momentum strategy: strong trend + rsi (use && for DSL path)
        momentum = evaluate(
            "ema_5 > ema_20 && rsi_14 > 50 && adx_14 > 25",
            data
        )
        assert momentum is False  # rsi_14 is 35, not > 50

        # Mean reversion: oversold signal (use && for DSL path)
        mean_rev = evaluate(
            "rsi_7 < 25 || rsi_7 > 75",
            data
        )
        assert mean_rev is True

        # Trend following: EMA alignment
        trend = evaluate(
            "ema_5 > ema_20 && adx_14 > 30",
            data
        )
        assert trend is True


class TestPerformance:
    """Performance and efficiency tests."""

    def test_repeated_formula_evaluation(self):
        """Test evaluating same formula multiple times."""
        formula = "rsi_14 > 50 && ema_20 < close"

        results = []
        for i in range(1000):
            data = {
                "rsi_14": 50 + i % 50,
                "ema_20": 100 - i % 20,
                "close": 110,
            }
            results.append(evaluate(formula, data))

        assert len(results) == 1000
        assert all(isinstance(r, bool) for r in results)

    def test_numeric_evaluation_performance(self):
        """Test numeric formula evaluation performance."""
        results = []
        for i in range(1000):
            result = evaluate_numeric_formula(
                "data['close'] * (1 + 0.05)",
                {"close": 100 + i % 50}
            )
            results.append(result)

        assert len(results) == 1000
        assert all(isinstance(r, (float, type(None))) for r in results)
        # Most should be float (some may be None if formula is disabled)
        float_results = [r for r in results if r is not None]
        assert len(float_results) > 0


class TestBackwardCompatibility:
    """Test backward compatibility with pandas.eval syntax."""

    def test_pandas_eval_basic(self):
        """Test traditional pandas.eval syntax still works."""
        result = evaluate("data['close'] > 100", {"close": 150})
        assert result is True

    def test_pandas_eval_with_operators(self):
        """Test pandas.eval with operators."""
        result = evaluate("data['a'] > 10 and data['b'] < 50", {"a": 15, "b": 30})
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
