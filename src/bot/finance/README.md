# BotFinance: Algorithmic Trading Bot

Finance-specific bot implementation for algorithmic trading with agent orchestration.

## Overview

BotFinance extends the base Bot class to implement a complete trading workflow with three distinct steps:

1. **pre_market** - Early market analysis and setup (before market open)
2. **in_market** - Active trading during market hours
3. **post_market** - Analysis and cleanup after market close

Each step runs a coordinated workflow of agents to analyze markets, generate signals, and manage portfolio.

## Architecture

```
BotFinance (extends Bot)
│
├── process(params)
│   └── params = {"step": "pre_market|in_market|post_market"}
│       │
│       ├── Common: _init_context()
│       │   ├── _load_configs()
│       │   ├── _load_portfolio()
│       │   ├── _get_tickers()
│       │   └── context.set(...all data...)
│       │
│       └── Step-specific:
│           ├── _process_pre_market()
│           ├── _process_in_market()
│           └── _process_post_market()
│
├── Agent Orchestration
│   ├── DataAgent: Market data fetching
│   ├── WatchlistAlphasAgent: Alpha generation
│   └── WatchListAgent: Watchlist management
│
└── Context Sharing
    └── All agents access shared AgentContext
```

## Usage

### Basic Usage

```python
from bot.finance import BotFinance
from pathlib import Path

# Create bot instance
bot = BotFinance("momentum_cac40", Path("./bots/momentum_cac40"))

# Activate bot
bot.activate()

# Run pre-market workflow
result = bot.run(params={"step": "pre_market"})

# Check results
if result["status"] == "success":
    output = result["output"]
    print(f"Agents executed: {output['agents_executed']}")
    print(f"Market data points: {len(output['market_data'])}")
    print(f"Alphas generated: {len(output['alphas'])}")
    print(f"Watchlist items: {len(output['watchlist'])}")
```

### Full Day Workflow

```python
bot = BotFinance("momentum_cac40", Path("./bots/momentum_cac40"))
bot.activate()

# Pre-market (9:00 AM)
pre_result = bot.run(params={"step": "pre_market"})
print(f"Pre-market: {pre_result['status']}")

# In-market (during market hours)
in_result = bot.run(params={"step": "in_market"})
print(f"In-market: {in_result['status']}")

# Post-market (after market close)
post_result = bot.run(params={"step": "post_market"})
print(f"Post-market: {post_result['status']}")
```

### With Scheduled Execution

```python
from apscheduler.schedulers.background import BackgroundScheduler

bot = BotFinance("momentum_cac40", Path("./bots/momentum_cac40"))
bot.activate()

scheduler = BackgroundScheduler()

# Pre-market: 9:00 AM
scheduler.add_job(
    lambda: bot.run(params={"step": "pre_market"}),
    'cron', hour=9, minute=0, day_of_week='mon-fri'
)

# In-market: Every hour 10 AM - 4 PM
scheduler.add_job(
    lambda: bot.run(params={"step": "in_market"}),
    'cron', hour='10-16', day_of_week='mon-fri'
)

# Post-market: 5:30 PM
scheduler.add_job(
    lambda: bot.run(params={"step": "post_market"}),
    'cron', hour=17, minute=30, day_of_week='mon-fri'
)

scheduler.start()
```

## Steps Explained

### Pre-Market (pre_market)

Executes before market open to prepare for trading.

**Workflow:**
1. Load bot config, strategy config, and portfolio
2. Initialize execution context with all data
3. Run DataAgent to fetch market data
4. Run WatchlistAlphasAgent to generate alphas
5. Run WatchListAgent to build watchlist

**Output:**
```python
{
    "step": "pre_market",
    "agents_executed": [
        "DataAgent[momentum_cac40]",
        "WatchlistAlphasAgent", 
        "WatchListAgent"
    ],
    "market_data": {...},      # Market data for all tickers
    "alphas": {...},           # Generated alphas
    "watchlist": [...],        # Top candidates
    "timestamp": "2026-06-18T09:00:00"
}
```

**Use Cases:**
- Prepare trading setup before market open
- Identify opportunities overnight
- Pre-calculate signals and alphas
- Build initial watchlist

### In-Market (in_market)

Active trading during market hours.

**Workflow:**
1. Load context and portfolio
2. Monitor positions
3. Execute trades based on signals
4. Scale in/out on price action
5. Manage stop losses and targets

**Output:**
```python
{
    "step": "in_market",
    "trades_executed": 3,
    "pnl": 1500.00,
    "positions": 2,
    "timestamp": "2026-06-18T10:15:00"
}
```

**Use Cases:**
- Execute live trades
- Monitor positions in real-time
- Scale in/out based on price action
- Manage risk and profit taking

### Post-Market (post_market)

Analysis and cleanup after market close.

**Workflow:**
1. Load daily results
2. Analyze trade performance
3. Update portfolio
4. Generate reports
5. Prepare for next day

**Output:**
```python
{
    "step": "post_market",
    "trades_analyzed": 5,
    "pnl_daily": 2000.00,
    "positions_closed": 1,
    "timestamp": "2026-06-18T17:30:00"
}
```

**Use Cases:**
- Analyze daily performance
- Close positions at end of day
- Calculate metrics
- Prepare reports

## Response Format

All methods return the standard response format:

```python
{
    "status": "success" | "error",
    "params": {...},           # Input parameters
    "output": {...},           # Step-specific output
    "message": "..."           # Error message (if error)
}
```

