# Strategy Tool

**Module**: `src.tools.finance.strategy` | **Status**: ✅ Functional

## Overview

Manage, configure, and execute trading strategies with backtesting and performance analysis.

## Class

### StrategyManager

**Methods**:
- `list_strategies()` → All configured strategies
- `get_strategy(name)` → Full strategy configuration
- `create_strategy(config)` → Create new strategy
- `update_strategy(name, config)` → Update strategy
- `delete_strategy(name)` → Delete strategy
- `run_strategy(name, backtest=False)` → Execute strategy, return signals
- `backtest_strategy(name, start_date, end_date)` → Backtest with metrics

## Strategy Engines

- **TaModel** - Technical analysis (no ML, rule-based)
  - Indicators: RSI, EMA, SMA, MACD, Bollinger Bands, ATR, ADX
  - Best for: Trend following, mean reversion
- **LightGbmModel** - Machine learning gradient boosting
- **AnomalyModel** - Anomaly detection (unsupervised)
- **PpoAgent** - Reinforcement learning

## Configuration

**Location**: `config/agents.yml`

```yaml
strategies:
  - name: momentum_cac
    engine: TaModel
    source: cac40
    signals: ['rsi_7', 'ema_20', 'ema_50', 'adx_14']
    buy_conditions: "data['rsi_7'] > 50 and data['ema_20_above_price']"
    sell_conditions: "data['rsi_7'] < 30"
    trade:
      stop: 0.05          # 5% stop loss
      target: 0.10        # 10% profit target
      fees: 0.007
      expiration: 20      # Exit after 20 days
      block: 10000        # Position size in currency
```

## Run Strategy Response

```json
{
  "status": "success",
  "strategy_name": "momentum_cac",
  "signal": "BUY",
  "tickers": [
    {
      "ticker": "EPA:MC",
      "signal": "BUY",
      "confidence": 0.85,
      "entry_price": 650.50,
      "stop": 617.98,
      "target": 715.55
    }
  ],
  "timestamp": "2026-03-19T10:30:00"
}
```

## Backtest Response

```json
{
  "status": "success",
  "strategy_name": "momentum_cac",
  "period": "2025-01-01 to 2026-03-19",
  "trades": {
    "total": 142,
    "winning": 89,
    "losing": 53,
    "open": 2
  },
  "pnl": {
    "realized": 15000.50,
    "unrealized": 2300.25,
    "total": 17300.75
  },
  "metrics": {
    "win_rate": 0.627,
    "avg_win": 250.15,
    "avg_loss": -180.50,
    "sharpe_ratio": 1.85,
    "max_drawdown": -0.125,
    "profit_factor": 2.15,
    "sortino_ratio": 2.45
  }
}
```

## Technical Indicators

- **RSI**: rsi_7, rsi_14 → rsi_7_above_50, rsi_7_above_70
- **EMA**: ema_9, ema_20, ema_50, ema_200 → ema_20_above_price, ema_20_above_ema_50
- **SMA**: sma_20, sma_50, sma_200
- **MACD**: macd, macd_signal, macd_histogram
- **Bollinger Bands**: bb_upper, bb_middle, bb_lower
- **ATR**: atr_14
- **ADX**: adx_14
- **Stochastic**: stoch_k, stoch_d

## Buy/Sell Conditions

Python expressions evaluated on each bar:

```python
"data['rsi_7'] > 50 and data['close'] > data['ema_20']"
"data['adx_14'] > 25"  # Strong trend
"data['rsi_7'] < 30"   # Oversold
"data['days_in_position'] > 20"  # Force exit
```

## Usage Examples

```python
sm = StrategyManager()

# List strategies
strategies = sm.list_strategies()
for s in strategies:
    print(f"{s['name']}: {s['engine']} on {s['source']}")

# Get today's signals
result = sm.run_strategy("momentum_cac", backtest=False)
for ticker in result['tickers']:
    print(f"{ticker['ticker']}: {ticker['signal']}")

# Backtest
backtest = sm.backtest_strategy(
    "momentum_cac",
    "2024-01-01",
    "2026-03-19"
)
print(f"Sharpe: {backtest['metrics']['sharpe_ratio']:.2f}")
```

## Performance

- List strategies: <10ms
- Get strategy: <5ms
- Run strategy: 1-5 seconds
- Backtest: 10-60 seconds (depends on period)

## Error Handling

```json
{
  "status": "error",
  "message": "Strategy 'unknown' not found",
  "available": ["momentum_cac", "ml_trend", ...]
}
```

## Dependencies

- pandas, lightgbm (optional), ta-lib (optional), loguru
