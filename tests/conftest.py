"""Pytest fixtures for PreMarketFlow tests."""

import pytest
import sys
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch


def pytest_configure(config):
	"""Add src to path before any test collection."""
	src_path = str(Path(__file__).parent.parent / "src")
	if src_path not in sys.path:
		sys.path.insert(0, src_path)


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.context import AgentContext


@pytest.fixture
def test_data_dir():
    """Return path to test data directory."""
    return Path(__file__).parent / "fixtures" / "data"


@pytest.fixture
def test_strategy_dir():
    """Return path to test strategy directory."""
    return Path(__file__).parent / "fixtures" / "strategies"


@pytest.fixture
def test_data_history(test_data_dir):
    """Load test parquet files as data_history dictionary."""
    data_history = {}
    for parquet_file in test_data_dir.glob("*.parquet"):
        ticker = parquet_file.stem
        df = pd.read_parquet(parquet_file)
        # Ensure timestamp is datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        data_history[ticker] = df
    return data_history


@pytest.fixture
def test_strategy_config(test_strategy_dir):
    """Load test strategy YAML."""
    import yaml
    strategy_file = test_strategy_dir / "test_premarket_strategy.yml"
    with open(strategy_file) as f:
        config = yaml.safe_load(f)
    return config


@pytest.fixture
def agent_context():
    """Create an AgentContext for testing."""
    return AgentContext()


@pytest.fixture
def mock_data_history():
    """Mock DataHistory to return test data."""
    def _mock_init(self, ticker):
        self.ticker = ticker

    def _mock_get_all(self, start_date=None, end_date=None):
        # Return mock OHLCV data
        from datetime import datetime
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
def aapl_data(test_data_dir):
    """Load AAPL.parquet real market data for indicator testing."""
    fixture_path = test_data_dir / "AAPL.parquet"
    if not fixture_path.exists():
        pytest.skip(f"Test fixture not found: {fixture_path}")
    df = pd.read_parquet(fixture_path)
    # AAPL.parquet has columns: timestamp, open, high, low, close, volume, etc.
    # Indicators expect lowercase: date/timestamp, open, high, low, close, volume
    if 'timestamp' in df.columns and 'date' not in df.columns:
        df = df.rename(columns={'timestamp': 'date'})
    df.columns = [col.lower() for col in df.columns]
    return df


@pytest.fixture
def sample_ohlcv_df():
    """Create a sample OHLCV DataFrame for basic unit tests."""
    dates = pd.date_range('2026-01-01', periods=100, freq='D')
    return pd.DataFrame({
        'date': dates,
        'open': [100 + i*0.5 for i in range(100)],
        'high': [102 + i*0.5 for i in range(100)],
        'low': [99 + i*0.5 for i in range(100)],
        'close': [101 + i*0.5 for i in range(100)],
        'volume': [1000000] * 100,
    })
