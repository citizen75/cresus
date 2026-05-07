# Research Analysis Subagents - Complete Summary

## 🎯 Overview

Two new specialized subagents have been created to provide comprehensive analysis of trading strategy performance and order execution quality:

1. **PortfolioStatsAnalyzerAgent** - Analyzes portfolio metrics and performance
2. **OrdersAnalysisAgent** - Analyzes order execution quality and consistency

## 📊 PortfolioStatsAnalyzerAgent

**Purpose**: Analyze portfolio performance metrics and provide strategic recommendations based on strategy configuration.

**File**: `src/agents/research/sub_agents/stats_analyzer.py` (16.7 KB)

### Analysis Dimensions

1. **Returns Analysis**
   - Total return vs benchmark
   - Excess returns
   - Sharpe, Sortino, Calmar ratios
   - Assessment: excellent/good/acceptable/marginal/poor

2. **Risk Analysis**
   - Maximum drawdown percentage
   - Drawdown duration
   - Gross exposure level
   - Assessment: low/moderate/moderate-high/high

3. **Trade Quality**
   - Win rate percentage
   - Profit factor
   - Expectancy
   - Risk/Reward ratio
   - Assessment: excellent/good/acceptable/negative/marginal

4. **Position Management**
   - Holding period alignment
   - Trade duration patterns
   - Winner vs loser management
   - Assessment: good/passive/poor/acceptable

### Recommendations Generated

Automatically generates 5-15+ prioritized recommendations:

```
CRITICAL:
- Issues preventing profitability
- Fundamental strategy flaws

HIGH:
- Performance bottlenecks
- Risk management failures
- Signal quality problems

MEDIUM:
- Optimization opportunities
- Minor parameter adjustments

LOW:
- Edge case improvements
- Fine-tuning suggestions
```

### Example Recommendations

```
• Negative Sharpe Ratio
  Description: Risk-adjusted returns negative
  Action: Increase signal selectivity, raise entry thresholds

• Excessive Drawdown (21.6% over 91 days)
  Description: Max drawdown too large
  Action: Tighten stop loss or reduce position size

• Low Win Rate (25.2%)
  Description: Only 25% of trades profitable
  Action: Improve entry confirmation, add filters

• Excessive Trading (1.9 trades/day)
  Description: Too many orders
  Action: Add holding period filter or entry cooldown
```

## 📋 OrdersAnalysisAgent

**Purpose**: Analyze order execution quality and provide recommendations for improving order placement and diversification.

**File**: `src/agents/research/sub_agents/orders_analysis.py` (17 KB)

### Analysis Dimensions

1. **Position Sizing Consistency**
   - Size coefficient of variation
   - Consistency percentage (0-100%)
   - Zero-quantity detection
   - Formula effectiveness

2. **Order Timing Patterns**
   - Orders per day (average, min, max)
   - Peak order hour
   - Intra-day distribution
   - Activity consistency

3. **Order Balance**
   - Buy/sell ratio
   - Total quantity/value analysis
   - Imbalance detection
   - Signal effectiveness

4. **Ticker Analysis**
   - Orders per ticker
   - Most active tickers
   - Concentration percentage
   - Diversification assessment

5. **Price Analysis**
   - Average buy/sell prices
   - Price range
   - Zero-price detection
   - Execution quality

### Recommendations Generated

Automatically generates 5-12+ prioritized recommendations:

**Categories**:
- Position sizing consistency
- Order frequency patterns
- Signal balance (buy/sell)
- Portfolio concentration
- Order type effectiveness
- Pricing quality

### Example Recommendations

```
• Inconsistent Position Sizing (100% variation)
  Description: Position sizes vary widely
  Action: Implement fixed position size formula

• Excessive Daily Orders (67 peak, 1.9 avg)
  Description: Too many orders in one day
  Action: Add cooldown period or entry confirmation

• Buy/Sell Imbalance (3:1 ratio)
  Description: Too many buys, weak exits
  Action: Strengthen exit conditions

• High Ticker Concentration (75% in top 5)
  Description: Overly concentrated
  Action: Expand watchlist or diversify signals
```

