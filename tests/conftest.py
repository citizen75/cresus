"""Pytest configuration for Cresus tests."""

import sys
from pathlib import Path
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Add src to Python path for imports
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def mock_data_history():
	"""Mock DataHistory to return synthetic OHLCV data.

	Patches DataHistory class and provides synthetic price data
	for testing agents that require historical market data.
	"""
	def _mock_init(self, ticker):
		self.ticker = ticker

	def _mock_get_all(self, start_date=None, end_date=None):
		# Return synthetic OHLCV data for 100 days
		dates = pd.date_range(start='2026-01-01', end='2026-05-07', freq='D')
		data = {
			'timestamp': dates,
			'open': [100 + i*0.5 for i in range(len(dates))],
			'high': [102 + i*0.5 for i in range(len(dates))],
			'low': [99 + i*0.5 for i in range(len(dates))],
			'close': [101 + i*0.5 for i in range(len(dates))],
			'volume': [1000000] * len(dates),
		}
		return pd.DataFrame(data)

	with patch('tools.data.core.DataHistory.__init__', _mock_init):
		with patch('tools.data.core.DataHistory.get_all', _mock_get_all):
			yield


@pytest.fixture
def mock_ohlcv_df():
	"""Return synthetic OHLCV DataFrame."""
	dates = pd.date_range('2026-01-01', periods=100, freq='D')
	return pd.DataFrame({
		'timestamp': dates,
		'open': [100 + i*0.5 for i in range(100)],
		'high': [102 + i*0.5 for i in range(100)],
		'low': [99 + i*0.5 for i in range(100)],
		'close': [101 + i*0.5 for i in range(100)],
		'volume': [1000000] * 100,
	})


@pytest.fixture
def sample_strategy_config():
	"""Return sample strategy configuration."""
	return {
		"name": "test_strategy",
		"engine": "TaModel",
		"source": "cac40",
		"signals": ["rsi_7", "ema_20", "ema_50"],
		"features_excluded": ["Date", "ticker"],
		"buy_conditions": "data['rsi_7'] < 30 and data['ema_20'] < data['ema_50']",
		"sell_conditions": "data['rsi_7'] > 70",
		"trade": {
			"stop": 0.05,
			"target": 0.07,
			"fees": 0.007,
			"expiration": 10,
			"block": 1000,
		},
		"predict": {
			"days": 5,
			"threshold": 0.05,
		},
		"indicators": ["rsi_7", "ema_20", "ema_50"],
	}


@pytest.fixture
def sample_market_regime_config():
	"""Return sample market regime configuration."""
	return {
		"universe": "cac40",
		"model_path": "/tmp/cac40_regime.pkl",
		"features": [
			"breadth_above_sma20",
			"breadth_above_sma50",
			"breadth_above_sma200",
			"breadth_change_5d",
			"adv_decline_ratio",
			"cross_correlation",
			"dispersion",
			"avg_atr_norm",
			"vol_regime_score",
			"momentum_factor_return",
			"meanrev_factor_return",
			"lowvol_factor_return",
			"quality_factor_return",
		],
		"training": {
			"lookback_days": 1000,
			"n_regimes": 6,
			"test_split": 0.2,
		},
		"lgbm_params": {
			"n_estimators": 200,
			"max_depth": 6,
			"learning_rate": 0.05,
			"num_leaves": 31,
			"min_child_samples": 20,
		},
	}


@pytest.fixture
def mock_context():
	"""Return a fresh AgentContext for testing."""
	from core.context import AgentContext
	return AgentContext()


@pytest.fixture
def sample_journal_df():
	"""Return sample journal DataFrame with trade history."""
	return pd.DataFrame({
		"id": ["1", "2", "3"],
		"ticker": ["AAPL", "GOOGL", "MSFT"],
		"entry_date": [datetime(2026, 1, 1), datetime(2026, 1, 5), datetime(2026, 1, 10)],
		"entry_price": [100, 2000, 300],
		"exit_date": [datetime(2026, 1, 3), datetime(2026, 1, 8), datetime(2026, 1, 15)],
		"exit_price": [105, 2050, 315],
		"quantity": [10, 5, 20],
		"pnl": [50, 250, 300],
	})


@pytest.fixture
def sample_orders_df():
	"""Return sample orders DataFrame."""
	return pd.DataFrame({
		"id": ["1", "2", "3"],
		"ticker": ["AAPL", "GOOGL", "MSFT"],
		"status": ["EXECUTED", "EXECUTED", "PENDING"],
		"quantity": [10, 5, 20],
		"price": [100, 2000, 300],
		"created_at": [
			datetime(2026, 5, 5).isoformat(),
			datetime(2026, 5, 6).isoformat(),
			datetime(2026, 5, 7).isoformat(),
		],
	})
