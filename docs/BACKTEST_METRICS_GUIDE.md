# Backtest Workflow & Portfolio Metrics - Complete Guide

## Quick Overview

The backtest system in Cresus consists of:

1. **BacktestFlow** - Orchestrates backtest execution with sandboxing
2. **BacktestAgent** - Loops through trading days in 3-phase cycles
3. **PortfolioManager** - Stores/retrieves portfolio state and metrics
4. **PortfolioMetrics** - Calculates financial metrics (mostly stubs)
5. **CLI Display** - Renders results (needs backtest-specific enhancement)

---

## 1. BacktestFlow.process() Return Structure

**File:** `src/flows/backtest.py` (lines 38-123)

The `BacktestFlow.process()` method returns a structured dictionary:

```python
{
    "status": "success",
    "output": {
        # METADATA (added by BacktestFlow)
        "backtest_id": "20250110_154523_a1b2c3d4",    # Unique run ID
        "backtest_dir": "/db/local/backtests/...",     # Sandboxed dir
        "portfolio": "Momentum cac",                    # Portfolio name
        
        # FROM BACKTEST AGENT
        "strategy_name": "momentum_cac",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "lookback_days": 365,
        "total_trading_days": 252,
        "days_processed": 251,
        
        # DAILY EXECUTION LOG
        "daily_results": [
            {"date": "2024-01-02"},
            {"date": "2024-01-03"},
            ...  # 251 entries
        ],
        
        # METRICS DICT (populated by post-market flow)
        "metrics": {},  # Currently empty
        
        # FINAL PORTFOLIO STATE
        "final_portfolio": {
            "name": "Momentum cac",
            "num_positions": 5,
            "num_trades": 47,
            "buy_trades": 28,
            "sell_trades": 19,
            "total_fees": 125.50,
            "total_gain_pct": 0.0,
            
            # Open positions at end of backtest
            "positions": [
                {
                    "ticker": "AAPL",
                    "quantity": 10,
                    "avg_entry_price": 150.25,
                    "current_price": 180.50,
                    "position_value": 1805.00,
                    "position_gain": 302.50,
                    "position_gain_pct": 20.12
                }
            ]
        }
    },
    "message": "Backtest 20250110_154523_a1b2c3d4 completed for momentum_cac"
}
```

