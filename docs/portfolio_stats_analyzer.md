# Portfolio Stats Analyzer Subagent

A comprehensive subagent within the Research agent that analyzes portfolio statistics and provides strategic recommendations based on strategy configuration.

## Overview

The `PortfolioStatsAnalyzerAgent` examines portfolio performance metrics and compares them against strategy configuration to identify performance issues and suggest improvements.

## Features

### 1. Metrics Analysis

Analyzes four key dimensions:

**Returns Analysis**
- Total return percentage
- Excess return vs benchmark
- Sharpe, Sortino, and Calmar ratios
- Assessment: excellent, good, acceptable, marginal, or poor

**Risk Analysis**
- Maximum drawdown percentage
- Drawdown duration
- Gross exposure level
- Assessment: low, moderate, moderate-high, or high

**Trade Quality Analysis**
- Win rate percentage
- Profit factor
- Expectancy
- Risk/Reward ratio
- Best/worst trade
- Assessment: excellent, good, acceptable, negative, or marginal

**Position Management Analysis**
- Average winning trade duration
- Average losing trade duration
- Comparison against configured holding period
- Assessment: good, passive, poor, or acceptable

### 2. Strategy Configuration Integration

Automatically loads strategy YAML files and:
- Compares actual position sizes against configured formulas
- Validates entry/exit thresholds
- Checks stop loss and take profit settings
- Analyzes signal weights and effectiveness

### 3. Intelligent Recommendations

Generates prioritized recommendations:
- **CRITICAL**: Issues preventing profitability
- **HIGH**: Performance bottlenecks
- **MEDIUM**: Optimization opportunities
- **LOW**: Minor improvements

### 4. Recommendation Categories

- **Returns**: Negative returns, poor risk-adjusted performance
- **Risk Management**: Excessive drawdown, concentration
- **Signal Quality**: Win rate, selectivity, confirmation filters
- **Position Sizing**: Risk/reward ratios, sizing formulas
- **Exit Timing**: Holding periods, loss management
- **Strategy Tuning**: Trade frequency, sample size

## Usage

### Via CLI

```bash
# Analyze most recent backtest with recommendations
cresus flow run portfolio_analysis momentum_cac --backtest

# Analyze live portfolio with recommendations
cresus flow run portfolio_analysis momentum_cac
```

### Output Format

```
💡 Recommendations (5)
────────────────────────────────────────────────────────────────────

CRITICAL PRIORITY

  1. Unprofitable Trades (trade_quality)
     Profit factor of 0.61 (below 1.0 threshold)
     → Review entry and exit logic. Losses exceed gains.

HIGH PRIORITY

  1. Negative Sharpe Ratio (risk_adjusted_returns)
     Risk-adjusted returns are negative, indicating volatility 
     is not compensated by returns
     → Increase signal selectivity. Consider raising entry thresholds.

MEDIUM PRIORITY

  1. Excessive Trading (signal_quality)
     229 trades (avg 1.9 per day)
     → Add holding period filter or entry confirmation.
```

## Integration

### Architecture

```
ResearchAgent
├── JournalAnalyzerAgent      (trades and execution)
├── OrderAnalyzerAgent        (order placement)
├── IssueIdentifierAgent      (trade/order issues)
└── PortfolioStatsAnalyzerAgent (performance metrics + strategy config)
    ├── _analyze_metrics()
    │   ├── _analyze_returns()
    │   ├── _analyze_risk()
    │   ├── _analyze_trade_quality()
    │   └── _analyze_position_management()
    ├── _load_strategy_config()
    └── _generate_recommendations()
```

### Data Flow

1. **PortfolioAnalysisFlow** calculates portfolio metrics
2. Metrics are set in context before research execution
3. **ResearchAgent** orchestrates all subagents
4. **PortfolioStatsAnalyzerAgent**:
   - Loads strategy configuration
   - Analyzes portfolio metrics
   - Generates recommendations
5. Results combined and displayed in CLI

## Recommendation Logic

### Win Rate Analysis
- < 35% → "Low Win Rate": Improve signal filters
- 35-45% → Acceptable
- 45-55% → Good
- > 55% → Excellent

### Profit Factor Analysis
- < 1.0 → "Unprofitable Trades": Critical issue
- 1.0-1.2 → Marginal
- 1.2-1.5 → Acceptable
- 1.5-2.0 → Good
- > 2.0 → Excellent

### Sharpe Ratio Analysis
- < 0 → "Negative Sharpe Ratio": Returns don't compensate volatility
- 0-0.5 → Low quality
- 0.5-1.0 → Acceptable
- 1.0-1.5 → Good
- > 1.5 → Excellent

### Drawdown Analysis
- < 10% in < 30 days → Low risk
- 10-20% in < 60 days → Moderate risk
- 20-35% in < 90 days → Moderate-high risk
- > 35% or > 90 days → High risk

## Configuration Expectations

The analyzer references these strategy config parameters:

```yaml
entry:
  parameters:
    position_size: formula
    extension_filter: formula
    regime_filter: formula

exit:
  parameters:
    stop_loss: formula
    take_profit: formula
    trailing_stop: formula
    holding_period: days
    time_stop: days
```

## Example Scenarios

### Scenario 1: High Win Rate, Low Profit Factor
- **Issue**: Taking small profits on winners, large losses on losers
- **Recommendation**: Increase take_profit target, reduce stop_loss width
- **Action**: Adjust exit parameters for better R:R ratio

### Scenario 2: Excessive Trading
- **Issue**: Too many trades per day
- **Recommendation**: Add holding_period filter or confirmation
- **Action**: Increase entry thresholds (RSI > 65, MACD > 0.7)

### Scenario 3: Negative Sharpe with Positive Returns
- **Issue**: High volatility relative to returns
- **Recommendation**: Improve signal selectivity
- **Action**: Add regime filters, increase entry confirmation

## Files Modified

- `src/agents/research/agent.py` - Added stats_analyzer orchestration
- `src/agents/research/sub_agents/__init__.py` - Registered new agent
- `src/flows/portfolio_analysis.py` - Calculate metrics before research
- `src/cli/commands/flow.py` - Display recommendations in CLI
- `src/agents/research/sub_agents/stats_analyzer.py` - NEW: Implementation

## Testing

```bash
# Test backtest analysis with full recommendations
python -m src.cli.main flow run portfolio_analysis momentum_cac --backtest

# Test live portfolio with recommendations
python -m src.cli.main flow run portfolio_analysis momentum_cac

# Check metrics are populated correctly
python -m src.cli.main flow run portfolio_analysis default_strategy --backtest
```
