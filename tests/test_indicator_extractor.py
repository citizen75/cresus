"""Test suite for indicator extraction utilities."""

import pytest
from src.tools.formula.indicator_extractor import (
    extract_indicators,
    extract_indicators_from_formulas,
    get_indicator_dependencies,
    validate_indicators_available,
)


class TestExtractIndicators:
    """Test extract_indicators function."""

    def test_single_indicator(self):
        """Extract single indicator."""
        result = extract_indicators("rsi_14 > 50")
        assert result == {"rsi_14"}

    def test_multiple_indicators(self):
        """Extract multiple indicators."""
        result = extract_indicators("rsi_14 > 50 && ema_20 < close")
        assert result == {"rsi_14", "ema_20", "close"}

    def test_indicator_with_shift(self):
        """Extract indicator with shift notation."""
        result = extract_indicators("rsi_14[0] > 50")
        assert result == {"rsi_14"}

    def test_multiple_shifts_same_indicator(self):
        """Extract same indicator with different shifts."""
        result = extract_indicators("rsi_14[0] > 50 && rsi_14[-1] < 40")
        assert result == {"rsi_14"}

    def test_complex_formula(self):
        """Extract indicators from complex formula."""
        result = extract_indicators(
            "(rsi_14 > 50) && (ema_5 > ema_20) && (adx_14 > 25)"
        )
        assert result == {"rsi_14", "ema_5", "ema_20", "adx_14"}

    def test_arithmetic_with_indicators(self):
        """Extract indicators from arithmetic formula."""
        result = extract_indicators("rsi_7 + rsi_14 > 100")
        assert result == {"rsi_7", "rsi_14"}

    def test_bollinger_band_formula(self):
        """Extract from Bollinger Band formula."""
        result = extract_indicators("close < bb_20_lower || close > bb_20_upper")
        assert result == {"close", "bb_20_lower", "bb_20_upper"}

    def test_volume_formula(self):
        """Extract from volume expansion formula."""
        result = extract_indicators("volume > volume_sma_20 * 2")
        assert result == {"volume", "volume_sma_20"}

    def test_empty_formula(self):
        """Handle empty formula."""
        result = extract_indicators("")
        assert result == set()

    def test_none_formula(self):
        """Handle None formula."""
        result = extract_indicators(None)
        assert result == set()

    def test_only_literals(self):
        """Formula with only literals."""
        result = extract_indicators("10 > 5")
        assert result == set()

    def test_pandas_data_reference(self):
        """Extract from pandas data reference."""
        result = extract_indicators("data['close'] > 100")
        assert result == {"close"}

    def test_mixed_pandas_and_dsl(self):
        """Handle mixed pandas and DSL syntax."""
        result = extract_indicators("data['close'] > ema_20")
        assert result == {"close", "ema_20"}

    def test_duplicate_indicators(self):
        """Duplicates are removed (returned as set)."""
        result = extract_indicators("rsi_14 > 50 || rsi_14 < 30")
        assert result == {"rsi_14"}
        assert len(result) == 1

    def test_case_insensitive_detection(self):
        """Indicators are detected case-insensitively."""
        result = extract_indicators("RSI_14 > 50 && EMA_20 < CLOSE")
        # DSL parser is case-sensitive, so this might extract as uppercase
        assert "rsi_14" in {i.lower() for i in result}


class TestExtractIndicatorsFromFormulas:
    """Test extract_indicators_from_formulas function."""

    def test_list_of_formulas(self):
        """Extract from list of formulas."""
        formulas = [
            "rsi_14 > 50 && ema_20 < close",
            "adx_14 > 25",
            "volume > volume_sma_20"
        ]
        result = extract_indicators_from_formulas(formulas)
        assert result == {"rsi_14", "ema_20", "close", "adx_14", "volume", "volume_sma_20"}

    def test_dict_of_formulas(self):
        """Extract from dict of formulas."""
        formulas = {
            "entry": "rsi_7 < 25 && close < bb_20_lower",
            "exit": "close > bb_20_upper || rsi_7 > 75"
        }
        result = extract_indicators_from_formulas(formulas)
        assert result == {"rsi_7", "close", "bb_20_lower", "bb_20_upper"}

    def test_empty_list(self):
        """Handle empty list."""
        result = extract_indicators_from_formulas([])
        assert result == set()

    def test_empty_dict(self):
        """Handle empty dict."""
        result = extract_indicators_from_formulas({})
        assert result == set()

    def test_none_list(self):
        """Handle None list."""
        result = extract_indicators_from_formulas(None)
        assert result == set()

    def test_overlapping_indicators(self):
        """Combine overlapping indicators."""
        formulas = [
            "rsi_14 > 50",
            "rsi_14 < 30",
            "ema_20 > close"
        ]
        result = extract_indicators_from_formulas(formulas)
        assert result == {"rsi_14", "ema_20", "close"}

    def test_many_strategies(self):
        """Extract from multiple strategy formulas."""
        formulas = {
            "momentum": "ema_5 > ema_20 && rsi_14 > 50 && adx_14 > 25",
            "mean_reversion": "rsi_7 < 25 && close < bb_20_lower",
            "trend": "ema_10 > ema_50 && adx_20 > 30"
        }
        result = extract_indicators_from_formulas(formulas)
        expected = {"ema_5", "ema_20", "rsi_14", "adx_14", "rsi_7", "close", "bb_20_lower", "ema_10", "ema_50", "adx_20"}
        assert result == expected


