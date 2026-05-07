# Research Analysis Architecture

Complete guide to the Research agent's subagents and their analysis capabilities.

## Architecture Overview

The ResearchAgent orchestrates 5 specialized subagents to provide comprehensive backtest and portfolio analysis:

```
ResearchAgent (Orchestrator)
│
├── 1. JournalAnalyzerAgent
│   └── Analyzes executed trades: entry/exit prices, durations, quantities
│       Output: Trade statistics, per-ticker analysis, anomalies
│
├── 2. OrderAnalyzerAgent (Basic)
│   └── Counts orders by type: buy/sell, totals, averages
│       Output: Basic order metrics, anomaly detection
│
├── 3. IssueIdentifierAgent
│   └── Identifies critical issues: zero trades, data errors, imbalances
│       Output: List of identified issues with severity
│
├── 4. PortfolioStatsAnalyzerAgent ⭐ NEW
│   └── Analyzes portfolio metrics against strategy config
│       Returns: Sharpe/Sortino ratios, win rates, profit factors
│       Recommendations: Strategy parameter tuning, signal improvements
│
└── 5. OrdersAnalysisAgent ⭐ NEW
    └── Analyzes order execution quality and consistency
        Orders: Position sizing, timing patterns, ticker concentration
        Recommendations: Order execution improvements, diversification
```

## Data Flow

```
PortfolioAnalysisFlow
    ↓
Calculate Portfolio Metrics
    ↓ (metrics stored in context)
ResearchAgent.process()
    ├─→ JournalAnalyzerAgent
    ├─→ OrderAnalyzerAgent
    ├─→ IssueIdentifierAgent
    ├─→ PortfolioStatsAnalyzerAgent (uses metrics from context)
    └─→ OrdersAnalysisAgent (analyzes order placement quality)
    ↓
Combine Results
    ├─ Identified Issues (critical)
    ├─ Performance Recommendations
    └─ Order Execution Recommendations
    ↓
CLI Display (formatted by priority)
```

## Recommendation Types

### A. Performance Recommendations (PortfolioStatsAnalyzerAgent)

Analyzes portfolio metrics and strategy configuration:

**Returns Analysis**
- Total return percentage vs benchmark
- Sharpe/Sortino/Calmar ratios
- Risk-adjusted return quality

**Risk Analysis**
- Maximum drawdown and duration
- Exposure concentration
- Volatility management

**Trade Quality**
- Win rate effectiveness
- Profit factor viability
- Risk/Reward ratio
- Trade frequency appropriateness

**Position Management**
- Holding period alignment
- Winner/loser duration balance
- Capital preservation

**Examples:**
```
• Negative Sharpe Ratio → Increase signal selectivity
• Excessive Drawdown → Tighten stop loss
• Low Win Rate → Improve entry confirmation
• Excessive Trading → Add holding period filter
```

### B. Order Execution Recommendations (OrdersAnalysisAgent)

Analyzes order placement quality and execution:

**Position Sizing**
- Consistency across orders
- Formula correctness
- Zero-quantity detection
- Capitalization alignment

**Order Frequency**
- Daily order patterns
- Peak hour concentration
- Activity consistency

**Order Balance**
- Buy/sell ratio equilibrium
- Signal effectiveness
- Exit signal strength

**Portfolio Concentration**
- Ticker diversity
- Top ticker dominance
- Strategy focus

**Examples:**
```
• Inconsistent Sizing → Implement fixed formula
• Excessive Daily Orders → Add order cooldown
• Buy/Sell Imbalance → Strengthen exit signals
• High Concentration → Expand watchlist size
```

## Integration with Strategy Config

Both subagents reference strategy configuration:

```yaml
strategy: momentum_cac
universe: cac40

watchlist:
  parameters:
    max_count: 15              # ← OrdersAnalysisAgent checks concentration
    min_volume: 500000         # ← Affects order diversity

signals:
  weights:
    momentum: 0.5              # ← PortfolioStatsAnalyzer evaluates effectiveness
    trend: 0.35
    volume_anomaly: 0.15

entry:
  parameters:
    position_size: 1000 / data["close"]  # ← OrdersAnalysisAgent validates consistency
    limit_price: data['close'] * 0.99    # ← OrdersAnalysisAgent checks fill impact
    regime_filter: ...                    # ← PortfolioStatsAnalyzer assesses effectiveness

exit:
  parameters:
    stop_loss: data['close'] - data['atr_14'] * 1.3    # ← Both analyze effectiveness
    take_profit: data['close'] + data['atr_14'] * 2.6  # ← R:R ratio checked
    holding_period: 12                                   # ← Position mgmt analyzed
    time_stop: 1                                         # ← Order expiration checked
```