### Key Points:
- **backtest_id**: Unique timestamp + UUID for run identification
- **backtest_dir**: Isolated directory (sandboxed, doesn't affect live portfolio)
- **daily_results**: One entry per execution day (execution dates, not calendar dates)
- **final_portfolio**: State of portfolio at end of backtest period
- **metrics**: Empty dict - meant to be populated by post-market flows but currently isn't

---

## 2. Portfolio Metrics Storage & Calculation

**Files:**
- `src/tools/portfolio/manager.py` - Core storage & retrieval
- `src/tools/portfolio/journal.py` - Transaction storage (SQLite)
- `src/tools/portfolio/cache.py` - Performance cache

### Storage Architecture

```
┌─────────────────────────────────────────┐
│ JOURNAL (SQLite - db/local/portfolios/) │
│─────────────────────────────────────────│
│ Stores each transaction:                │
│  • BUY/SELL: ticker, qty, price, fees  │
│  • CASH: deposits/withdrawals          │
│  • Status: pending/completed/cancelled │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│ PORTFOLIO MANAGER CALCULATIONS          │
│─────────────────────────────────────────│
│ On-demand calculation methods:          │
│  • get_portfolio_details() → positions │
│  • get_portfolio_performance() → trades│
│  • get_portfolio_cash() → available    │
│  • get_portfolio_summary() → combined  │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│ CACHE (JSON - performance optimization) │
│─────────────────────────────────────────│
│ Stores computed metrics for fast access│
│  • Position weights & values           │
│  • Aggregated statistics               │
│  • Portfolio config                    │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│ BACKTEST SANDBOXING                    │
│─────────────────────────────────────────│
│ When backtest_dir is in context:       │
│  ✓ Uses isolated journals              │
│  ✓ Separate portfolio directory        │
│  ✓ No live portfolio interference      │
└─────────────────────────────────────────┘
```

### Key Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| `get_portfolio_summary(name)` | Complete portfolio snapshot | details + performance |
| `get_portfolio_details(name)` | Positions and valuations | positions[], total_value |
| `get_portfolio_performance(name)` | Trading statistics | trades, fees, returns |
| `get_portfolio_cash(name)` | Available cash | float (EUR) |
| `get_portfolio_allocation(name)` | Position weights | positions with weight % |
| `calculate_portfolio_value(name)` | Current total value | total_value, positions |
| `calculate_portfolio_history(name)` | Daily equity curve | {date: value} history |
| `update_portfolio_cache(name)` | Refresh cache | stores in PortfolioCache |

---

## 3. Available Metrics

**File:** `src/tools/portfolio/metrics.py`

The `PortfolioMetrics` class extends `PortfolioManager` and provides `get_daily_metrics(name)`:

### Implemented Metrics ✓

These are calculated from journal transactions:

```python
{
    "num_trades": int,          # Total completed trades
    "buy_trades": int,          # Count of BUY orders
    "sell_trades": int,         # Count of SELL orders
    "total_fees": float,        # Sum of all transaction fees
    "total_gain_pct": float,    # Overall return percentage
}
```

### Stub Metrics ⚠️ (Return Hardcoded Values)

These methods exist but return hardcoded values, not actual calculations:

```python
{
    "sharpe_ratio": 1.5,           # Risk-adjusted return (STUB: always 1.5)
    "sortino_ratio": 2.0,          # Downside deviation (STUB: always 2.0)
    "calmar_ratio": 1.0,           # Return / max drawdown (STUB: always 1.0)
    
    "max_drawdown_pct": 5.0,       # Largest peak-to-trough % (STUB: always 5.0)
    "profit_factor": 1.5,          # Gross profit / loss ratio (STUB: always 1.5)
    
    "expectancy_pct": 0.5,         # Expected % per trade (STUB: always 0.5)
    "sqn": 1.5,                    # System Quality Number (STUB: always 1.5)
    "kelly_criterion_pct": 5.0,    # Optimal position size % (STUB: always 5.0)
}
```

### Per-Position Metrics

When fetching positions, each includes:

```python
{
    "ticker": str,
    "quantity": int,
    "avg_entry_price": float,          # Weighted average entry
    "current_price": float,            # Latest market price
    "position_value": float,           # quantity * current_price
    "position_gain": float,            # P&L in currency
    "position_gain_pct": float,        # P&L percentage
    "weight": float,                   # % of portfolio value
}
```

---

## 4. CLI Display - _print_flow_result()

**File:** `src/cli/app.py` (lines 362-520)

### Current Behavior

The `_print_flow_result()` method displays workflow results but has **no specialized handling for backtest output**.

**What it currently shows:**
- Status panel (green ✓ or red ✗)
- Generic metadata (flow, strategy, duration)
- Workflow-specific sections:
  - Signals (tickers with scores)
  - Watchlist (ticker list)
  - Orders (executable orders table)
  - Execution results (fills)
  - Execution history (step trace)
  - Context (key-value pairs with --context flag)

**What it's missing for backtest:**
- ❌ backtest_id display
- ❌ Portfolio summary table
- ❌ Performance metrics (trades, fees, gains)
- ❌ Positions table with P&L
- ❌ Daily results visualization
- ❌ Portfolio allocation
- ❌ Top holdings

### Example Current Output
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ✓ Workflow executed successfully      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
Flow: backtest
Strategy: momentum_cac
Duration: 5234ms

(No further output - backtest data not rendered)
```

---

## 5. Backtest Execution Flow

**File:** `src/agents/backtest/agent.py` (lines 96-220)

### Three-Phase Daily Cycle

For each trading day, the backtest follows this pattern:

```
For each trading day from start_date to end_date-1:

Day i                    Day i+1
┌──────────────────┐   
│ PRE-MARKET       │    current_date = Day i
├──────────────────┤    • Use data up to Day i
│ • Data ≤ Day i   │    • Generate signals
│ • Signals        │    • Create pending orders
│ • Create orders  │    
└──────────────────┘   
        ↓
┌──────────────────┐
│ INCREMENT        │    current_date = Day i+1
└──────────────────┘
        ↓
┌──────────────────┐   
│ MARKET           │    • Execute pending orders
├──────────────────┤    • Fill at Day i+1 prices
│ • Execute trades │    • Record transactions
│ • Fill prices    │    
│ • Record tx      │    
└──────────────────┘   
        ↓
┌──────────────────┐   
│ POST-MARKET      │    • Expire unmatched orders
├──────────────────┤    • Update portfolio
│ • Expire orders  │    • Update cache
│ • Update cache   │    • Append daily_results
│ • Metrics        │    
└──────────────────┘   
        ↓
daily_results.append({"date": "Day i+1"})
```

### Data Handling

- **Pre-market data**: Sliced to current_date (historical data only)
- **Market prices**: Full next_date OHLCV data (open, high, low, close, volume)
- **Efficiency**: Day data cached to avoid repeated filtering

---

## 6. Implementation Status

### ✅ FULLY IMPLEMENTED

- Backtest flow orchestration with sandboxing
- Portfolio transaction journal (SQLite storage)
- Position tracking and calculation
- Trade counting (buy/sell/cash operations)
- Transaction fee aggregation
- Position-level P&L (gain, gain_pct)
- Daily backtest loop (pre/market/post phases)
- Isolated backtest directories
- Portfolio cache layer
- Position allocation by weight
- Journal transaction replay

### ⚠️ PARTIALLY IMPLEMENTED

- Metrics display (only stub values returned)
- CLI output (generic, not backtest-specific)
- daily_results population (dates only, no metrics)

### ❌ NOT IMPLEMENTED

- Sharpe ratio calculation
- Sortino ratio calculation
- Calmar ratio calculation
- Max drawdown calculation
- Profit factor calculation
- Expectancy calculation
- System Quality Number (SQN)
- Kelly criterion calculation
- Equity curve / portfolio history in daily_results
- Backtest-specific CLI formatting
- Export functionality (CSV, JSON, HTML reports)
- Performance visualization

---

## 7. Data Flow Diagram

```
CLI Input: "flow run backtest momentum_cac 2024-01-01 2024-12-31"
    ↓
BacktestFlow.process(input_data)
    ├─ Creates backtest_id (YYYYMMdd_HHMMSS_XXXXX)
    ├─ Creates backtest_dir (db/local/backtests/backtest_id/)
    ├─ Sets context: {backtest_id, backtest_dir, portfolio_name}
    │
    ├─ BacktestAgent.process(input_data)
    │   ├─ StrategyAgent.run() → Load watchlist rules
    │   ├─ DataAgent.run() → Load historical OHLCV data
    │   ├─ FOR each trading day from start_date to end_date-1:
    │   │   ├─ PreMarketFlow.process() → Generate orders
    │   │   ├─ Increment current_date
    │   │   ├─ TransactFlow.process() → Execute orders
    │   │   ├─ PostMarketFlow.process() → Update metrics
    │   │   └─ daily_results.append({"date": execution_date})
    │   └─ Return backtest summary with daily_results[]
    │
    ├─ PortfolioManager(context).get_portfolio_summary(portfolio_name)
    │   ├─ Load journal from backtest_dir
    │   ├─ Calculate open positions
    │   ├─ Calculate performance metrics
    │   └─ Return final_portfolio
    │
    └─ Return enriched output:
        {
            "status": "success",
            "output": {
                backtest_id, backtest_dir, portfolio,
                strategy_name, start_date, end_date,
                total_trading_days, days_processed,
                daily_results[], metrics{},
                final_portfolio{}
            }
        }
        ↓
CLI._print_flow_result(result)
    ├─ Display status panel
    ├─ Display metadata (flow, strategy, duration)
    └─ ⚠️ No backtest-specific formatting (enhancement needed)
```

---

## 8. File References

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| BacktestFlow | `src/flows/backtest.py` | 38-123 | Orchestrates backtest with sandboxing |
| BacktestAgent | `src/agents/backtest/agent.py` | 96-220 | Loops through trading days |
| PortfolioManager | `src/tools/portfolio/manager.py` | 16-497 | Portfolio storage & retrieval |
| PortfolioMetrics | `src/tools/portfolio/metrics.py` | 8-47 | Metrics calculations |
| PortfolioHistory | `src/tools/portfolio/portfolio_history.py` | 17+ | Daily value replay |
| Journal | `src/tools/portfolio/journal.py` | - | Transaction storage |
| PortfolioCache | `src/tools/portfolio/cache.py` | - | Performance cache |
| CLI Display | `src/cli/app.py` | 362-520 | Result rendering |

---

## 9. Example Complete Output

```python
{
    "status": "success",
    "output": {
        "backtest_id": "20250110_154523_a1b2c3d4",
        "backtest_dir": "/Volumes/Data/dev/cresus/db/local/backtests/20250110_154523_a1b2c3d4",
        "portfolio": "Momentum cac",
        
        "strategy_name": "momentum_cac",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "lookback_days": 365,
        "total_trading_days": 252,
        "days_processed": 251,
        
        "daily_results": [
            {"date": "2024-01-02"},
            {"date": "2024-01-03"},
            # ... 251 total
        ],
        
        "metrics": {},
        
        "final_portfolio": {
            "name": "Momentum cac",
            "num_positions": 5,
            "num_trades": 47,
            "buy_trades": 28,
            "sell_trades": 19,
            "total_fees": 125.50,
            "total_gain_pct": 0.0,
            
            "positions": [
                {
                    "ticker": "AAPL",
                    "quantity": 10,
                    "avg_entry_price": 150.25,
                    "current_price": 180.50,
                    "position_value": 1805.00,
                    "position_gain": 302.50,
                    "position_gain_pct": 20.12
                },
                {
                    "ticker": "MSFT",
                    "quantity": 5,
                    "avg_entry_price": 300.00,
                    "current_price": 420.00,
                    "position_value": 2100.00,
                    "position_gain": 600.00,
                    "position_gain_pct": 40.00
                }
            ]
        }
    },
    "message": "Backtest 20250110_154523_a1b2c3d4 completed for momentum_cac"
}
```

---

## 10. Next Steps for Enhancement

### Priority 1: Implement Metric Calculations
- Replace stub methods in `PortfolioMetrics` with actual calculations
- Calculate metrics from daily portfolio values and returns
- Add equity curve calculation

### Priority 2: CLI Display Enhancement
- Add backtest-specific section to `_print_flow_result()`
- Create tables for:
  - Backtest metadata (ID, dates, days processed)
  - Performance summary (trades, returns, fees)
  - Final positions with P&L
  - Risk metrics (drawdown, Sharpe, etc.)

### Priority 3: Daily Metrics Population
- Populate `daily_results` with daily metrics
- Calculate daily returns and equity curve
- Track drawdown progression

### Priority 4: Export Functionality
- Add backtest report generation
- Support CSV, JSON, and HTML formats
- Include charts (equity curve, drawdown)

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-10  
**Author:** Codebase Analysis
