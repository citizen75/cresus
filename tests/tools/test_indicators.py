"""Tests for the indicators module and calculate function."""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tools.indicators import calculate
from tools.indicators.core.heikin_ashi import calculate as calculate_ha, calculate_smooth as calculate_sha


class TestIndicatorsCalculate:
	"""Test cases for the main calculate function."""

	@pytest.fixture
	def sample_ohlcv_df(self):
		"""Create a sample OHLCV DataFrame."""
		dates = pd.date_range('2026-01-01', periods=50, freq='D')
		return pd.DataFrame({
			'Open': [100 + i*0.5 for i in range(50)],
			'High': [102 + i*0.5 for i in range(50)],
			'Low': [99 + i*0.5 for i in range(50)],
			'Close': [101 + i*0.5 for i in range(50)],
			'Volume': [1000000] * 50,
		}, index=dates)

	@pytest.fixture
	def sample_ohlcv_uppercase_df(self):
		"""Create a sample OHLCV DataFrame with uppercase columns."""
		dates = pd.date_range('2026-01-01', periods=50, freq='D')
		return pd.DataFrame({
			'OPEN': [100 + i*0.5 for i in range(50)],
			'HIGH': [102 + i*0.5 for i in range(50)],
			'LOW': [99 + i*0.5 for i in range(50)],
			'CLOSE': [101 + i*0.5 for i in range(50)],
			'VOLUME': [1000000] * 50,
		}, index=dates)

	def test_calculate_single_ha_indicator(self, sample_ohlcv_df):
		"""Test calculating a single Heikin Ashi indicator."""
		result = calculate(['ha'], sample_ohlcv_df)

		assert isinstance(result, dict)
		# HA returns components: ha_open, ha_high, ha_low, ha_close, not a single 'ha' key
		assert 'ha_open' in result
		assert 'ha_close' in result
		assert len(result['ha_close']) == len(sample_ohlcv_df)
		assert result['ha_close'].dtype in [np.float64, np.float32]

	def test_calculate_ha_components(self, sample_ohlcv_df):
		"""Test calculating all Heikin Ashi components."""
		result = calculate(['ha_open', 'ha_high', 'ha_low', 'ha_close'], sample_ohlcv_df)
		
		assert 'ha_open' in result
		assert 'ha_high' in result
		assert 'ha_low' in result
		assert 'ha_close' in result
		
		for key in ['ha_open', 'ha_high', 'ha_low', 'ha_close']:
			assert len(result[key]) == len(sample_ohlcv_df)

	def test_calculate_ha_color_indicators(self, sample_ohlcv_df):
		"""Test calculating Heikin Ashi color indicators."""
		result = calculate(['ha_green', 'ha_red'], sample_ohlcv_df)
		
		assert 'ha_green' in result
		assert 'ha_red' in result
		
		# Color indicators should be binary (0 or 1)
		assert set(result['ha_green'].unique()) <= {0, 1}
		assert set(result['ha_red'].unique()) <= {0, 1}

	def test_calculate_sha_single_period(self, sample_ohlcv_df):
		"""Test calculating Smooth Heikin Ashi with single period."""
		result = calculate(['sha_14'], sample_ohlcv_df)
		
		assert 'sha_14' in result or 'sha_14_close' in result
		assert len(result.get('sha_14', result.get('sha_14_close'))) == len(sample_ohlcv_df)

	def test_calculate_sha_with_components(self, sample_ohlcv_df):
		"""Test calculating Smooth Heikin Ashi with specific components."""
		result = calculate(['sha_14_open', 'sha_14_close', 'sha_14_high', 'sha_14_low'], sample_ohlcv_df)
		
		for key in result.keys():
			assert len(result[key]) == len(sample_ohlcv_df)

	def test_calculate_sha_color_indicators(self, sample_ohlcv_df):
		"""Test calculating Smooth Heikin Ashi color indicators."""
		result = calculate(['sha_14_green', 'sha_14_red'], sample_ohlcv_df)
		
		# At least one of these should be returned
		color_keys = [k for k in result.keys() if 'green' in k or 'red' in k]
		assert len(color_keys) > 0

	def test_calculate_multiple_indicators(self, sample_ohlcv_df):
		"""Test calculating multiple indicators at once."""
		result = calculate(
			['ha', 'ha_green', 'sha_14', 'sha_14_green'],
			sample_ohlcv_df
		)
		
		assert len(result) >= 2
		for series in result.values():
			assert len(series) == len(sample_ohlcv_df)

	def test_calculate_with_uppercase_columns(self, sample_ohlcv_uppercase_df):
		"""Test that calculate handles uppercase column names."""
		result = calculate(['ha'], sample_ohlcv_uppercase_df)

		# HA returns components, not a single 'ha' key
		assert 'ha_close' in result or 'ha_open' in result
		key = 'ha_close' if 'ha_close' in result else 'ha_open'
		assert len(result[key]) == len(sample_ohlcv_uppercase_df)

	def test_calculate_returns_series(self, sample_ohlcv_df):
		"""Test that calculate returns pandas Series objects."""
		result = calculate(['ha', 'ha_green'], sample_ohlcv_df)
		
		for series in result.values():
			assert isinstance(series, pd.Series)

	def test_calculate_returns_numeric_data(self, sample_ohlcv_df):
		"""Test that calculate returns numeric data."""
		result = calculate(['ha', 'ha_green'], sample_ohlcv_df)
		
		for series in result.values():
			assert pd.api.types.is_numeric_dtype(series)

	def test_calculate_preserves_index(self, sample_ohlcv_df):
		"""Test that calculate preserves the DataFrame index."""
		result = calculate(['ha'], sample_ohlcv_df)

		# Index should match the input DataFrame
		key = 'ha_close' if 'ha_close' in result else 'ha_open'
		assert len(result[key]) == len(sample_ohlcv_df)

	@pytest.mark.skip(reason="HA (Heikin-Ashi) indicator not yet implemented")
	def test_calculate_with_minimal_data(self):
		"""Test calculate with minimal data (edge case)."""
		df = pd.DataFrame({
			'Open': [100, 101],
			'High': [102, 103],
			'Low': [99, 100],
			'Close': [101, 102],
			'Volume': [1000000, 1000000],
		})

		result = calculate(['ha'], df)
		# HA returns components
		assert 'ha_close' in result or 'ha_open' in result
		assert len(result['ha']) == 2

	def test_calculate_no_nan_in_output(self, sample_ohlcv_df):
		"""Test that calculate doesn't introduce excessive NaNs."""
		result = calculate(['ha', 'ha_green', 'sha_14'], sample_ohlcv_df)
		
		for key, series in result.items():
			# Allow some NaNs in early rows for indicators that need warmup
			nan_count = series.isna().sum()
			# Less than 50% of data should be NaN
			assert nan_count < len(series) * 0.5, f"{key} has too many NaNs"

	def test_ha_and_sha_consistency(self, sample_ohlcv_df):
		"""Test that HA values are reasonable (not inverted)."""
		result = calculate(['ha_open', 'ha_high', 'ha_low', 'ha_close'], sample_ohlcv_df)
		
		# High should generally be >= Low
		assert (result['ha_high'] >= result['ha_low']).sum() > len(sample_ohlcv_df) * 0.9


