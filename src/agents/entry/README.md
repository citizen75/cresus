# Entry Agent

Comprehensive trade entry point analysis for watchlist tickers using multi-criteria evaluation.

## Overview

The EntryAgent orchestrates three specialized sub-agents to evaluate trade entry points:

1. **EntryScoreAgent** - Signal strength evaluation
2. **EntryTimingAgent** - Optimal timing analysis
3. **EntryRRAgent** - Risk/reward ratio calculation

## Architecture

```
EntryAgent (Orchestrator)
├── EntryScoreAgent (0-100 score)
│   └── Evaluates technical indicators
├── EntryTimingAgent (0-100 score)
│   └── Analyzes price patterns and momentum
└── EntryRRAgent (Metrics)
    └── Calculates support/resistance levels
```

## Components

### EntryScoreAgent

Evaluates technical signal strength based on:

- **RSI (14)**: Oversold conditions (< 30) get higher scores
- **EMA Crossover**: Bullish alignment (EMA20 > EMA50) gets bonus points
- **ADX Trend**: Strong trends (> 25) indicate favorable conditions
- **MACD Momentum**: Positive momentum confirmation

**Scoring:**
- 0-20 points: RSI analysis
- 0-20 points: EMA crossover
- 0-15 points: ADX strength
- 0-15 points: MACD momentum
- **Range: 0-100**

### EntryTimingAgent

Evaluates when to enter based on price action:

- **Pullback Analysis**: Ideal pullback is 5-15% from recent high
- **Momentum**: Uptrend formation signals (3-day uptrend)
- **Volume Confirmation**: Above-average volume adds points
- **Volatility**: Moderate volatility (1-3%) is ideal

**Timing Scores:**
- Perfect pullback (5-15%): +20 points
- Uptrend formation: +15 points
- Above-average volume: +10 points
- Moderate volatility: +5 points
- **Range: 0-100**

### EntryRRAgent

Calculates risk/reward metrics:

- **Support Level**: Lowest low in 20-day period (or ATR-based)
- **Resistance Level**: Highest high in 20-day period (or ATR-based)
- **Stop Loss**: Support level
- **Take Profit**: Resistance level
- **Risk/Reward Ratio**: Reward / Risk

**Output Metrics:**
```json
{
  "entry_price": 100.0,
  "stop_loss": 95.0,
  "take_profit": 110.0,
  "risk_amount": 5.0,
  "reward_amount": 10.0,
  "rr_ratio": 2.0,
  "risk_pct": 5.0,
  "reward_pct": 10.0
}
```

## Composite Score

Weighted combination of all three analyses:

```
Composite = (EntryScore × 0.40) + (TimingScore × 0.35) + (RRScore × 0.25)
```

**Weights:**
- Entry Score: 40% - Signal strength is most important
- Timing Score: 35% - Pattern quality matters
- RR Score: 25% - Must have acceptable risk/reward

## Recommendation Levels

Based on composite score:

| Score | Recommendation | Action |
|-------|---|---|
| 80-100 | STRONG BUY | High confidence entry |
| 65-79 | BUY | Good entry opportunity |
| 50-64 | HOLD | Neutral, wait for better |
| 35-49 | WAIT | Weak signals, avoid |
| 0-34 | SKIP | Poor entry conditions |

## Usage

### Basic Flow Integration

```python
from agents.entry.agent import EntryAgent
from core.context import AgentContext

# Setup context with watchlist and data
context = AgentContext()
context.set("watchlist", ["TICKER1", "TICKER2"])
context.set("data_history", {
    "TICKER1": df1,  # pandas DataFrame with OHLCV
    "TICKER2": df2,
})

# Run entry analysis
agent = EntryAgent("entry_analyzer", context)
result = agent.process({})

# Get recommendations
recommendations = context.get("entry_recommendations")
for rec in recommendations:
    print(f"{rec['ticker']}: {rec['recommendation']} (Score: {rec['composite_score']})")
```

### In PreMarketFlow

```python
from flows.premarket import PreMarketFlow
from agents.entry.agent import EntryAgent

flow = PreMarketFlow("strategy_name")
result = flow.process()

# Add entry analysis
entry_agent = EntryAgent("entry", flow.context)
entry_result = entry_agent.process()

# Get top opportunities
recommendations = flow.context.get("entry_recommendations")
top_5 = sorted(recommendations, key=lambda x: x['composite_score'], reverse=True)[:5]
```

## Required Data

### DataFrame Columns

EntryAgent requires OHLCV data with technical indicators:

**Minimum Required:**
- `close` - Closing price
- `high` - High price
- `low` - Low price
- `volume` - Trading volume

**Recommended Indicators:**
- `rsi_14` - Relative Strength Index (14-period)
- `ema_20` - 20-period Exponential Moving Average
- `ema_50` - 50-period Exponential Moving Average
- `adx_20` - Average Directional Index (20-period)
- `macd_12_26` - MACD (12-26)
- `atr_14` - Average True Range (14-period)

### Context Requirements

```python
context.set("watchlist", ["TICKER1", "TICKER2", ...])
context.set("data_history", {
    "TICKER1": df1,  # pandas DataFrame
    "TICKER2": df2,
    ...
})
```

## Output

### Context Data

```python
# After execution, context contains:
entry_scores = context.get("entry_scores")           # {ticker: score}
timing_scores = context.get("timing_scores")         # {ticker: score}
rr_metrics = context.get("rr_metrics")               # {ticker: metrics}
recommendations = context.get("entry_recommendations") # [recommendation_objects]
```

### Result Dictionary

```python
{
    "status": "success",
    "output": {
        "total_analyzed": 20,
        "scored": 20,
        "with_timing": 18,
        "with_rr": 17,
        "recommendations": 17,
        "top_opportunities": [
            {
                "rank": 1,
                "ticker": "TICKER1",
                "score": 85.3,
                "recommendation": "STRONG BUY",
                "rr_ratio": 2.5
            },
            ...
        ],
        "statistics": {
            "avg_entry_score": 72.5,
            "avg_timing_score": 68.3,
            "avg_rr": 1.8
        }
    }
}
```

## Performance Tips

1. **Data Quality**: Ensure accurate OHLCV data and indicator calculations
2. **Minimum History**: Prefer 20+ days of data for reliable analysis
3. **Indicator Calculation**: Pre-calculate indicators in DataAgent
4. **Filtering**: Run EntryAgent only on filtered watchlists (post-PreMarketFlow)

## Testing

Run test suite:

```bash
pytest tests/agents/entry/test_agent.py -v
```

Test Coverage:
- 6 EntryScoreAgent tests
- 4 EntryTimingAgent tests
- 3 EntryRRAgent tests
- 7 EntryAgent tests
- **Total: 20 tests**

## Example Output

```
TICKER1: STRONG BUY
  - Entry Score: 82.5
  - Timing Score: 78.0
  - Composite: 82.1
  - Entry Price: 100.00
  - Stop Loss: 95.00
  - Take Profit: 112.50
  - Risk/Reward: 2.50x

TICKER2: BUY
  - Entry Score: 68.0
  - Timing Score: 65.0
  - Composite: 67.3
  - Entry Price: 50.00
  - Stop Loss: 47.50
  - Take Profit: 57.50
  - Risk/Reward: 1.60x
```

## Integration with Trading System

EntryAgent fits into the full trading flow:

1. **PreMarketFlow** - Generates watchlist
2. **EntryAgent** - Analyzes entry points
3. **TradeExecutor** - Places orders based on recommendations
4. **PortfolioManager** - Tracks positions

This provides a complete pipeline from watchlist generation to entry execution.