## CLI Output Structure

```
Portfolio Analysis - BACKTEST MODE
════════════════════════════════════════════════════════════

📊 Portfolio Metrics
  Start Value: $9,997.60
  End Value: $8,125.72
  Total Return: -18.72%
  Win Rate: 25.21%
  Sharpe Ratio: -3.062
  [... all metrics ...]

✓ No issues found!

💡 Recommendations (6)
────────────────────────────────────────────────────────────

📊 Performance Recommendations
  HIGH PRIORITY
    1. Negative Sharpe Ratio (risk_adjusted_returns)
       Risk-adjusted returns are negative...
       → Increase signal selectivity...

  MEDIUM PRIORITY
    1. Excessive Trading (signal_quality)
       229 trades (avg 1.9 per day)
       → Add holding period filter...

📋 Order Execution Recommendations
  HIGH PRIORITY
    1. Inconsistent Position Sizing (position_sizing)
       Position sizes vary by 100% (low consistency)
       → Implement fixed position size formula...
```

## Recommendation Priority Levels

### CRITICAL 🔴
- Orders cannot execute (zero quantity/price)
- Strategy fundamentally broken
- Data errors preventing analysis

**Action:** Fix immediately before running live trading

### HIGH 🟠
- Performance significantly impaired
- Order execution quality poor
- Risk factors not controlled

**Action:** Address before production deployment

### MEDIUM 🟡
- Optimization opportunities exist
- Marginal improvements available
- Trade-offs to evaluate

**Action:** Prioritize based on impact

### LOW ⚪
- Nice-to-have improvements
- Minor consistency issues
- Edge case handling

**Action:** Consider for next iteration

## Analysis Workflow

### 1. Pre-Analysis Setup
```python
# PortfolioAnalysisFlow calculates metrics first
metrics = PortfolioMetrics(context=context)
portfolio_metrics = metrics.calculate_backtest_metrics(...)
context.set("portfolio_metrics", portfolio_metrics)
```

### 2. Journal Analysis
```python
# JournalAnalyzerAgent loads trade history
journal = Journal(name=portfolio_name, context=backtest_context)
trades_df = journal.load_df()
# Analyzes: trade counts, durations, P&L, by-ticker stats
```

### 3. Order Analysis (Basic)
```python
# OrderAnalyzerAgent basic statistics
# Counts: buy/sell orders, total quantity, price ranges
# Detects: zero-value anomalies
```

### 4. Issue Identification
```python
# IssueIdentifierAgent looks for critical problems
# Checks: zero trades, zero orders, imbalances, anomalies
# Returns: identified_issues list with severity
```

### 5. Performance Analysis ⭐
```python
# PortfolioStatsAnalyzerAgent deep metrics analysis
# Loads: strategy YAML config
# Analyzes: returns, risk, trade quality, position management
# Generates: 5-15+ recommendations by priority
```

### 6. Order Execution Analysis ⭐
```python
# OrdersAnalysisAgent quality analysis
# Loads: strategy YAML config
# Analyzes: sizing consistency, timing patterns, balance, concentration
# Generates: 5-10+ recommendations by priority
```

### 7. Results Compilation
```python
output = {
    "identified_issues": issues_list,        # From IssueIdentifier
    "metrics_analysis": metrics_data,        # From PortfolioStats
    "orders_analysis": orders_data,          # From OrdersAnalysis
    "recommendations": all_recommendations,  # Combined from both
}
```

## Key Metrics Cross-Reference