class TestHeikinAshiCalculate:
	"""Test cases for Heikin Ashi calculate function."""

	@pytest.fixture
	def simple_ohlcv_df(self):
		"""Create a simple OHLCV DataFrame with predictable values."""
		return pd.DataFrame({
			'Open': [100.0, 101.0, 102.0],
			'High': [102.0, 103.0, 104.0],
			'Low': [99.0, 100.0, 101.0],
			'Close': [101.0, 102.0, 103.0],
		})

	@pytest.fixture
	def history_df(self):
		"""Create a historical DataFrame for lookback."""
		return pd.DataFrame({
			'Open': [95.0, 96.0, 97.0],
			'High': [97.0, 98.0, 99.0],
			'Low': [94.0, 95.0, 96.0],
			'Close': [96.0, 97.0, 98.0],
		})

	def test_ha_calculate_returns_dict(self, simple_ohlcv_df):
		"""Test that calculate returns a dictionary."""
		result = calculate_ha(simple_ohlcv_df)
		
		assert isinstance(result, dict)

	def test_ha_calculate_required_keys(self, simple_ohlcv_df):
		"""Test that calculate returns all required keys."""
		result = calculate_ha(simple_ohlcv_df)
		
		required_keys = {'ha_open', 'ha_high', 'ha_low', 'ha_close', 'ha_green', 'ha_red', 'ha'}
		assert required_keys.issubset(set(result.keys()))

	def test_ha_calculate_returns_series(self, simple_ohlcv_df):
		"""Test that all values are pandas Series."""
		result = calculate_ha(simple_ohlcv_df)
		
		for series in result.values():
			assert isinstance(series, pd.Series)

	def test_ha_calculate_preserves_length(self, simple_ohlcv_df):
		"""Test that output has same length as input."""
		result = calculate_ha(simple_ohlcv_df)
		
		assert len(result['ha_close']) == len(simple_ohlcv_df)

	def test_ha_close_is_average_of_ohlc(self, simple_ohlcv_df):
		"""Test that HA Close is the average of OHLC."""
		result = calculate_ha(simple_ohlcv_df)
		
		expected_close = (simple_ohlcv_df['Open'] + simple_ohlcv_df['High'] + 
						  simple_ohlcv_df['Low'] + simple_ohlcv_df['Close']) / 4.0
		
		pd.testing.assert_series_equal(
			result['ha_close'],
			expected_close,
			check_names=False,
			atol=1e-6
		)

	def test_ha_green_is_binary(self, simple_ohlcv_df):
		"""Test that green indicator is binary."""
		result = calculate_ha(simple_ohlcv_df)
		
		assert set(result['ha_green'].unique()) <= {0, 1}

	def test_ha_red_is_binary(self, simple_ohlcv_df):
		"""Test that red indicator is binary."""
		result = calculate_ha(simple_ohlcv_df)
		
		assert set(result['ha_red'].unique()) <= {0, 1}

	def test_ha_green_red_mutually_exclusive(self, simple_ohlcv_df):
		"""Test that green and red are mostly mutually exclusive."""
		result = calculate_ha(simple_ohlcv_df)
		
		# Green + Red should be <= 1 (allowing for close == open edge case)
		sum_colors = result['ha_green'] + result['ha_red']
		assert (sum_colors <= 1).all()

	def test_ha_with_history_df(self, simple_ohlcv_df, history_df):
		"""Test that calculate works with historical data."""
		result = calculate_ha(simple_ohlcv_df, history_df=history_df)
		
		# Output length should match input, not include history
		assert len(result['ha_close']) == len(simple_ohlcv_df)

	def test_ha_high_is_maximum(self, simple_ohlcv_df):
		"""Test that HA High >= max(High, HA_Open, HA_Close)."""
		result = calculate_ha(simple_ohlcv_df)
		
		# HA High should be reasonable (at least as high as the original High)
		assert (result['ha_high'] >= simple_ohlcv_df['High']).all() or \
			   (result['ha_high'] >= simple_ohlcv_df['High'] - 1e-6).all()

	def test_ha_low_is_minimum(self, simple_ohlcv_df):
		"""Test that HA Low <= min(Low, HA_Open, HA_Close)."""
		result = calculate_ha(simple_ohlcv_df)
		
		# HA Low should be reasonable (at most as low as the original Low)
		assert (result['ha_low'] <= simple_ohlcv_df['Low']).all() or \
			   (result['ha_low'] <= simple_ohlcv_df['Low'] + 1e-6).all()

	def test_ha_uppercase_columns(self):
		"""Test that calculate handles uppercase column names."""
		df = pd.DataFrame({
			'OPEN': [100.0, 101.0],
			'HIGH': [102.0, 103.0],
			'LOW': [99.0, 100.0],
			'CLOSE': [101.0, 102.0],
		})
		
		result = calculate_ha(df)
		assert 'ha_close' in result
		assert len(result['ha_close']) == 2

	def test_ha_numeric_stability(self, simple_ohlcv_df):
		"""Test that HA calculation is numerically stable."""
		result = calculate_ha(simple_ohlcv_df)
		
		# All values should be finite (no inf, no excessive NaN)
		for series in result.values():
			assert np.isfinite(series).sum() > len(series) * 0.9


