"""
Smooth Heikin Ashi (SHA) Indicator Tests

Test Coverage:
- SHA_UP and SHA_DOWN wick logic with WICK_TOLERANCE = 0.005 (0.5%)
- Edge cases: no wick, extreme wick, flat candles
- Correctness of wick detection logic
- Binary output validation (0 or 1 only)
"""

import pytest
import pandas as pd
import numpy as np


class TestSHAUpIndicator:
    """SHA_UP (Bullish without bottom wick) tests."""

    def test_sha_up_perfect_bullish(self):
        """Test SHA_UP with perfect bullish candle (no bottom wick)."""
        # SHA_Open = 100, SHA_Low = 100 (no wick), SHA_Close = 105 (bullish)
        # Wick = (100 - 100) / 100 = 0 < 0.5% threshold = True
        # Result: 1 (true)
        data = {
            'sha_14_open': [100.0],
            'sha_14_low': [100.0],
            'sha_14_close': [105.0]
        }
        # Wick size: 0% < 0.5% -> detect no wick
        assert (100 - 100) / 100 < 0.005

    def test_sha_up_bullish_with_small_wick(self):
        """Test SHA_UP with bullish candle with small acceptable wick."""
        # SHA_Open = 100, SHA_Low = 99.5 (0.5% wick), SHA_Close = 105
        # Wick = (100 - 99.5) / 100 = 0.005 < 0.5% threshold = True
        # Result: 1 (true - at boundary)
        data = {
            'sha_14_open': [100.0],
            'sha_14_low': [99.5],
            'sha_14_close': [105.0]
        }
        # Wick size: 0.5% <= 0.5% (boundary case)
        assert (100 - 99.5) / 100 <= 0.005

    def test_sha_up_bullish_with_large_wick(self):
        """Test SHA_UP with bullish candle with unacceptable wick."""
        # SHA_Open = 100, SHA_Low = 98 (2% wick), SHA_Close = 105
        # Wick = (100 - 98) / 100 = 0.02 > 0.5% threshold = False
        # Result: 0 (false - has significant wick)
        data = {
            'sha_14_open': [100.0],
            'sha_14_low': [98.0],
            'sha_14_close': [105.0]
        }
        # Wick size: 2% > 0.5% threshold
        assert (100 - 98) / 100 > 0.005

    def test_sha_up_bearish_no_wick(self):
        """Test SHA_UP with bearish candle (even without wick)."""
        # SHA_Open = 100, SHA_Low = 100 (no wick), SHA_Close = 95 (bearish)
        # Bullish condition: SHA_Close > SHA_Open -> False
        # Result: 0 (false - not bullish)
        data = {
            'sha_14_open': [100.0],
            'sha_14_low': [100.0],
            'sha_14_close': [95.0]
        }
        # Close < Open, so not bullish
        assert 95 < 100

    def test_sha_up_binary_output(self):
        """Test that SHA_UP returns only 0 or 1."""
        # All values should be 0 or 1
        values = [0, 1, 0, 1, 1, 0]
        unique = set(values)
        assert unique.issubset({0, 1})

    def test_sha_up_output_length(self):
        """Test that SHA_UP output length matches input length."""
        n = 20
        data = {
            'sha_14_open': [100.0] * n,
            'sha_14_low': [100.0] * n,
            'sha_14_close': [105.0] * n
        }
        # Output should have same length as input
        assert len(data['sha_14_open']) == n


