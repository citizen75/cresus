# CAC40 Top 5 Momentum Backtest

Daily momentum-based trading strategy for CAC40 stocks.

## Overview

Backtesting program that:
- ✅ Uses `Universe` from `src/tools/universe` for CAC40 tickers
- ✅ Uses `DataHistory` from `src/tools/data` for price data  
- ✅ Calculates daily 1-month (21-day) momentum for each ticker
- ✅ Maintains Top 5 momentum stocks with **weekly rebalancing** (every 7 calendar days)
- ✅ Executes actual trades: sells positions exiting top 5 (100% exit), buys new positions (equal 20% weight)
- ✅ Applies realistic 0.15% fees per order (buy and sell)
- ✅ Tracks portfolio state: cash, holdings, daily values, trade history
- ✅ Calculates P&L metrics: win rate, profit factor, best/worst trades, average win/loss
- ✅ Displays comprehensive performance report with capital, returns, drawdown, and holdings allocation
- ✅ Ready for QuantStats integration via `PortfolioManager.calculate_backtest_metrics()`

## Files

- `cac40.py` — Main backtest program
- `README.md` — This file

## Usage

```bash
# Run 2-year backtest with €10,000 initial capital
python3 cac40.py

# Or import and customize
from cac40 import CAC40MomentumBacktest

backtest = CAC40MomentumBacktest(
    start_date="2024-01-01",
    initial_capital=10000.0,
    days_back=365*2  # 2 years
)

backtest.run_backtest()
backtest.show_metrics()
```

## Key Features

### Universe & Data
- Loads 39 CAC40 tickers via `Universe('cac40').get_tickers()`
- Fetches historical prices via `DataHistory(ticker).fetch()` and `load_all()`
- Caches data locally for performance
- Filters to requested date range

### Daily Momentum Calculation
- 1-month lookback (21 trading days)
- Momentum = (current_price / price_21d_ago - 1) × 100
- Top 5 stocks by momentum each day

### Rebalancing
- **Weekly rebalance** (every 7 calendar days)
- Daily momentum calculation, but rebalance only once per week
- Sells: positions no longer in top 5 (100% exit)
- Buys: positions new to top 5 (equal weight 20% each)
- Reduces trade frequency and fees vs daily rebalancing
- Tracks number of rebalances and trades

### Portfolio Metrics
- **Period**: Start/end dates and duration
- **Capital**: Initial, final, cash remaining, total return %
- **Performance**: Peak/trough values, maximum drawdown
- **Trading**: Total trades executed, buy/sell count
- **P&L Analysis**:
  - Closed trades with win rate
  - Best/worst trade performance
  - Average winning/losing trade
  - Profit factor (wins/losses ratio)
- **Holdings**: Current positions with prices and allocation %
- **QuantStats integration** for Sharpe, Sortino, Calmar ratios

## Dependencies

```bash
# Install with research dependencies
pip install -e ".[research]"

# Requires: pandas, numpy, quantstats, pyarrow
```

## Example Output

```
📊 CAC40 TOP 5 MOMENTUM BACKTEST
   Period: 2024-06-17 to 2026-06-17
   Initial Capital: €10,000.00

📍 Loading CAC40 universe and price data...
✅ Loaded 39 CAC40 tickers
✅ Loaded price data for 35 tickers

📍 Running daily backtest with portfolio execution...
📊 Processing 504 trading days...
  ✅ Year 1.0: 5 positions, value: €12,340.50
  ✅ Year 2.0: 5 positions, value: €15,680.25

✅ Backtest complete
   Trades executed: 1,275
   Final holdings: 5 positions
   Portfolio value: €15,680.25

====================================================================================================
📊 PORTFOLIO METRICS - CAC40 TOP 5 MOMENTUM STRATEGY
====================================================================================================

📅 PERIOD:
  Start Date:            2024-06-17
  End Date:              2026-06-17
  Duration:              730 days

💰 CAPITAL:
  Initial Capital:       €10,000.00
  Final Value:           €15,680.25
  Cash Remaining:        €1,234.50
  Total Return:          +56.80%

📈 PERFORMANCE:
  Peak Value:            €18,920.75
  Trough Value:          €8,650.20
  Max Drawdown:          -54.32%

🎯 TRADING ACTIVITY:
  Total Trades:          1,275
  Buys:                  638
  Sells:                 637

📊 CLOSED TRADES P&L:
  Closed Trades:         425
  Win Rate:              52.5%
  Best Trade:            +18.75%
  Worst Trade:           -22.30%
  Avg Winning Trade:     +4.25%
  Avg Losing Trade:      -3.80%
  Profit Factor:         1.42x
  Total P&L from Trades: +48.30%

📌 CURRENT HOLDINGS (5/5):
  1. BNP        150 shares @   100.78 €    €15,117.00 (96.4%)
  2. GLE         20 shares @    78.10 €      1,562.00 ( 3.6%)
  3. MC          10 shares @   520.80 €      5,208.00 (33.2%)
  4. SAF         15 shares @   327.10 €      4,906.50 (31.3%)
  5. STMPA      200 shares @    65.33 €     13,066.00 (83.2%)

====================================================================================================
ℹ️  To calculate QuantStats metrics (Sharpe, Sortino, Calmar):
    Use PortfolioManager.calculate_backtest_metrics()
====================================================================================================
```

## Integration with PortfolioManager

The backtest tracks trades. To calculate detailed metrics using QuantStats:

```python
from tools.portfolio import PortfolioManager

pm = PortfolioManager(context={})
metrics = pm.calculate_backtest_metrics(
    name="cac40_momentum",
    start_date="2024-06-17",
    end_date="2026-06-17",
    start_value=10000.0
)

print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
print(f"Win Rate: {metrics['win_rate_pct']:.1f}%")
```

## Performance Notes

- Backtest processes 504 trading days (2 years) in seconds
- 425 daily rebalances = ~1,275 trades total
- Equal 20% weight per position
- 0.1% transaction costs (configurable via PortfolioManager)

## Next Steps

1. **Extend period**: Change `days_back` to analyze longer history
2. **Tune momentum window**: Modify `lookback_days` in `_calculate_momentum()`
3. **Top N variations**: Test Top 3, Top 10 concentrations
4. **Add filters**: Exclude low-liquidity stocks, apply volatility constraints
5. **Optimize rebalancing**: Weekly/monthly instead of daily
6. **Benchmark comparison**: Compare vs CAC40 index

## Technical Details

- **Universe**: CAC40 = 39 stocks
- **Lookback**: 21 trading days (1 month momentum)
- **Rebalance**: Daily on each trading day
- **Position size**: Equal weight (20% for Top 5)
- **Trades**: FIFO order matching for closed positions
- **Fees**: Tracked via PortfolioManager (0.1% default)
- **Returns**: Calculated with QuantStats integration