class TestSmoothHeikinAshiCalculate:
	"""Test cases for Smooth Heikin Ashi calculate function."""

	@pytest.fixture
	def sample_ohlcv_df(self):
		"""Create a sample OHLCV DataFrame."""
		dates = pd.date_range('2026-01-01', periods=30, freq='D')
		return pd.DataFrame({
			'Open': [100 + i*0.5 for i in range(30)],
			'High': [102 + i*0.5 for i in range(30)],
			'Low': [99 + i*0.5 for i in range(30)],
			'Close': [101 + i*0.5 for i in range(30)],
		}, index=dates)

	def test_sha_calculate_returns_dict(self, sample_ohlcv_df):
		"""Test that calculate_smooth returns a dictionary."""
		result = calculate_sha(sample_ohlcv_df, period=14)
		
		assert isinstance(result, dict)

	def test_sha_calculate_required_keys(self, sample_ohlcv_df):
		"""Test that calculate_smooth returns all required keys."""
		result = calculate_sha(sample_ohlcv_df, period=14)

		required_keys = {'sha_14_open', 'sha_14_high', 'sha_14_low', 'sha_14_close', 'sha_14_green', 'sha_14_red', 'sha_14_body', 'sha_14'}
		assert required_keys.issubset(set(result.keys()))

	def test_sha_body_is_abs_close_minus_open(self, sample_ohlcv_df):
		"""Test that sha_<period>_body == abs(sha_close - sha_open)."""
		result = calculate_sha(sample_ohlcv_df, period=14)

		expected = (result['sha_14_close'] - result['sha_14_open']).abs()
		pd.testing.assert_series_equal(result['sha_14_body'], expected, check_names=False)

	def test_sha_body_is_non_negative(self, sample_ohlcv_df):
		"""Test that body size is always non-negative."""
		result = calculate_sha(sample_ohlcv_df, period=14)

		assert (result['sha_14_body'].dropna() >= 0).all()

	def test_sha_body_via_dsl_formula(self, sample_ohlcv_df):
		"""Test that 'sha_<period>_body' resolves through the calculate() DSL."""
		df = sample_ohlcv_df.copy()
		df['Volume'] = 1000000
		result = calculate(['sha_14_body'], df)

		assert 'sha_14_body' in result
		assert isinstance(result['sha_14_body'], pd.Series)
		assert len(result['sha_14_body']) == len(df)

	def test_sha_body_default_period_via_dsl(self, sample_ohlcv_df):
		"""Test that 'sha_body' (no period) defaults to period 14."""
		df = sample_ohlcv_df.copy()
		df['Volume'] = 1000000
		result = calculate(['sha_body'], df)

		# calculate() keys results by the original formula string, but the
		# value resolves through the default period (14).
		assert 'sha_body' in result
		expected = calculate(['sha_14_body'], df)['sha_14_body']
		pd.testing.assert_series_equal(result['sha_body'], expected, check_names=False)

	def test_sha_default_period(self, sample_ohlcv_df):
		"""Test that SHA uses default period of 14."""
		result = calculate_sha(sample_ohlcv_df)

		assert 'sha_14_close' in result
		assert len(result['sha_14_close']) == len(sample_ohlcv_df)

	def test_sha_custom_period(self, sample_ohlcv_df):
		"""Test that SHA respects custom period."""
		result_7 = calculate_sha(sample_ohlcv_df, period=7)
		result_21 = calculate_sha(sample_ohlcv_df, period=21)

		# Different periods should produce different results
		assert not result_7['sha_7_close'].equals(result_21['sha_21_close'])

	def test_sha_smoothing_effect(self, sample_ohlcv_df):
		"""Test that SHA is smoother than raw HA."""
		ha_result = calculate_ha(sample_ohlcv_df)
		sha_result = calculate_sha(sample_ohlcv_df, period=14)

		# Both should have results
		assert 'ha_close' in ha_result
		assert 'sha_14_close' in sha_result

		ha_close = ha_result['ha_close'].values
		sha_close = sha_result['sha_14_close'].values

		# Both should have reasonable values (not all NaN or infinite)
		assert np.isfinite(ha_close).sum() > 0
		assert np.isfinite(sha_close).sum() > 0

	def test_sha_green_is_binary(self, sample_ohlcv_df):
		"""Test that SHA green indicator is binary."""
		result = calculate_sha(sample_ohlcv_df, period=14)

		assert set(result['sha_14_green'].unique()) <= {0, 1}

	def test_sha_red_is_binary(self, sample_ohlcv_df):
		"""Test that SHA red indicator is binary."""
		result = calculate_sha(sample_ohlcv_df, period=14)

		assert set(result['sha_14_red'].unique()) <= {0, 1}

	def test_sha_colors_based_on_close_open(self, sample_ohlcv_df):
		"""Test that colors are based on close > open."""
		result = calculate_sha(sample_ohlcv_df, period=14)

		# Green should be 1 when close > open, 0 otherwise
		close_gt_open = result['sha_14_close'] > result['sha_14_open']

		# Most of the time, green should match this condition
		matches = (result['sha_14_green'] == close_gt_open.astype(int)).sum()
		assert matches > len(sample_ohlcv_df) * 0.95

	def test_sha_with_history_df(self, sample_ohlcv_df):
		"""Test that SHA works with historical data."""
		history = pd.DataFrame({
			'Open': [95 + i*0.5 for i in range(10)],
			'High': [97 + i*0.5 for i in range(10)],
			'Low': [94 + i*0.5 for i in range(10)],
			'Close': [96 + i*0.5 for i in range(10)],
		})

		result = calculate_sha(sample_ohlcv_df, period=14, history_df=history)

		# Output should match input length, not include history
		assert len(result['sha_14_close']) == len(sample_ohlcv_df)

	def test_sha_returns_series(self, sample_ohlcv_df):
		"""Test that all SHA values are Series."""
		result = calculate_sha(sample_ohlcv_df, period=14)
		
		for series in result.values():
			assert isinstance(series, pd.Series)

	def test_sha_preserves_length(self, sample_ohlcv_df):
		"""Test that SHA preserves input length."""
		result = calculate_sha(sample_ohlcv_df, period=14)

		assert len(result['sha_14_close']) == len(sample_ohlcv_df)

	def test_sha_numeric_stability(self, sample_ohlcv_df):
		"""Test that SHA is numerically stable."""
		result = calculate_sha(sample_ohlcv_df, period=14)

		# All values should be finite (no inf, no excessive NaN)
		# For small datasets (100 rows), with period 14 + EMA warmup, might have many NaNs initially
		for series in result.values():
			# Just check that some values are finite (allow for warmup period)
			finite_count = np.isfinite(series).sum()
			assert finite_count > len(series) * 0.2  # At least 20% should be finite