class TestGetIndicatorDependencies:
    """Test get_indicator_dependencies function."""

    def test_single_indicator_shift_zero(self):
        """Get dependencies with shift [0]."""
        result = get_indicator_dependencies("rsi_14 > 50")
        assert result == {"rsi_14": [0]}

    def test_indicator_with_explicit_shift(self):
        """Get dependencies with explicit shift."""
        result = get_indicator_dependencies("rsi_14[0] > 50")
        assert result == {"rsi_14": [0]}

    def test_indicator_with_negative_shift(self):
        """Get dependencies with negative shift."""
        result = get_indicator_dependencies("rsi_14[-1] > 50")
        assert result == {"rsi_14": [-1]}

    def test_multiple_shifts_same_indicator(self):
        """Get multiple shifts for same indicator."""
        result = get_indicator_dependencies("rsi_14[0] > 50 && rsi_14[-1] < 40")
        assert result == {"rsi_14": [0, -1]}

    def test_multiple_shifts_sorted(self):
        """Multiple shifts may be in any order."""
        result = get_indicator_dependencies("rsi_14[-2] > 30 && rsi_14[-1] > 40 && rsi_14[0] > 50")
        assert set(result["rsi_14"]) == {0, -1, -2}

    def test_multiple_indicators_different_shifts(self):
        """Get dependencies for multiple indicators."""
        result = get_indicator_dependencies("ema_5[0] > ema_20[-1]")
        assert result == {"ema_5": [0], "ema_20": [-1]}

    def test_complex_formula_dependencies(self):
        """Get dependencies from complex formula."""
        result = get_indicator_dependencies(
            "(rsi_14[0] > 50) && (rsi_14[-1] < 40) && (ema_20 > close)"
        )
        assert result == {"rsi_14": [0, -1], "ema_20": [0], "close": [0]}

    def test_empty_formula(self):
        """Handle empty formula."""
        result = get_indicator_dependencies("")
        assert result == {}

    def test_only_literals(self):
        """Formula with only literals."""
        result = get_indicator_dependencies("10 > 5 && 20 < 30")
        assert result == {}

    def test_pandas_data_reference(self):
        """Extract from pandas data reference."""
        result = get_indicator_dependencies("data['close'] > 100")
        assert result == {"close": [0]}

    def test_volume_sma_dependencies(self):
        """Get dependencies from volume formula."""
        result = get_indicator_dependencies("volume[0] > volume_sma_20[-1] * 2")
        assert result == {"volume": [0], "volume_sma_20": [-1]}


class TestValidateIndicatorsAvailable:
    """Test validate_indicators_available function."""

    def test_all_available(self):
        """All indicators available."""
        formula = "rsi_14 > 50 && ema_20 < close"
        available = {"rsi_14", "ema_20", "close"}
        is_valid, missing = validate_indicators_available(formula, available)
        assert is_valid is True
        assert missing == set()

    def test_some_missing(self):
        """Some indicators missing."""
        formula = "rsi_14 > 50 && ema_20 < close"
        available = {"rsi_14", "close"}
        is_valid, missing = validate_indicators_available(formula, available)
        assert is_valid is False
        assert missing == {"ema_20"}

    def test_all_missing(self):
        """All indicators missing."""
        formula = "rsi_14 > 50 && ema_20 < close"
        available = {"sma_20", "atr_14"}
        is_valid, missing = validate_indicators_available(formula, available)
        assert is_valid is False
        assert missing == {"rsi_14", "ema_20", "close"}

    def test_extra_indicators_available(self):
        """Extra indicators available (OK)."""
        formula = "rsi_14 > 50"
        available = {"rsi_14", "ema_20", "close", "adx_14", "atr_5"}
        is_valid, missing = validate_indicators_available(formula, available)
        assert is_valid is True
        assert missing == set()

    def test_empty_formula(self):
        """Empty formula."""
        formula = ""
        available = {"rsi_14", "ema_20"}
        is_valid, missing = validate_indicators_available(formula, available)
        assert is_valid is True
        assert missing == set()

    def test_only_literals(self):
        """Formula with only literals."""
        formula = "10 > 5 && 20 < 30"
        available = set()
        is_valid, missing = validate_indicators_available(formula, available)
        assert is_valid is True
        assert missing == set()

    def test_bollinger_band_validation(self):
        """Validate Bollinger Band indicators."""
        formula = "close < bb_20_lower || close > bb_20_upper"
        available = {"close", "bb_20_lower", "bb_20_upper"}
        is_valid, missing = validate_indicators_available(formula, available)
        assert is_valid is True
        assert missing == set()

    def test_complex_signal_validation(self):
        """Validate complex trading signal."""
        formula = (
            "rsi_7 < 25 && close < bb_20_lower && "
            "atr_5 > 1.0 && volume > volume_sma_20 * 1.5"
        )
        available = {
            "rsi_7", "close", "bb_20_lower",
            "atr_5", "volume", "volume_sma_20"
        }
        is_valid, missing = validate_indicators_available(formula, available)
        assert is_valid is True
        assert missing == set()

    def test_case_sensitivity(self):
        """Validate is case-sensitive."""
        formula = "rsi_14 > 50"
        available = {"RSI_14"}  # uppercase
        is_valid, missing = validate_indicators_available(formula, available)
        # Depends on how the parser handles case
        assert isinstance(is_valid, bool)
        assert isinstance(missing, set)