## 🔄 Integration Flow

```
User Command:
  cresus flow run portfolio_analysis momentum_cac --backtest

↓

PortfolioAnalysisFlow:
  1. Load portfolio journal
  2. Calculate metrics (Sharpe, Sortino, drawdown, win rate, etc.)
  3. Store metrics in context

↓

ResearchAgent (orchestrator):
  1. JournalAnalyzerAgent     → Trade statistics
  2. OrderAnalyzerAgent       → Basic order counts
  3. IssueIdentifierAgent     → Critical issues
  4. PortfolioStatsAnalyzer   → Performance analysis + recommendations
  5. OrdersAnalysisAgent      → Order quality + recommendations

↓

Combine Results:
  - Identified issues (critical/high/medium/low)
  - Performance recommendations
  - Order execution recommendations

↓

CLI Display:
  📊 Portfolio Metrics (full breakdown)
  ✓/✗ Issues found
  💡 Recommendations (by category and priority)
    - 📊 Performance Recommendations
    - 📋 Order Execution Recommendations
```

## 📈 Example Output

```
Portfolio Analysis - BACKTEST MODE
════════════════════════════════════════════════════════════

📊 Portfolio Metrics
────────────────────────────────────────────────────────────
Start                                2026-01-06
End                                  2026-05-06
Period                                         120 days

Start Value                                    $9,997.60
End Value                                      $8,125.72
Total Return                                     -18.72 %

Win Rate                                        25.21 %
Profit Factor                                   0.606946
Sharpe Ratio                                   -3.062075
Max Drawdown                                     21.63 %

Total Trades                                         229

✓ No issues found!

💡 Recommendations (6)
────────────────────────────────────────────────────────────

📊 Performance Recommendations

HIGH PRIORITY

  1. Negative Sharpe Ratio (risk_adjusted_returns)
     Risk-adjusted returns are negative
     → Increase signal selectivity

  2. Excessive Drawdown (risk_management)
     Max drawdown of 21.6% over 91 days
     → Tighten stop loss or reduce position size

  3. Low Win Rate (signal_quality)
     Only 25.2% of trades are profitable
     → Improve signal filters

MEDIUM PRIORITY

  1. Excessive Trading (signal_quality)
     229 trades (avg 1.9 per day)
     → Add holding period filter

📋 Order Execution Recommendations

HIGH PRIORITY

  1. Inconsistent Position Sizing (position_sizing)
     Position sizes vary by 100% (low consistency)
     → Implement fixed position size formula
```

## 🔍 Strategy Configuration Integration

Both agents reference strategy YAML files:

```yaml
entry:
  parameters:
    position_size: 1000 / data["close"]        # OrdersAnalysis validates
    limit_price: data['close'] * 0.99          # OrdersAnalysis checks
    regime_filter: ...                          # PortfolioStats evaluates

exit:
  parameters:
    stop_loss: data['close'] - data['atr_14'] * 1.3
    take_profit: data['close'] + data['atr_14'] * 2.6
    holding_period: 12                         # Both analyze effectiveness
    time_stop: 1

signals:
  weights:
    momentum: 0.5                              # PortfolioStats evaluates impact
    trend: 0.35
    volume_anomaly: 0.15
```

## 📚 Documentation

Three comprehensive guides have been created:

1. **`docs/portfolio_stats_analyzer.md`**
   - PortfolioStatsAnalyzerAgent detailed guide
   - Metrics definitions and analysis logic
   - Recommendation types and examples

2. **`docs/orders_analysis_agent.md`**
   - OrdersAnalysisAgent detailed guide
   - Order analysis metrics and interpretation
   - Execution quality recommendations

3. **`docs/research_analysis_architecture.md`**
   - Complete architecture overview
   - Data flow and integration points
   - Cross-reference of metrics and recommendations

## 🚀 Usage

### Command Line

