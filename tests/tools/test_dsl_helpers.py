"""Tests for DSL formula simplification helpers."""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tools.formula.dsl_helpers import simplify_formula, is_dsl_formula, convert_formulas_in_dict
from tools.formula.calculator import evaluate
import pandas as pd


class TestDSLSimplification:
	"""Test DSL formula simplification."""

	def test_simplify_current_bar(self):
		"""Test converting [0] to current bar."""
		result = simplify_formula("sha_10_green[0] == 1")
		assert result == "data['sha_10_green'] == 1"

	def test_simplify_previous_bar(self):
		"""Test converting [-1] to previous bar."""
		result = simplify_formula("sha_10_red[-1] == 1")
		assert result == "data.shift(1)['sha_10_red'] == 1"

	def test_simplify_multiple_bars_back(self):
		"""Test converting [-2], [-3] etc."""
		result = simplify_formula("ema_20[-2] > close[-2]")
		assert result == "data.shift(2)['ema_20'] > data.shift(2)['close']"

	def test_simplify_future_bar(self):
		"""Test converting [1] for future bar (rare)."""
		result = simplify_formula("close[1]")
		assert result == "data.shift(-1)['close']"

	def test_simplify_mixed_syntax(self):
		"""Test mixing current and previous bars."""
		formula = "sha_10_green[0] == 1 and sha_10_red[-1] == 1"
		expected = "data['sha_10_green'] == 1 and data.shift(1)['sha_10_red'] == 1"
		assert simplify_formula(formula) == expected

	def test_simplify_complex_formula(self):
		"""Test complex formula with multiple indicators."""
		formula = "sha_10_green[-1] == 1 and ema_20[0] < close[0] and adx_14[0] > adx_14[-1]"
		result = simplify_formula(formula)
		
		assert "data.shift(1)['sha_10_green']" in result
		assert "data['ema_20']" in result
		assert "data['close']" in result
		assert "data['adx_14']" in result
		assert "data.shift(1)['adx_14']" in result

	def test_simplify_numeric_comparison(self):
		"""Test with numeric indicators."""
		result = simplify_formula("rsi_14[0] > 50 and rsi_14[-1] < 50")
		assert result == "data['rsi_14'] > 50 and data.shift(1)['rsi_14'] < 50"

	def test_simplify_underscored_indicators(self):
		"""Test indicators with underscores in name."""
		result = simplify_formula("sha_10_green[0] and ma_cross_50_200[-1]")
		assert "data['sha_10_green']" in result
		assert "data.shift(1)['ma_cross_50_200']" in result

	def test_no_simplification_needed(self):
		"""Test that traditional syntax is unchanged."""
		formula = "data['close'] > data['ema_20']"
		assert simplify_formula(formula) == formula

	def test_no_simplification_brackets_in_string(self):
		"""Test that brackets in string literals aren't affected."""
		formula = "data['description'] != '[0]' and close[0] > 100"
		result = simplify_formula(formula)
		assert "[0]" in result  # String literal unchanged
		assert "data['close']" in result  # DSL syntax converted

	def test_simplify_with_operators(self):
		"""Test with various comparison operators."""
		formulas = [
			("close[0] > 100", "data['close'] > 100"),
			("close[0] < 100", "data['close'] < 100"),
			("close[0] == 100", "data['close'] == 100"),
			("close[0] >= 100", "data['close'] >= 100"),
			("close[0] <= 100", "data['close'] <= 100"),
		]
		
		for original, expected in formulas:
			assert simplify_formula(original) == expected

	def test_is_dsl_formula_true(self):
		"""Test detecting DSL formulas."""
		assert is_dsl_formula("close[0]")
		assert is_dsl_formula("sha_10_green[-1]")
		assert is_dsl_formula("ema_20[0] > 100")

	def test_is_dsl_formula_false(self):
		"""Test non-DSL formulas."""
		assert not is_dsl_formula("data['close']")
		assert not is_dsl_formula("close > 100")
		assert not is_dsl_formula("data.shift(1)['close']")

	def test_convert_formulas_in_dict_single(self):
		"""Test converting formulas in a dictionary."""
		data = {
			"buy": "close[0] > ema_20[0]",
			"name": "test_strategy",
			"count": 42,
		}
		
		result = convert_formulas_in_dict(data)
		assert result["buy"] == "data['close'] > data['ema_20']"
		assert result["name"] == "test_strategy"
		assert result["count"] == 42

	def test_convert_formulas_in_dict_nested(self):
		"""Test converting formulas in nested dictionaries."""
		data = {
			"signals": {
				"trend": {
					"formula": "close[0] > ema_20[0]",
					"description": "Trend formula"
				},
				"momentum": {
					"formula": "rsi_14[0] > 50",
				}
			}
		}
		
		result = convert_formulas_in_dict(data)
		assert result["signals"]["trend"]["formula"] == "data['close'] > data['ema_20']"
		assert result["signals"]["momentum"]["formula"] == "data['rsi_14'] > 50"

	def test_convert_formulas_in_dict_with_list(self):
		"""Test converting formulas in lists."""
		data = {
			"formulas": [
				"close[0] > 100",
				"rsi_14[0] < 30",
			]
		}
		
		result = convert_formulas_in_dict(data)
		assert result["formulas"][0] == "data['close'] > 100"
		assert result["formulas"][1] == "data['rsi_14'] < 30"