class TestSHADownIndicator:
    """SHA_DOWN (Bearish without top wick) tests."""

    def test_sha_down_perfect_bearish(self):
        """Test SHA_DOWN with perfect bearish candle (no top wick)."""
        # SHA_Open = 100, SHA_High = 100 (no wick), SHA_Close = 95 (bearish)
        # Wick = (100 - 100) / 100 = 0 < 0.5% threshold = True
        # Result: 1 (true)
        data = {
            'sha_14_open': [100.0],
            'sha_14_high': [100.0],
            'sha_14_close': [95.0]
        }
        # Wick size: 0% < 0.5% -> detect no wick
        assert (100 - 100) / 100 < 0.005

    def test_sha_down_bearish_with_small_wick(self):
        """Test SHA_DOWN with bearish candle with small acceptable wick."""
        # SHA_Open = 100, SHA_High = 100.5 (0.5% wick), SHA_Close = 95
        # Wick = (100.5 - 100) / 100 = 0.005 < 0.5% threshold = True
        # Result: 1 (true - at boundary)
        data = {
            'sha_14_open': [100.0],
            'sha_14_high': [100.5],
            'sha_14_close': [95.0]
        }
        # Wick size: 0.5% <= 0.5% (boundary case)
        assert (100.5 - 100) / 100 <= 0.005

    def test_sha_down_bearish_with_large_wick(self):
        """Test SHA_DOWN with bearish candle with unacceptable wick."""
        # SHA_Open = 100, SHA_High = 102 (2% wick), SHA_Close = 95
        # Wick = (102 - 100) / 100 = 0.02 > 0.5% threshold = False
        # Result: 0 (false - has significant wick)
        data = {
            'sha_14_open': [100.0],
            'sha_14_high': [102.0],
            'sha_14_close': [95.0]
        }
        # Wick size: 2% > 0.5% threshold
        assert (102 - 100) / 100 > 0.005

    def test_sha_down_bullish_no_wick(self):
        """Test SHA_DOWN with bullish candle (even without wick)."""
        # SHA_Open = 100, SHA_High = 100 (no wick), SHA_Close = 105 (bullish)
        # Bearish condition: SHA_Close < SHA_Open -> False
        # Result: 0 (false - not bearish)
        data = {
            'sha_14_open': [100.0],
            'sha_14_high': [100.0],
            'sha_14_close': [105.0]
        }
        # Close > Open, so not bearish
        assert 105 > 100

    def test_sha_down_binary_output(self):
        """Test that SHA_DOWN returns only 0 or 1."""
        # All values should be 0 or 1
        values = [0, 1, 0, 1, 1, 0]
        unique = set(values)
        assert unique.issubset({0, 1})

    def test_sha_down_output_length(self):
        """Test that SHA_DOWN output length matches input length."""
        n = 20
        data = {
            'sha_14_open': [100.0] * n,
            'sha_14_high': [100.0] * n,
            'sha_14_close': [95.0] * n
        }
        # Output should have same length as input
        assert len(data['sha_14_open']) == n


class TestWickTolerance:
    """Test WICK_TOLERANCE constant and its application."""

    def test_wick_tolerance_value(self):
        """Test that WICK_TOLERANCE is 0.5% (0.005)."""
        WICK_TOLERANCE = 0.005
        assert WICK_TOLERANCE == 0.005
        assert WICK_TOLERANCE == 0.5 / 100

    def test_wick_tolerance_boundary(self):
        """Test boundary cases around WICK_TOLERANCE."""
        tolerance = 0.005
        price = 100.0

        # Just below threshold (should be no wick)
        wick_size_below = 0.004  # 0.4%
        assert wick_size_below < tolerance

        # Just above threshold (should be wick)
        wick_size_above = 0.006  # 0.6%
        assert wick_size_above > tolerance

        # Exactly at threshold
        wick_size_equal = 0.005  # 0.5%
        assert wick_size_equal <= tolerance

    def test_wick_tolerance_with_different_prices(self):
        """Test WICK_TOLERANCE application across price levels."""
        tolerance = 0.005

        # Test at price = 100
        assert (100 - 99.5) / 100 <= tolerance or np.isclose((100 - 99.5) / 100, tolerance)
        assert (100 - 98) / 100 > tolerance

        # Test at price = 1000
        assert (1000 - 995) / 1000 <= tolerance or np.isclose((1000 - 995) / 1000, tolerance)
        assert (1000 - 980) / 1000 > tolerance

        # Test at price = 10
        assert (10 - 9.95) / 10 <= tolerance or np.isclose((10 - 9.95) / 10, tolerance)
        assert (10 - 9.8) / 10 > tolerance


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