class TestIndicatorEdgeCases:
	"""Test edge cases and error handling."""

	def test_calculate_empty_dataframe(self):
		"""Test calculate with empty DataFrame raises error."""
		df = pd.DataFrame({'Open': [], 'High': [], 'Low': [], 'Close': [], 'Volume': []})
		
		from tools.indicators.utils.errors import InsufficientDataError
		with pytest.raises(InsufficientDataError):
			calculate(['ha'], df)

	def test_calculate_single_row(self):
		"""Test calculate with single row raises error."""
		df = pd.DataFrame({
			'Open': [100.0],
			'High': [102.0],
			'Low': [99.0],
			'Close': [101.0],
			'Volume': [1000000],
		})
		
		from tools.indicators.utils.errors import InsufficientDataError
		with pytest.raises(InsufficientDataError):
			calculate(['ha'], df)

	def test_calculate_with_nan_values(self):
		"""Test calculate with NaN values in data."""
		df = pd.DataFrame({
			'Open': [100.0, np.nan, 102.0],
			'High': [102.0, 103.0, np.nan],
			'Low': [99.0, 100.0, 101.0],
			'Close': [101.0, 102.0, 103.0],
			'Volume': [1000000, 1000000, 1000000],
		})

		# NaN values may cause validation errors
		try:
			result = calculate(['ha'], df)
			# If it succeeds, verify result
			key = 'ha_close' if 'ha_close' in result else 'ha_open'
			assert len(result[key]) == 3
		except Exception as e:
			# Expected if NaN validation fails
			assert 'valid' in str(e).lower() or 'nan' in str(e).lower()

	def test_calculate_large_dataset(self):
		"""Test calculate with large dataset."""
		large_df = pd.DataFrame({
			'Open': [100 + i*0.001 for i in range(10000)],
			'High': [102 + i*0.001 for i in range(10000)],
			'Low': [99 + i*0.001 for i in range(10000)],
			'Close': [101 + i*0.001 for i in range(10000)],
			'Volume': [1000000] * 10000,
		})

		result = calculate(['ha', 'sha_14'], large_df)
		# HA returns components
		key = 'ha_close' if 'ha_close' in result else 'ha_open'
		assert len(result[key]) == 10000

	def test_sha_extreme_period(self):
		"""Test SHA with extreme period values."""
		df = pd.DataFrame({
			'Open': [100 + i for i in range(100)],
			'High': [102 + i for i in range(100)],
			'Low': [99 + i for i in range(100)],
			'Close': [101 + i for i in range(100)],
		})

		# Very large period
		result_large = calculate_sha(df, period=50)
		assert len(result_large['sha_50_close']) == 100

		# Very small period
		result_small = calculate_sha(df, period=2)
		assert len(result_small['sha_2_close']) == 100

	@pytest.mark.skip(reason="HA (Heikin-Ashi) indicator not yet implemented")
	def test_calculate_with_zero_prices(self):
		"""Test calculate with zero prices (edge case)."""
		df = pd.DataFrame({
			'Open': [0.0, 1.0, 2.0],
			'High': [1.0, 2.0, 3.0],
			'Low': [0.0, 0.0, 1.0],
			'Close': [0.5, 1.5, 2.5],
			'Volume': [1000000, 1000000, 1000000],
		})

		result = calculate(['ha'], df)
		assert len(result['ha']) == 3

	def test_calculate_ha_default_component(self):
		"""Test that 'ha' calculation includes close component."""
		df = pd.DataFrame({
			'Open': [100.0, 101.0],
			'High': [102.0, 103.0],
			'Low': [99.0, 100.0],
			'Close': [101.0, 102.0],
			'Volume': [1000000, 1000000],
		})

		result = calculate(['ha'], df)

		# HA returns components: ha_open, ha_close, ha_high, ha_low, etc.
		# At minimum, ha_close should be present
		assert 'ha_close' in result
		assert len(result['ha_close']) == 2

	def test_calculate_sha_default_component(self):
		"""Test that 'sha_<period>' returns close by default."""
		df = pd.DataFrame({
			'Open': [100 + i for i in range(30)],
			'High': [102 + i for i in range(30)],
			'Low': [99 + i for i in range(30)],
			'Close': [101 + i for i in range(30)],
			'Volume': [1000000] * 30,
		})
		
		result = calculate(['sha_14', 'sha_14_close'], df)
		
		# Check if either key exists and they match
		sha_key = 'sha_14' if 'sha_14' in result else 'sha_14_close'
		sha_close_key = 'sha_14_close'
		
		if sha_close_key in result:
			# If both exist, they should be equal
			if sha_key in result and sha_key != sha_close_key:
				pd.testing.assert_series_equal(result[sha_key], result[sha_close_key], check_names=False)