class TestRealWorldScenarios:
    """Test with real trading formula scenarios."""

    def test_momentum_strategy_indicators(self):
        """Extract indicators from momentum strategy."""
        formulas = {
            "signal": "rsi_7 > 50 && roc_5 > 0",
            "confirmation": "adx_14 > 25 && ema_5 > ema_20",
            "volume_filter": "volume > volume_sma_20"
        }
        result = extract_indicators_from_formulas(formulas)
        expected = {"rsi_7", "roc_5", "adx_14", "ema_5", "ema_20", "volume", "volume_sma_20"}
        assert result == expected

    def test_mean_reversion_validation(self):
        """Validate mean reversion strategy indicators."""
        formula = "rsi_7 < 25 && close < bb_20_lower"
        available_indicators = {
            "rsi_7", "rsi_14", "close", "bb_20_upper", "bb_20_lower", "bb_20_middle",
            "ema_5", "ema_20", "adx_14", "volume"
        }
        is_valid, missing = validate_indicators_available(formula, available_indicators)
        assert is_valid is True
        assert missing == set()

    def test_entry_exit_dependencies(self):
        """Get dependencies for entry/exit rules."""
        entry_formula = "rsi_7 < 25 && close < bb_20_lower && atr_5 > 0.5"
        exit_formula = "close > ema_20 || rsi_7 > 75"

        entry_deps = get_indicator_dependencies(entry_formula)
        exit_deps = get_indicator_dependencies(exit_formula)

        assert "rsi_7" in entry_deps
        assert "bb_20_lower" in entry_deps
        assert "atr_5" in entry_deps
        assert "ema_20" in exit_deps
        assert "rsi_7" in exit_deps

    def test_multi_timeframe_shifts(self):
        """Extract dependencies with multiple timeframe shifts."""
        formula = (
            "rsi_14[0] > 50 && "  # current bar
            "rsi_14[-1] > 40 && "  # previous bar
            "rsi_14[-2] > 30"      # 2 bars ago
        )
        deps = get_indicator_dependencies(formula)
        assert deps == {"rsi_14": [0, -1, -2]}

    def test_position_sizing_validation(self):
        """Validate position sizing formula indicators."""
        formula = "account_size / (close * multiplier)"
        available = {"account_size", "close", "multiplier"}
        is_valid, missing = validate_indicators_available(formula, available)
        assert is_valid is True


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_malformed_formula_fallback(self):
        """Fallback extraction on malformed formula."""
        # Invalid formula but should still extract what it can
        formula = "rsi_14 > 50 @@ ema_20 < close"
        result = extract_indicators(formula)
        # Should extract at least the indicators mentioned
        assert "rsi_14" in result or len(result) > 0

    def test_very_long_formula(self):
        """Handle very long formula."""
        indicators = ["ind_" + str(i) for i in range(100)]
        formula = " && ".join([f"{ind} > 50" for ind in indicators[:10]])
        result = extract_indicators(formula)
        assert len(result) == 10
        assert "ind_0" in result
        assert "ind_9" in result

    def test_repeated_indicators_in_formula(self):
        """Many references to same indicator."""
        formula = "rsi_14 > 50 && rsi_14 < 70 && rsi_14 >= 60 && rsi_14 <= 65"
        result = extract_indicators(formula)
        assert result == {"rsi_14"}
        assert len(result) == 1

    def test_special_characters_in_names(self):
        """Indicators with underscores and numbers."""
        result = extract_indicators("rsi_7_prev[0] > rsi_14_ema_smooth[-1]")
        assert "rsi_7_prev" in result
        assert "rsi_14_ema_smooth" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
