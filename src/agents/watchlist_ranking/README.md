# Watchlist Ranking Agent

Machine learning-powered watchlist ranking using LightGBM models.

## Overview

The Watchlist Ranking Agent provides:
- **Feature Extraction**: Automatically extracts all available features from historical price data and indicators
- **Model Training**: Trains LightGBM regression models to predict future returns
- **Ticker Ranking**: Scores and ranks tickers by predicted performance
- **Fallback Scoring**: Uses feature-based scoring when model training fails

## Architecture

### Main Agent: `WatchlistRankingAgent`

Orchestrates the three-step pipeline:
1. Features extraction (from `data_history`)
2. Model training/loading
3. Ticker ranking by model predictions

### Sub-agents

#### 1. FeaturesAgent (`features.py`)

Extracts features from historical data:
- **Price Features**: open, high, low, close, volume
- **Indicator Features**: All calculated technical indicators (RSI, EMA, MACD, etc.)
- **Output**: DataFrame with one row per ticker, columns for each feature

#### 2. TrainAgent (`train.py`)

Trains or loads LGBM models:
- **Training Mode**: 
  - Generates labels from 5-day forward returns
  - Trains LightGBM on feature → return mapping
  - Saves model to `~/.cresus/db/models/watchlist_ranking/`
- **Load Mode**: 
  - Loads pre-trained model if available
  - Falls back to feature-based scoring if model missing
- **Graceful Degradation**:
  - If LightGBM not installed → feature-based scoring
  - If insufficient data (< 6 rows) → feature-based scoring
  - If training fails → feature-based scoring

#### 3. RankAgent (`rank.py`)

Scores and ranks tickers:
- **With Model**: Uses trained LGBM to predict return scores
- **Without Model**: Uses weighted feature scoring
  - Weights indicators like RSI, MACD, ADX, EMAs, SHA, Bollinger Bands
  - Normalizes features to 0-1 scale
  - Returns composite score

## Usage

### Python API

```python
from agents.watchlist_ranking.agent import WatchlistRankingAgent
from core.context import AgentContext
from agents.strategy.agent import StrategyAgent
from agents.data.agent import DataAgent

# Setup context
ctx = AgentContext()
strategy_agent = StrategyAgent("strategy[my_strategy]", ctx)
strategy_agent.process({})

data_agent = DataAgent("data[my_strategy]", ctx)
data_agent.process({})

# Create ranking agent
ranking = WatchlistRankingAgent("Ranking", ctx)

# Train model (one-time)
result = ranking.train("my_strategy")

# Rank tickers
result = ranking.rank("my_strategy")
scores = result["output"]["scores"]
ranked = result["output"]["ranked"]  # Top 20 sorted

for ticker, score in ranked[:10]:
    print(f"{ticker}: {score:.4f}")
```

### CLI Commands

```bash
# Train LGBM model for a strategy
cresus watchlist train nasdaq_100_trend

# Rank tickers using the model
cresus watchlist rank nasdaq_100_trend
```

## Model Training

### Label Generation

Labels are generated from 5-day forward returns:
```
label = (close[+5] - close[0]) / close[0]
```

This measures the expected return if buying today and selling 5 days later.

### Feature Set

All columns in `data_history` (except metadata):
- OHLCV prices (5 features)
- All indicators defined in strategy config (typically 15-20 features)
- Example: RSI, MACD, EMA, ADX, ATR, Bollinger Bands, SHA, Volume SMA, etc.

### Model Parameters

LightGBM with default settings:
- **Objective**: Regression (predicting return magnitude)
- **Leaves**: 31
- **Learning Rate**: 0.05
- **Rounds**: 100
- **Verbose**: Disabled

## Feature-Based Scoring (Fallback)

When LGBM model unavailable, uses weighted indicator scoring:

```
weights = {
  'rsi_14': 0.1,           # Momentum
  'rsi_5': 0.1,            # Short-term momentum
  'macd_12_26': 0.1,       # Trend confirmation
  'adx_14': 0.1,           # Trend strength
  'ema_10': 0.05,          # Trend
  'ema_20': 0.05,          # Trend
  'ema_50': 0.05,          # Long-term trend
  'volume_sma_20': 0.05,   # Volume confirmation
  'sha_5_green': 0.1,      # Bullish candle pattern
  'sha_10_green': 0.1,     # Bullish candle pattern
  'bb_20_upper': 0.05,     # Breakout potential
  'close': 0.05,           # Price level
}

score = sum(normalized[col] * weight for col, weight in weights.items()) / sum(weights)
```

## Output Format

### Training Result

```python
{
  "status": "success",
  "output": {
    "model_path": "/path/to/strategy_lgb.pkl",
    "samples": 100,        # Training samples
    "features": 24,        # Number of features
  },
  "message": "Trained model on 100 samples"
}
```

### Ranking Result

```python
{
  "status": "success",
  "output": {
    "scores": {
      "NVDA": 0.75,
      "MSFT": 0.68,
      ...
    },
    "ranked": [
      ("NVDA", 0.75),
      ("MSFT", 0.68),
      ...  # Top 20
    ]
  },
  "message": "Ranked 50 tickers"
}
```

## Performance Considerations

- **Feature Extraction**: O(n) where n = number of tickers
- **Model Training**: O(n * f * r) where f = features, r = rounds
- **Ranking**: O(n) prediction time + O(n log n) sorting
- Typical runtime: < 1 second for 100 tickers

## Installation

LightGBM is optional but recommended:

```bash
pip install lightgbm
```

Without LightGBM, the agent will use feature-based scoring (slightly lower accuracy but still effective).

## Example: Complete Workflow

```bash
# 1. Train model
cresus watchlist train nasdaq_100_trend
# Output: Model trained on X samples with Y features

# 2. View rankings
cresus watchlist rank nasdaq_100_trend
# Output: Table showing top 20 ranked tickers

# 3. Use in strategy
# Rankings are stored in context and can be used by other agents
# to filter watchlist or weight position sizing
```

## Integration with Strategies

The ranking scores can be integrated into strategies by:

1. **Watchlist Filtering**: Only trade top N ranked tickers
2. **Position Sizing**: Allocate more capital to higher-ranked tickers
3. **Entry Weighting**: Increase confidence for well-ranked entries
4. **Rebalancing**: Reweight portfolio based on latest rankings

## Troubleshooting

### "No valid training data"
- Occurs when tickers have < 6 rows of history
- Falls back to feature-based scoring automatically
- Solution: Add more historical data or use feature scoring

### "LightGBM not installed"
- Install with: `pip install lightgbm`
- Falls back to feature-based scoring automatically
- Feature scoring is still effective for ranking

### Poor ranking quality
- Check that indicators are being calculated properly
- Verify strategy has 15+ indicators defined
- Consider retraining model with more data
- Adjust feature weights in `RankAgent._score_with_features()`

## Future Enhancements

- [ ] Classification model (buy/sell/hold) instead of regression
- [ ] Time-series cross-validation for better model evaluation
- [ ] Feature importance analysis and auto-weighting
- [ ] Multi-model ensemble voting
- [ ] Hyperparameter optimization (optuna)
- [ ] Walk-forward backtesting
