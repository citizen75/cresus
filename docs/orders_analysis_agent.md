# Orders Analysis Agent

A specialized subagent within the Research agent framework that analyzes order execution quality, effectiveness, and provides strategic recommendations based on strategy configuration.

## Overview

The `OrdersAnalysisAgent` examines order placement, execution patterns, and sizing consistency to identify issues with order generation and provide actionable improvement recommendations.

## Features

### 1. Order Execution Analysis

**Position Sizing Consistency**
- Calculates position size coefficient of variation
- Detects zero-quantity orders
- Compares against strategy position_size formula
- Assessment: consistency percentage (0-100%)

**Order Timing Analysis**
- Daily order frequency patterns
- Peak order hours
- Intra-day distribution
- Busiest trading days
- Variability assessment

**Order Balance Analysis**
- Buy/sell order ratio
- Total quantity and value by operation
- Imbalance detection
- Order flow assessment

**Ticker-Level Analysis**
- Orders per ticker
- Most active tickers
- Concentration detection
- Per-ticker buy/sell counts

**Price Analysis**
- Average buy/sell prices
- Price range analysis
- Zero-price order detection
- Execution quality

### 2. Strategy Configuration Integration

Automatically loads strategy YAML and:
- Validates position_size formula effectiveness
- Checks limit_price implementation
- References entry/exit parameters
- Analyzes signal configuration impact

### 3. Intelligent Recommendations

Generates prioritized recommendations:
- **CRITICAL**: Order execution bugs or data errors
- **HIGH**: Significant execution quality issues
- **MEDIUM**: Optimization opportunities
- **LOW**: Minor improvements

### 4. Recommendation Categories

**Order Execution**
- Position sizing consistency
- Zero quantity/price orders
- Order fill quality

**Order Frequency**
- Excessive daily orders
- Inconsistent daily activity
- Peak hour concentration

**Signal Quality**
- Buy/sell imbalance
- Order generation effectiveness
- Signal confirmation

**Portfolio Management**
- Ticker concentration
- Position diversification
- Order distribution

**Order Type**
- Limit order effectiveness
- Market order needs
- Fill rate analysis

## Usage

### Via CLI

```bash
# Analyze backtest with full recommendations
cresus flow run portfolio_analysis momentum_cac --backtest

# Analyze live portfolio with recommendations
cresus flow run portfolio_analysis momentum_cac
```

### Output Format

```
📋 Order Execution Recommendations

HIGH PRIORITY

  1. Inconsistent Position Sizing (position_sizing)
     Position sizes vary by 100% (low consistency)
     → Implement fixed position size formula.

MEDIUM PRIORITY

  1. Excessive Daily Orders (order_frequency)
     Peak of 67 orders in a single day (avg 1.9)
     → Consider adding cooldown period between orders.
```

## Analysis Sections

### Sizing Analysis

```python
{
    "avg_buy_size": 26.5,
    "avg_sell_size": 24.3,
    "min_size": 1.2,
    "max_size": 52.1,
    "size_std_dev": 14.2,
    "size_consistency_pct": 46.3,  # Higher is better
    "zero_quantity_orders": 0,
}
```

**Interpretation:**
- Consistency < 50% → Inconsistent sizing
- Consistency > 80% → Good sizing consistency
- Zero quantity orders → Critical bug

### Timing Analysis

```python
{
    "avg_orders_per_day": 1.9,
    "max_orders_per_day": 67,
    "min_orders_per_day": 0,
    "peak_hour": 14,        # 2 PM peak
    "total_days": 121,
}
```

**Interpretation:**
- Max orders > 50 → Excessive daily activity
- Std dev > mean → Bursty order generation
- Single peak hour → Concentrated order placement

### Order Balance Analysis

```python
{
    "total_buy_quantity": 6087.2,
    "total_sell_quantity": 5943.1,
    "total_buy_value": $143,250,
    "total_sell_value": $139,862,
    "imbalance_ratio": 1.02,  # Buy/Sell ratio
}
```

**Interpretation:**
- Ratio > 2.0 → Too many buys (weak exits)
- Ratio < 0.5 → Too many sells (weak entries)
- Ratio ~1.0 → Balanced trading

### Ticker Analysis

```python
{
    "total_tickers": 29,
    "most_active": ["MC", "OREP", "GTO", "AC", "GLEN"],
    "concentration_pct": 42.3,  # Top 5 tickers
}
```

**Interpretation:**
- Concentration > 70% → Over-concentrated
- Concentration 40-70% → Moderate focus
- Concentration < 40% → Well-diversified

## Recommendation Logic

### Position Sizing Issues

**Inconsistent Sizing** (consistency < 50%)
- **Cause**: Position size formula not being applied consistently
- **Fix**: Verify position_size formula in entry config
- **Example**: `position_size: 1000 / data["close"]` should be consistent

**Zero Quantity Orders** (>0 found)
- **Cause**: Division by infinity or formula returning 0
- **Severity**: CRITICAL
- **Fix**: Check position_size formula for infinity/NaN handling

### Order Frequency Issues

