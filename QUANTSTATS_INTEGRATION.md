# QuantStats Integration

## Overview

QuantStats has been integrated into the portfolio system for advanced performance analytics. The integration is **fully backward compatible** — existing code requires no changes.

## Files Modified

### 1. `src/tools/portfolio/metrics.py` (PortfolioMetrics class)
- Added QuantStats import with graceful fallback
- Enhanced metric calculations:
  - `_calculate_sharpe_ratio()` — uses `qs.stats.sharpe()`
  - `_calculate_sortino_ratio()` — uses `qs.stats.sortino()`
  - `_calculate_omega_ratio()` — uses `qs.stats.omega()`
- All methods fall back to manual calculation if QuantStats unavailable
- **No change to public interface** — all existing code continues to work

### 2. `src/tools/portfolio/portfolio_engine_v2.py` (Research backtest engine)
- `SimplePortfolio` class with QuantStats analytics methods:
  - `analyze_with_quantstats()` — Generate comprehensive metrics dictionary
  - `print_quantstats_report()` — Formatted console output
- Tracks daily portfolio values and returns
- Standalone module (independent of src/tools/portfolio)

## Installation

Add QuantStats to research dependencies:
```bash
pip install -e '.[research]'
```

This installs: matplotlib, seaborn, plotly, jupyter, quantstats, etc.

## Usage Examples

### Option 1: Automatic (existing code, no changes needed)

```python
from tools.portfolio.metrics import PortfolioMetrics

metrics_obj = PortfolioMetrics(context)
results = metrics_obj.calculate_backtest_metrics(
    name="portfolio_name",
    start_date="2024-01-01",
    end_date="2024-12-31"
)

# QuantStats is automatically used if available
# Falls back to manual calculation otherwise
print(f"Sharpe: {results['sharpe_ratio']}")
print(f"Sortino: {results['sortino_ratio']}")
print(f"Calmar: {results['calmar_ratio']}")
```

### Option 2: Direct QuantStats access (research/backtest)

```python
from portfolio_engine_v2 import run_simple_backtest
import pandas as pd

# Run backtest
portfolio = run_simple_backtest(trades_df, initial_capital=10000.0)

# Calculate daily returns
daily_returns = pd.Series(...)  # Your returns

# Get QuantStats analytics
portfolio.print_quantstats_report(daily_returns)

# Or get as dictionary
metrics = portfolio.analyze_with_quantstats(daily_returns)
print(f"Sharpe: {metrics['sharpe']:.2f}")
print(f"Sortino: {metrics['sortino']:.2f}")
print(f"Max Drawdown: {metrics['max_drawdown']*100:.2f}%")
```

## Metrics Available

| Metric | Method | Source |
|--------|--------|--------|
| **Returns** | `annual_return`, `total_return`, `best_day`, `worst_day` | QuantStats |
| **Risk** | `volatility`, `max_drawdown`, `avg_drawdown`, `skew`, `kurtosis` | QuantStats |
| **Risk-Adjusted** | `sharpe_ratio`, `sortino_ratio`, `calmar_ratio`, `omega_ratio` | QuantStats |
| **Trade Analysis** | `win_rate`, `best_trade`, `worst_trade`, `profit_factor`, `expectancy` | Manual FIFO |
| **Benchmark** | `beta`, `alpha`, `correlation` | QuantStats (optional) |

## Backward Compatibility

✅ **All existing code works unchanged**
- PortfolioMetrics maintains exact same interface
- Function signatures identical
- Return dictionary keys unchanged
- If QuantStats unavailable, falls back to manual calculation
- No breaking changes to public API

## Benefits

- ✅ Industry-standard metrics (QuantStats is widely used)
- ✅ Consistent with portfolio analysis tools
- ✅ Advanced metrics (Sortino, Calmar, Omega)
- ✅ Graceful fallback if library unavailable
- ✅ Zero migration cost for existing code
- ✅ Optional enhanced analytics for research

## Testing

All existing tests continue to pass without modification:
```bash
pytest tests/tools/portfolio/test_metrics.py
```

QuantStats metrics can be validated against the [QuantStats documentation](https://github.com/ranaroussi/quantstats).
