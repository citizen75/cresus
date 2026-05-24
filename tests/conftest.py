"""Pytest fixtures for PreMarketFlow tests."""

import pytest
import sys
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

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