**Excessive Orders** (max > 50 per day)
- **Cause**: Too many signal confirmations on same ticker
- **Fix**: Add cooldown period or holding period filter
- **Example**: Reduce entry confirmation count, increase entry thresholds

**Inconsistent Activity** (std dev > mean)
- **Cause**: Order generation concentrated at specific times
- **Fix**: Verify watchlist updates happen regularly
- **Example**: Check scheduler frequency, entry conditions

### Buy/Sell Imbalance

**Too Many Buys** (ratio > 2.0)
- **Cause**: Weak or missing exit conditions
- **Fix**: Improve sell_conditions or add time-based exits
- **Example**: Add trailing stop or holding_period exit

**Too Many Sells** (ratio < 0.5)
- **Cause**: Entries too aggressive, exits too early
- **Fix**: Strengthen buy_conditions or soften exit thresholds
- **Example**: Increase entry confirmation, reduce stop loss

### Concentration Issues

**High Concentration** (concentration > 70%)
- **Cause**: Strategy focused on few stocks
- **Fix**: Increase watchlist size or diversify entry conditions
- **Example**: Expand universe or add cross-sectional ranking

**Low Ticker Diversity**
- **Cause**: Universe filter too strict
- **Fix**: Relax entry filters or expand ticker list
- **Example**: Lower volume requirement, increase max_count

## Configuration References

Orders analysis references these strategy parameters:

```yaml
watchlist:
  parameters:
    tickers:
      max_count: 15          # Affects diversity
    volume:
      min_volume: 500000     # Affects candidate pool

entry:
  parameters:
    position_size:
      formula: 1000 / data["close"]
    limit_price:
      formula: data['close'] * 0.99     # 1% limit order
    regime_filter:
      formula: data['close'] > data['ema_20']

exit:
  parameters:
    holding_period: 12       # Max days per position
```

## Example Scenarios

### Scenario 1: Zero Quantity Orders

**Problem**: 23 orders placed with 0 quantity
**Analysis**: Position size formula returning zero
**Recommendation**: Check position_size calculation - likely dividing by zero or infinity
**Action**: 
```yaml
# Broken: might divide by NaN price
position_size: 1000 / data["close"]

# Fixed: add validation
position_size: max(1, 1000 / data["close"])
```

### Scenario 2: Inconsistent Sizing (100% variation)

**Problem**: Position sizes vary from 1 share to 50 shares
**Analysis**: Prices vary 50x, but sizing not accounting for it
**Recommendation**: Ensure position_size formula uses inverse price
**Action**: Verify formula works across price range

### Scenario 3: Excessive Buy Orders (3:1 ratio)

**Problem**: 300 buys but only 100 sells
**Analysis**: Exit signals weak or missing
**Recommendation**: Strengthen exit conditions
**Action**: Add confirmation to sell_conditions or trailing stop

### Scenario 4: Peak Order Hour

**Problem**: 80% of orders between 2-3 PM
**Analysis**: Watchlist updates concentrated at one time
**Recommendation**: Spread order generation across day
**Action**: Add multiple scheduler times or continuous monitoring

## Integration Points

```
ResearchAgent (orchestrator)
├── JournalAnalyzerAgent ─────────→ Trade statistics
├── OrderAnalyzerAgent ───────────→ Basic order counts
├── IssueIdentifierAgent ────────→ Critical issues
├── PortfolioStatsAnalyzerAgent → Performance metrics + recs
└── OrdersAnalysisAgent ─────────→ Order execution quality + recs
```

## Files Modified

- `src/agents/research/agent.py` - Added OrdersAnalysisAgent orchestration
- `src/agents/research/sub_agents/__init__.py` - Registered OrdersAnalysisAgent
- `src/agents/research/sub_agents/orders_analysis.py` - NEW: Implementation
- `src/cli/commands/flow.py` - Enhanced recommendations display with separate sections

## Testing

```bash
# Full backtest analysis with order recommendations
python -m src.cli.main flow run portfolio_analysis momentum_cac --backtest

# Live portfolio analysis
python -m src.cli.main flow run portfolio_analysis momentum_cac

# Check order analysis data structure
python -c "
from src.agents.research.sub_agents.orders_analysis import OrdersAnalysisAgent
agent = OrdersAnalysisAgent()
# Set up context and test
"
```

## Key Metrics Explained

| Metric | Range | Interpretation |
|--------|-------|-----------------|
| Size Consistency | 0-100% | % consistency (higher better) |
| Imbalance Ratio | 0.5-2.0 | Sweet spot; <0.5 or >2.0 problematic |
| Orders/Day | Variable | <5 sparse, 5-20 normal, >50 excessive |
| Concentration | 0-100% | %orders from top 5 tickers |
| Peak Hour | 0-23 | Hour with most orders (0=midnight) |
| Ticker Count | Variable | Number of distinct tickers traded |

## Performance Impact

Orders analysis recommendations can improve:
- **Fill rates** by identifying limit order issues
- **Position sizing** by ensuring consistent capitalization
- **Diversification** by reducing ticker concentration
- **Consistency** by identifying order frequency issues
- **Profitability** by reducing transaction frequency