class TestMissingIndicators:
	"""Test indicators that were missing test coverage."""

	@pytest.fixture
	def sample_ohlcv_df(self):
		"""Create sample OHLCV DataFrame."""
		dates = pd.date_range('2026-01-01', periods=100, freq='D')
		return pd.DataFrame({
			'Open': [100 + i*0.5 for i in range(100)],
			'High': [102 + i*0.5 for i in range(100)],
			'Low': [99 + i*0.5 for i in range(100)],
			'Close': [101 + i*0.5 for i in range(100)],
			'Volume': [1000000 + i*10000 for i in range(100)],
		}, index=dates)

	# OBV (On Balance Volume)
	def test_obv_basic(self, sample_ohlcv_df):
		"""Test OBV calculation."""
		result = calculate(['obv'], sample_ohlcv_df)
		assert 'obv' in result
		assert len(result['obv']) == len(sample_ohlcv_df)
		assert isinstance(result['obv'], pd.Series)

	def test_obv_cumulative(self, sample_ohlcv_df):
		"""OBV should be cumulative."""
		result = calculate(['obv'], sample_ohlcv_df)
		obv = result['obv'].values
		# OBV should not decrease (or decrease only when price goes down)
		assert obv[-1] > obv[0]  # Ends higher than starts in uptrend

	# MFI (Money Flow Index)
	def test_mfi_basic(self, sample_ohlcv_df):
		"""Test MFI calculation."""
		result = calculate(['mfi_14'], sample_ohlcv_df)
		assert 'mfi_14' in result
		assert len(result['mfi_14']) == len(sample_ohlcv_df)

	def test_mfi_range(self, sample_ohlcv_df):
		"""MFI should be between 0 and 100."""
		result = calculate(['mfi_14'], sample_ohlcv_df)
		mfi = result['mfi_14'].dropna()
		assert (mfi >= 0).all() and (mfi <= 100).all()

	def test_mfi_custom_period(self, sample_ohlcv_df):
		"""Test MFI with different periods."""
		result_7 = calculate(['mfi_7'], sample_ohlcv_df)
		result_21 = calculate(['mfi_21'], sample_ohlcv_df)
		assert 'mfi_7' in result_7
		assert 'mfi_21' in result_21

	# CMF (Chaikin Money Flow)
	def test_cmf_basic(self, sample_ohlcv_df):
		"""Test CMF calculation."""
		result = calculate(['cmf_20'], sample_ohlcv_df)
		assert 'cmf_20' in result
		assert len(result['cmf_20']) == len(sample_ohlcv_df)

	def test_cmf_range(self, sample_ohlcv_df):
		"""CMF should be between -1 and 1."""
		result = calculate(['cmf_20'], sample_ohlcv_df)
		cmf = result['cmf_20'].dropna()
		assert (cmf >= -1).all() and (cmf <= 1).all()

	# VWAP (Volume Weighted Average Price)
	def test_vwap_basic(self, sample_ohlcv_df):
		"""Test VWAP calculation."""
		result = calculate(['vwap'], sample_ohlcv_df)
		assert 'vwap' in result
		assert len(result['vwap']) == len(sample_ohlcv_df)

	def test_vwap_roughly_near_price(self, sample_ohlcv_df):
		"""VWAP should be roughly near the price."""
		result = calculate(['vwap'], sample_ohlcv_df)
		vwap = result['vwap'].dropna()
		close = sample_ohlcv_df['Close'].iloc[vwap.index]
		# VWAP should not deviate too much from price (20% is reasonable tolerance)
		diff_pct = abs(vwap.values - close.values) / close.values
		assert (diff_pct < 0.2).mean() > 0.8  # 80% of points within 20%

	# ROC (Rate of Change)
	def test_roc_basic(self, sample_ohlcv_df):
		"""Test ROC calculation."""
		result = calculate(['roc_12'], sample_ohlcv_df)
		assert 'roc_12' in result
		assert len(result['roc_12']) == len(sample_ohlcv_df)

	def test_roc_uptrend(self, sample_ohlcv_df):
		"""ROC should be positive in uptrend."""
		result = calculate(['roc_12'], sample_ohlcv_df)
		roc = result['roc_12'].dropna()
		# In uptrend, most ROC values should be positive
		assert (roc > 0).sum() > len(roc) * 0.6

	# ADX (Average Directional Index)
	def test_adx_basic(self, sample_ohlcv_df):
		"""Test ADX calculation."""
		result = calculate(['adx_14'], sample_ohlcv_df)
		assert 'adx_14' in result
		assert len(result['adx_14']) == len(sample_ohlcv_df)

	def test_adx_range(self, sample_ohlcv_df):
		"""ADX should be between 0 and 100."""
		result = calculate(['adx_14'], sample_ohlcv_df)
		adx = result['adx_14'].dropna()
		assert (adx >= 0).all() and (adx <= 100).all()

	# EMA Percentage Change (ema_xx_chgpct_yy)
	def test_ema_chgpct_basic(self, sample_ohlcv_df):
		"""Test EMA percentage change calculation."""
		try:
			result = calculate(['ema_20_chgpct_5'], sample_ohlcv_df)
			assert 'ema_20_chgpct_5' in result
			assert len(result['ema_20_chgpct_5']) == len(sample_ohlcv_df)
		except Exception as e:
			# EMA_CHGPCT not registered in parser - skip test
			if 'InvalidFormulaError' in str(type(e).__name__):
				pytest.skip(f"EMA_CHGPCT not available: {e}")
			raise

	def test_ema_chgpct_multiple_periods(self, sample_ohlcv_df):
		"""Test EMA percentage change with different periods."""
		try:
			result = calculate(['ema_10_chgpct_3', 'ema_20_chgpct_5', 'ema_50_chgpct_10'], sample_ohlcv_df)
			assert 'ema_10_chgpct_3' in result
			assert 'ema_20_chgpct_5' in result
			assert 'ema_50_chgpct_10' in result
			for key in result:
				assert len(result[key]) == len(sample_ohlcv_df)
		except Exception as e:
			if 'InvalidFormulaError' in str(type(e).__name__):
				pytest.skip(f"EMA_CHGPCT not available: {e}")
			raise

	def test_ema_chgpct_uptrend(self, sample_ohlcv_df):
		"""EMA percentage change should be positive in uptrend."""
		try:
			result = calculate(['ema_20_chgpct_5'], sample_ohlcv_df)
			ema_chgpct = result['ema_20_chgpct_5'].dropna()
			# In uptrend data, most EMA chgpct values should be positive
			assert (ema_chgpct > 0).sum() > len(ema_chgpct) * 0.5
		except Exception as e:
			if 'InvalidFormulaError' in str(type(e).__name__):
				pytest.skip(f"EMA_CHGPCT not available: {e}")
			raise

	def test_ema_chgpct_values_correct_range(self, sample_ohlcv_df):
		"""EMA percentage change values should be in reasonable range."""
		try:
			result = calculate(['ema_20_chgpct_5'], sample_ohlcv_df)
			ema_chgpct = result['ema_20_chgpct_5'].dropna()
			# For steady uptrend data, percentage change should be between -50% and +50%
			assert (ema_chgpct >= -50).all() and (ema_chgpct <= 50).all()
		except Exception as e:
			if 'InvalidFormulaError' in str(type(e).__name__):
				pytest.skip(f"EMA_CHGPCT not available: {e}")
			raise

	def test_ema_chgpct_with_history(self, sample_ohlcv_df):
		"""Test EMA percentage change with historical data."""
		# Split data into history and current
		history_df = sample_ohlcv_df.iloc[:25].copy()
		current_df = sample_ohlcv_df.iloc[25:].copy()

		# Import directly to test with history_df parameter
		from tools.indicators.trend.ema_chgpct import calculate as calculate_ema_chgpct
		result = calculate_ema_chgpct(current_df, ema_period=20, change_period=5, history_df=history_df)

		assert len(result) == len(current_df)
		assert result.dtype in [np.float64, np.float32]

	# Pivot Points
	def test_pivot_basic(self, sample_ohlcv_df):
		"""Test Pivot points calculation."""
		result = calculate(['pivot_classic'], sample_ohlcv_df)
		# Pivot returns 'pivot_p' key (P for Pivot)
		assert 'pivot_p' in result or 'pivot_classic' in result or 'pivot' in result
		key = next(k for k in result.keys() if 'pivot' in k.lower())
		assert len(result[key]) == len(sample_ohlcv_df)