**Status Values:**
- `"success"` - Step executed successfully
- `"error"` - Step failed

## Context Management

BotFinance initializes a shared context with all necessary data:

```python
context = {
    "bot_name": "momentum_cac40",
    "strategy_name": "cac_top_5",
    "strategy_config": {...},      # Full strategy configuration
    "portfolio": {...},            # Portfolio state
    "tickers": [...],              # List of tickers to analyze
    "timestamp": "2026-06-18T09:00:00",
    
    # Updated by agents
    "market_data": {...},          # From DataAgent
    "alphas": {...},               # From WatchlistAlphasAgent
    "watchlist": [...],            # From WatchListAgent
}
```

All agents in the workflow access this shared context via `self.context`.

## Agent Orchestration

### DataAgent

**Purpose:** Fetch and process market data

**Input:**
```python
{
    "tickers": ["AC.PA", "OR.PA", ...],
    "strategy": "momentum_cac40",
    "timestamp": "2026-06-18T09:00:00"
}
```

**Output:**
```python
{
    "AC.PA": {
        "close": 50.25,
        "high": 51.00,
        "low": 49.50,
        "volume": 1000000,
        ...
    },
    ...
}
```

### WatchlistAlphasAgent

**Purpose:** Generate alpha scores for tickers

**Input:**
```python
{
    "tickers": ["AC.PA", "OR.PA", ...],
    "strategy": "momentum_cac40"
}
```

**Output:**
```python
{
    "AC.PA": 0.85,   # Alpha score
    "OR.PA": 0.72,
    "CS.PA": 0.65,
    ...
}
```

### WatchListAgent

**Purpose:** Build trading watchlist from alphas

**Input:**
```python
{
    "tickers": ["AC.PA", "OR.PA", ...],
    "strategy": "momentum_cac40",
    "alphas": {...}
}
```

**Output:**
```python
[
    "AC.PA",  # Top alpha
    "OR.PA",  # Second
    "CS.PA",  # Third
    ...
]
```

## Configuration

BotFinance uses two configuration files:

### Bot Config (config.yml)
```yaml
name: momentum_cac40
state: active
strategy: cac_top_5
portfolio:
  initial_capital: 100000
  risk_per_trade: 0.02
```

### Strategy Config (strategy.yml)
```yaml
name: cac_top_5
description: Top 5 CAC40 by momentum
tickers:
  - AC.PA
  - OR.PA
  - CS.PA
  - GLE.PA
  - SAF.PA
signals:
  - rsi_7
  - macd_12_26
buy_conditions: "rsi_7 > 50"
sell_conditions: "rsi_7 < 30"
```

## Error Handling

BotFinance handles errors gracefully at each step:

```python
# Invalid step
result = bot.run(params={"step": "invalid"})
# Returns: {"status": "error", "message": "Invalid step: ..."}

# Missing configuration
result = bot.run(params={"step": "pre_market"})
# Returns: {"status": "error", "message": "Failed to initialize context"}

# Agent failure
result = bot.run(params={"step": "pre_market"})
# Returns: {"status": "error", "message": "DataAgent failed"}
```

All errors are logged and returned in the response.

## File Structure

```
~/.cresus/db/bots/momentum_cac40/
├── config.yml              # Bot configuration
├── strategy.yml            # Strategy definition
├── portfolio.json          # Portfolio state
├── journal.csv             # Trade journal
├── watchlist.txt           # Current watchlist
├── metadata.json           # Bot metadata
└── bot.log                 # Execution logs
```

## Examples

See `examples.py` for working examples:

```bash
python src/bot/finance/examples.py
```

## Integration

### With Scheduler

Use APScheduler to run bot on schedule:

```python
scheduler.add_job(
    lambda: bot.run(params={"step": "pre_market"}),
    'cron', hour=9, minute=0
)
```

### With CLI

Use CLI commands to manage bot:

```bash
# Create bot
cresus> bot create momentum_cac40 cac_top_5

# Activate
cresus> bot activate momentum_cac40

# Run
cresus> bot run momentum_cac40 '{"step":"pre_market"}'

# Check portfolio
cresus> bot portfolio momentum_cac40
```

### With Jobs

Use Job system for backtesting:

```python
from jobs import BotBacktest

backtest = BotBacktest("test", Path("./jobs/test"))
result = backtest.run(params={
    "strategy": "cac_top_5",
    "start": "2025-01-01",
    "end": "2026-01-01"
})
```

## Performance

Each step typically executes in:
- **Pre-market:** 2-5 seconds (data fetch + analysis)
- **In-market:** 500ms-2 seconds (per execution)
- **Post-market:** 1-3 seconds (analysis + reporting)

## Logging

All operations are logged to `~/.cresus/db/bots/<bot_name>/bot.log`:

```
2026-06-18 09:00:00 INFO Processing step: pre_market
2026-06-18 09:00:00 DEBUG Context initialized successfully
2026-06-18 09:00:01 INFO Running DataAgent[momentum_cac40] for 5 tickers
2026-06-18 09:00:02 INFO Running WatchlistAlphasAgent
2026-06-18 09:00:03 INFO Running WatchListAgent
2026-06-18 09:00:03 INFO Pre-market workflow completed with 3 agents executed
```

## See Also

- **Bot Base Class:** `src/core/bot.py`
- **Bot Manager:** `src/tools/bot/__init__.py`
- **Agent:** `src/core/agent.py`
- **Examples:** `examples.py`
- **Execution Pattern:** `EXECUTION_PATTERN.md`
