# Test Fixtures for PreMarketFlow Tests

This directory contains test data and sample strategy configurations for PreMarketFlow testing.

## Structure

### Data Files (`data/`)
- **AAPL.PA.parquet** - Historical OHLCV data for Apple (Paris Exchange) test ticker
- **MSFT.PA.parquet** - Historical OHLCV data for Microsoft (Paris Exchange) test ticker

Each parquet file contains 100 trading days of data (2026-01-01 to 2026-04-10) with columns:
- `timestamp` - Trading date/time
- `open` - Opening price
- `high` - High price
- `low` - Low price
- `close` - Closing price
- `volume` - Trading volume
- `ticker` - Ticker symbol

### Strategy Templates (`strategies/`)
- **test_premarket_strategy.yml** - Sample strategy configuration for PreMarketFlow testing

This strategy demonstrates all major configuration sections:
- Basic indicator list (RSI, EMA, ADX, etc.)
- Watchlist filtering (simple pass-through filter)
- Signal generation (momentum, trend, volume anomaly)
- Entry configuration (score filtering, order type)
- Position sizing (capital-based: €2,000 per position)
- Exit rules (trailing stop, take profit)

## Usage

### Running PreMarketFlow Tests
```bash
# Run all PreMarketFlow tests
pytest tests/flows/test_premarket.py -v

# Run specific test class
pytest tests/flows/test_premarket.py::TestPreMarketFlowInitialization -v

# Run with detailed output
pytest tests/flows/test_premarket.py -vv
```

### Using Test Data in Custom Tests
```python
import pytest
from pathlib import Path
import pandas as pd

# Use fixtures from conftest.py
def test_with_fixtures(test_data_history, test_strategy_config):
    assert len(test_data_history) == 2  # AAPL.PA, MSFT.PA
    assert test_strategy_config["name"] == "test_premarket"
```

## Test Data Generation

The parquet files were generated using:
```python
import pandas as pd
import numpy as np
from datetime import datetime

# Realistic OHLCV data with proper high/low relationships
dates = pd.date_range(start='2026-01-01', periods=100, freq='D')
data = {
    'timestamp': dates,
    'open': base_price + np.cumsum(random_walk),
    'high': max(open, close) + gap,
    'low': min(open, close) - gap,
    'close': price_series,
    'volume': random_volumes,
    'ticker': 'TICKER'
}
df = pd.DataFrame(data)
df.to_parquet('ticker.parquet', index=False)
```

## Test Coverage

The PreMarketFlow tests cover:
- **Initialization** (4 tests)
  - Basic initialization with strategy name
  - Step creation (all 10 steps present)
  - Custom context support
  - String representation

- **Backtest vs Live Mode** (2 tests)
  - Backtest mode detection and step ordering
  - Live mode operation

- **Process Method** (6 tests)
  - Valid input handling
  - Portfolio name setting
  - Target date handling
  - Ranking scores extraction
  - Watchlist extraction
  - Data history extraction
  - Order initialization

- **Data Slicing** (3 tests)
  - Date-based data slicing
  - Invalid date format handling
  - Missing timestamp column handling

- **Context Cleanup** (2 tests)
  - Intermediate variable removal
  - Essential variable preservation

- **Naming** (2 tests)
  - Strategy to portfolio name conversion
  - Consistency across strategies

- **Integration** (2 tests)
  - Test data directory validation
  - Output structure validation

## Adding More Test Data

To add more ticker data:

```python
# Generate and save parquet file
import pandas as pd
import numpy as np

dates = pd.date_range(start='2026-01-01', periods=100, freq='D')
data = {
    'timestamp': dates,
    'open': 100 + np.cumsum(np.random.randn(100) * 2),
    'high': 105 + np.cumsum(np.random.randn(100) * 2),
    'low': 95 + np.cumsum(np.random.randn(100) * 2),
    'close': 100 + np.cumsum(np.random.randn(100) * 2),
    'volume': np.random.randint(1000000, 5000000, 100),
    'ticker': 'NEW.PA'
}

df = pd.DataFrame(data)
df.to_parquet('tests/fixtures/data/NEW.PA.parquet', index=False)
```

Then update `test_premarket_strategy.yml` to include the new ticker in the `tickers` list.