class TestDSLEvaluationIntegration:
	"""Test DSL formulas with the evaluate function."""

	@pytest.fixture
	def sample_data(self):
		"""Create sample data dictionary."""
		return {
			"close": [100, 101, 102, 103, 104],
			"ema_20": [99, 99.5, 100, 100.5, 101],
			"sha_10_green": [0, 1, 1, 0, 1],
			"sha_10_red": [1, 0, 0, 1, 0],
			"rsi_14": [45, 50, 55, 40, 65],
		}

	def test_evaluate_dsl_current_bar(self, sample_data):
		"""Test evaluating DSL formula with current bar."""
		# Create a simple data dict for a single row
		row_data = {
			"close": 102,
			"ema_20": 100,
		}
		
		result = evaluate("close[0] > ema_20[0]", row_data)
		assert result is True

	def test_evaluate_dsl_with_dataframe(self, sample_data):
		"""Test evaluating DSL formula with DataFrame (shift capability)."""
		df = pd.DataFrame(sample_data)
		
		# Get the last row as a dict
		row_data = df.iloc[-1].to_dict()
		
		# Simple evaluation (no shift in single row)
		result = evaluate("rsi_14[0] > 50", row_data)
		assert result is True

	def test_evaluate_dsl_complex_formula(self):
		"""Test complex DSL formula."""
		data = {
			"sha_10_green": 1,
			"ema_20": 99,
			"close": 102,
		}
		
		result = evaluate("sha_10_green[0] == 1 and ema_20[0] < close[0]", data)
		assert result is True

	def test_evaluate_traditional_still_works(self):
		"""Test that traditional syntax still works."""
		data = {
			"close": 102,
			"ema_20": 100,
		}
		
		result = evaluate("data['close'] > data['ema_20']", data)
		assert result is True

	def test_evaluate_mixed_syntax(self):
		"""Test mixed DSL and traditional syntax."""
		data = {
			"close": 102,
			"ema_20": 100,
			"rsi_14": 55,
		}
		
		# Mix DSL and traditional notation
		formula = "close[0] > ema_20[0] and data['rsi_14'] > 50"
		result = evaluate(formula, data)
		assert result is True

	def test_evaluate_dsl_false_condition(self):
		"""Test DSL formula that evaluates to false."""
		data = {
			"close": 98,
			"ema_20": 100,
		}
		
		result = evaluate("close[0] > ema_20[0]", data)
		assert result is False

	def test_evaluate_dsl_with_logic_operators(self):
		"""Test DSL with and/or operators."""
		data = {
			"close": 102,
			"ema_20": 100,
			"rsi_14": 40,
		}
		
		# AND operator
		result = evaluate("close[0] > ema_20[0] and rsi_14[0] > 50", data)
		assert result is False  # rsi_14 is 40, not > 50
		
		# OR operator
		result = evaluate("close[0] > ema_20[0] or rsi_14[0] > 50", data)
		assert result is True  # close > ema_20 is true


class TestDSLEdgeCases:
	"""Test edge cases and error handling."""

	def test_empty_formula(self):
		"""Test empty formula raises error."""
		with pytest.raises(ValueError):
			evaluate("", {})

	def test_invalid_formula_syntax(self):
		"""Test invalid formula raises error."""
		with pytest.raises(ValueError):
			evaluate("close[0] >>>> 100", {"close": 100})

	def test_dsl_with_missing_column(self):
		"""Test DSL formula with missing column."""
		with pytest.raises(ValueError):
			evaluate("missing_column[0] > 100", {"close": 100})

	def test_dsl_zero_and_negative_indices(self):
		"""Test mixing zero and negative indices."""
		formula = "close[0] > close[-1] and close[-1] > close[-2]"
		result = simplify_formula(formula)
		
		assert "data['close']" in result
		assert "data.shift(1)['close']" in result
		assert "data.shift(2)['close']" in result

	def test_indicator_names_with_numbers(self):
		"""Test indicator names with multiple numbers."""
		formula = "macd_12_26_9[0] > signal_12_26_9[-1]"
		result = simplify_formula(formula)
		
		assert "data['macd_12_26_9']" in result
		assert "data.shift(1)['signal_12_26_9']" in result

	def test_very_far_back_bar(self):
		"""Test accessing very far back bars."""
		formula = "close[-100]"
		result = simplify_formula(formula)
		assert result == "data.shift(100)['close']"

	def test_dsl_preserves_spacing(self):
		"""Test that simplification preserves formula readability."""
		formula = "close[0] > ema_20[0]   and   rsi_14[0] < 70"
		result = simplify_formula(formula)
		
		# Spacing should be preserved (between comparisons)
		assert "and" in result
		assert result.count("and") == 1


if __name__ == '__main__':
	pytest.main([__file__, '-v'])