| Metric | Analyzer | Purpose | Recommendation Type |
|--------|----------|---------|---------------------|
| Win Rate | PortfolioStats | Signal quality | Signal improvement |
| Sharpe Ratio | PortfolioStats | Risk-adjusted return | Entry selectivity |
| Profit Factor | PortfolioStats | Trade profitability | Exit timing |
| Max Drawdown | PortfolioStats | Risk management | Stop loss tuning |
| Position Size Consistency | OrdersAnalysis | Execution quality | Sizing formula |
| Order/Day | OrdersAnalysis | Trade frequency | Order throttling |
| Buy/Sell Ratio | OrdersAnalysis | Signal balance | Exit strengthening |
| Ticker Concentration | OrdersAnalysis | Diversification | Watchlist expansion |

## Practical Examples

### Example 1: Strategy with Good Returns but Poor Sharpe

```
PortfolioStats:
  • Total Return: +25% ✓
  • Sharpe Ratio: 0.5 ✗
  
Recommendation:
  "Negative Sharpe Ratio: Volatility not compensated by returns"
  Action: Increase entry signal confirmation, reduce false signals
```

### Example 2: Strategy Trades Too Much

```
PortfolioStats:
  • 500 trades in 120 days (4.2/day) ✗
  
OrdersAnalysis:
  • Inconsistent position sizing ✗
  • Peak hour 2 PM (concentrated) ✗
  
Recommendations:
  1. "Excessive Trading: Add holding period filter"
  2. "Inconsistent Position Sizing: Implement fixed formula"
  3. "Inconsistent Daily Activity: Spread order generation"
```

### Example 3: Imbalanced Portfolio

```
OrdersAnalysis:
  • Buy/Sell Ratio: 3:1 ✗
  • Most active 5 tickers: 75% of orders ✗
  
PortfolioStats:
  • Low Win Rate: 20% ✗
  
Recommendations:
  1. "Excessive Buy Orders: Exit signals too weak"
  2. "High Ticker Concentration: Expand watchlist"
  3. "Low Win Rate: Improve signal confirmation"
```

## Extension Points

To add new analysis subagents:

1. Create new subagent class inheriting from `Agent`
2. Implement `process(input_data)` method
3. Return dict with `output` containing analysis results
4. Register in ResearchAgent.process()
5. Provide context (backtest_dir, portfolio_name, etc.)
6. Return recommendations in output dict

## Testing

```bash
# Test complete analysis pipeline
python -m src.cli.main flow run portfolio_analysis momentum_cac --backtest

# Test live portfolio
python -m src.cli.main flow run portfolio_analysis momentum_cac

# Test multiple portfolios
python -m src.cli.main flow run portfolio_analysis "portfolio_name" --backtest

# Verify recommendations output
python -m src.cli.main flow run portfolio_analysis momentum_cac --backtest 2>&1 | grep -E "Recommendations|PRIORITY"
```

## Performance Considerations

- **JournalAnalyzer**: O(n) where n = number of trades
- **OrderAnalyzer**: O(n) where n = number of orders
- **PortfolioStats**: O(n) for metrics calculation
- **OrdersAnalysis**: O(n) for order analysis
- **Total**: Linear in trade/order count, typically < 1s for 1000+ trades

## Files Reference

| File | Purpose |
|------|---------|
| `src/agents/research/agent.py` | Main orchestrator |
| `src/agents/research/sub_agents/journal_analyzer.py` | Trade analysis |
| `src/agents/research/sub_agents/order_analyzer.py` | Basic order stats |
| `src/agents/research/sub_agents/issue_identifier.py` | Critical issues |
| `src/agents/research/sub_agents/stats_analyzer.py` | Portfolio metrics + recs |
| `src/agents/research/sub_agents/orders_analysis.py` | Order quality + recs |
| `src/flows/portfolio_analysis.py` | Flow orchestration |
| `src/cli/commands/flow.py` | CLI display logic |

## Future Enhancements

Possible additions:
1. **TradeSequenceAnalyzer**: Entry/exit timing effectiveness
2. **SlippageAnalyzer**: Actual vs limit price comparison
3. **CorrelationAnalyzer**: Position correlation and hedging
4. **DrawdownAnalyzer**: Drawdown recovery patterns
5. **SeasonalityAnalyzer**: Time-of-day/week/month patterns
6. **VolatilityAnalyzer**: Volatility regime analysis