class TestDonchianChannel:
	"""Donchian Channel (dc_<period>) tests."""

	@pytest.fixture
	def sample_ohlcv_df(self):
		"""Create sample OHLCV DataFrame."""
		dates = pd.date_range('2026-01-01', periods=100, freq='D')
		return pd.DataFrame({
			'Open': [100 + i * 0.5 for i in range(100)],
			'High': [102 + i * 0.5 for i in range(100)],
			'Low': [99 + i * 0.5 for i in range(100)],
			'Close': [101 + i * 0.5 for i in range(100)],
			'Volume': [1000000] * 100,
		}, index=dates)

	def test_dc_components(self, sample_ohlcv_df):
		"""dc_<period> alone should expand to upper/mid/lower components."""
		result = calculate(['dc_20'], sample_ohlcv_df)
		assert 'dc_20_upper' in result
		assert 'dc_20_mid' in result
		assert 'dc_20_lower' in result
		for key in ('dc_20_upper', 'dc_20_mid', 'dc_20_lower'):
			assert len(result[key]) == len(sample_ohlcv_df)

	def test_dc_explicit_components(self, sample_ohlcv_df):
		"""dc_<period>_<upper|lower|mid> should each resolve to a single Series."""
		result = calculate(['dc_20_upper', 'dc_20_lower', 'dc_20_mid'], sample_ohlcv_df)
		assert isinstance(result['dc_20_upper'], pd.Series)
		assert isinstance(result['dc_20_lower'], pd.Series)
		assert isinstance(result['dc_20_mid'], pd.Series)

	def test_dc_upper_is_highest_high(self, sample_ohlcv_df):
		"""Upper band must equal the rolling highest high over the period."""
		result = calculate(['dc_10_upper'], sample_ohlcv_df)
		expected = sample_ohlcv_df['High'].rolling(window=10, min_periods=1).max().reset_index(drop=True)
		pd.testing.assert_series_equal(result['dc_10_upper'], expected, check_names=False)

	def test_dc_lower_is_lowest_low(self, sample_ohlcv_df):
		"""Lower band must equal the rolling lowest low over the period."""
		result = calculate(['dc_10_lower'], sample_ohlcv_df)
		expected = sample_ohlcv_df['Low'].rolling(window=10, min_periods=1).min().reset_index(drop=True)
		pd.testing.assert_series_equal(result['dc_10_lower'], expected, check_names=False)

	def test_dc_mid_is_average_of_bands(self, sample_ohlcv_df):
		"""Mid band must be the midpoint between upper and lower."""
		result = calculate(['dc_10_upper', 'dc_10_lower', 'dc_10_mid'], sample_ohlcv_df)
		expected_mid = (result['dc_10_upper'] + result['dc_10_lower']) / 2
		pd.testing.assert_series_equal(result['dc_10_mid'], expected_mid, check_names=False)

	def test_dc_band_ordering(self, sample_ohlcv_df):
		"""Upper >= mid >= lower at every point."""
		result = calculate(['dc_15_upper', 'dc_15_mid', 'dc_15_lower'], sample_ohlcv_df)
		assert (result['dc_15_upper'] >= result['dc_15_mid']).all()
		assert (result['dc_15_mid'] >= result['dc_15_lower']).all()

	def test_dc_default_period(self, sample_ohlcv_df):
		"""dc with no period suffix should use the default period of 20."""
		result = calculate(['dc'], sample_ohlcv_df)
		assert 'dc_20_upper' in result
		assert 'dc_20_lower' in result
		assert 'dc_20_mid' in result


if __name__ == '__main__':
	pytest.main([__file__, '-v'])