```bash
# Analyze backtest with all recommendations
cresus flow run portfolio_analysis momentum_cac --backtest

# Analyze live portfolio with recommendations
cresus flow run portfolio_analysis momentum_cac

# View any strategy
cresus flow run portfolio_analysis any_strategy_name --backtest
```

### Output Includes

1. **Portfolio Metrics** (comprehensive statistics)
   - Dates, returns, ratios
   - Trade statistics
   - Risk metrics

2. **Issues Identified** (critical problems)
   - No trades, zero orders
   - Data inconsistencies
   - Severity levels

3. **Performance Recommendations** (strategy tuning)
   - Signal improvements
   - Risk management
   - Position sizing
   - Trade frequency

4. **Order Execution Recommendations** (execution quality)
   - Sizing consistency
   - Order frequency patterns
   - Diversification
   - Balance improvements

## ✅ Files Created/Modified

### New Files
- ✅ `src/agents/research/sub_agents/stats_analyzer.py` (16.7 KB)
- ✅ `src/agents/research/sub_agents/orders_analysis.py` (17 KB)
- ✅ `docs/portfolio_stats_analyzer.md`
- ✅ `docs/orders_analysis_agent.md`
- ✅ `docs/research_analysis_architecture.md`

### Modified Files
- ✅ `src/agents/research/agent.py` - Added orchestration for both agents
- ✅ `src/agents/research/sub_agents/__init__.py` - Registered both agents
- ✅ `src/flows/portfolio_analysis.py` - Metrics calculated before research
- ✅ `src/cli/commands/flow.py` - Enhanced recommendations display

## 🎯 Key Features

### PortfolioStatsAnalyzerAgent
✅ Analyzes 4 key metrics dimensions
✅ Loads strategy configuration
✅ Generates 5-15+ recommendations
✅ Prioritizes by severity
✅ References actual metrics in recommendations
✅ Context-aware suggestions

### OrdersAnalysisAgent
✅ Analyzes order execution quality
✅ Detects sizing inconsistencies
✅ Identifies timing patterns
✅ Measures diversification
✅ Detects buy/sell imbalances
✅ Provides specific fix recommendations

### Integration
✅ Both agents work within ResearchAgent
✅ Share context and configuration
✅ Provide non-overlapping recommendations
✅ Display in organized sections
✅ Separate performance from execution issues

## 💡 Typical Recommendations

**From PortfolioStatsAnalyzer:**
- "Negative Sharpe Ratio: Increase signal selectivity"
- "Excessive Drawdown: Tighten stop loss"
- "Low Win Rate: Improve entry confirmation"
- "Excessive Trading: Add holding period"

**From OrdersAnalyzer:**
- "Inconsistent Position Sizing: Implement fixed formula"
- "Excessive Daily Orders: Add order cooldown"
- "Buy/Sell Imbalance: Strengthen exit signals"
- "High Concentration: Expand watchlist"

## 🔄 Process Summary

1. User runs portfolio analysis command
2. PortfolioAnalysisFlow loads journal and calculates metrics
3. ResearchAgent orchestrates 5 subagents:
   - Journal, Order, Issue analyzers (basic)
   - PortfolioStats analyzer (performance focus)
   - Orders analyzer (execution focus)
4. Results combined into comprehensive report
5. CLI displays issues and recommendations by category
6. User gets actionable advice for strategy improvement

## 📊 Testing

All features have been tested with:
- Backtest analysis (with --backtest flag)
- Live portfolio analysis (without --backtest flag)
- Multiple strategy configurations
- Empty portfolios
- High-volume portfolios (229+ trades)

## 🎓 Benefits

1. **Comprehensive Analysis** - 2 new specialized agents provide deep insights
2. **Actionable Recommendations** - Specific, prioritized suggestions
3. **Strategy-Aware** - References actual strategy configuration
4. **Non-Overlapping** - Different perspectives on performance vs execution
5. **Organized Display** - Separated by category and priority
6. **Complete Context** - Works with all analysis types (backtest, live)

---

**Next Steps**: Use recommendations to improve strategy configuration and re-run analysis to validate improvements.
