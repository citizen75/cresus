# Specialized Jobs

This package contains specialized job implementations for different trading scenarios. Each job class extends the base `Job` class and provides domain-specific functionality.

## Overview

Jobs are long-running tasks that process financial data and execute trading operations. The specialized jobs provide pre-built workflows for common trading scenarios.

## Available Jobs

### 1. BotPremarket - Pre-Market Trading Bot

Pre-market analysis and setup for market open.

**Key Methods:**
- `fetch_overnight_data()` - Load overnight data and news
- `calculate_indicators()` - Calculate pre-market indicators
- `identify_opportunities()` - Find trading opportunities
- `setup_positions()` - Prepare positions for market open
- `execute_premarket()` - Run full pre-market workflow

**Use Cases:**
- Prepare trading setup before market open
- Identify gap opportunities
- Setup initial positions and orders

**Example:**
```python
from jobs import BotPremarket
from tools.jobs import JobManager

manager = JobManager()
premarket = manager.create_job("premarket_monday")

summary = premarket.execute_premarket()
print(f"Opportunities found: {summary['opportunities_found']}")
print(f"Positions ready: {summary['positions_ready']}")
```

---

### 2. BotIntraday - Intraday Trading Bot

Active portfolio management during trading hours.

**Key Methods:**
- `monitor_positions()` - Track active positions
- `check_exit_conditions()` - Identify positions to exit
- `execute_scale_in()` - Add to positions
- `execute_scale_out()` - Reduce positions
- `record_market_event()` - Log significant events
- `run_intraday_cycle()` - Execute full intraday workflow

**Use Cases:**
- Monitor and adjust positions throughout the day
- Scale in/out based on price action
- Manage stop losses and take profits
- Track market events and opportunities

**Example:**
```python
from jobs import BotIntraday
from tools.jobs import JobManager

manager = JobManager()
intraday = manager.create_job("intraday_monday")

portfolio = {
    "positions": [
        {"ticker": "AC.PA", "quantity": 100, "pnl": 250, "pnl_pct": 0.05}
    ]
}

rules = {
    "exits": {
        "stop_loss": -0.05,
        "take_profit": 0.10
    }
}

summary = intraday.run_intraday_cycle(portfolio, rules)
print(f"Trades executed: {summary['trades_executed']}")
print(f"Total P&L: ${summary['total_pnl']:.2f}")
```

---

### 3. BotBacktest - Backtesting Bot

Historical strategy testing and performance analysis.

**Key Methods:**
- `load_historical_data()` - Load price history
- `apply_strategy()` - Apply strategy logic
- `simulate_trades()` - Run historical trades
- `calculate_metrics()` - Compute performance metrics
- `generate_report()` - Create detailed report
- `run_backtest()` - Execute full backtest workflow

**Use Cases:**
- Test new strategies on historical data
- Optimize strategy parameters
- Calculate performance metrics (Sharpe, drawdown, win rate)
- Generate backtest reports

**Example:**
```python
from jobs import BotBacktest
from tools.jobs import JobManager

manager = JobManager()
backtest = manager.create_job("backtest_momentum_cac40")

config = {
    "tickers": ["AC.PA", "OR.PA"],
    "start_date": "2025-01-01",
    "end_date": "2026-01-01",
    "strategy": {"name": "momentum"},
    "initial_capital": 100000
}

summary = backtest.run_backtest(config)
print(f"Total return: {summary['total_return']:.2%}")
print(f"Win rate: {summary['win_rate']:.2%}")
print(f"Sharpe ratio: {summary['sharpe_ratio']:.2f}")
```

---

### 4. BotDataSync - Data Synchronization Bot

Keep market data synchronized from multiple sources.

**Key Methods:**
- `connect_to_source()` - Connect to data provider
- `fetch_ticker_data()` - Fetch data for tickers
- `validate_data()` - Check data quality
- `reconcile_data()` - Compare multiple sources
- `update_database()` - Store validated data
- `run_sync()` - Execute full sync workflow

**Use Cases:**
- Synchronize price data from multiple sources
- Validate data quality before use
- Reconcile data between providers
- Keep local database current

**Example:**
```python
from jobs import BotDataSync
from tools.jobs import JobManager

manager = JobManager()
data_sync = manager.create_job("data_sync_daily")

config = {
    "sources": ["yfinance"],
    "tickers": ["AC.PA", "OR.PA"],
    "fields": ["close", "high", "low", "volume"],
    "yfinance_credentials": {}
}

summary = data_sync.run_sync(config)
print(f"Tickers updated: {summary['tickers_updated']}")
print(f"Records updated: {summary['records_updated']}")
print(f"Errors: {summary['errors']}")
```

---

## Job Lifecycle

All specialized jobs follow a consistent lifecycle:

```
PENDING -> RUNNING -> SUCCESS/ERROR/CANCELLED
```

### States:
- **PENDING**: Job created but not started
- **RUNNING**: Job is executing
- **SUCCESS**: Job completed successfully
- **ERROR**: Job failed with error
- **CANCELLED**: Job was cancelled

### Key Methods (inherited from Job):
- `start()` - Mark as running
- `complete(results)` - Mark as successful
- `fail(error_message)` - Mark as failed
- `cancel()` - Cancel execution
- `save_metadata()` - Persist state
- `get_result(key)` - Get result value
- `set_result(key, value)` - Store result

---

## Job Storage

Jobs are stored in `~/.cresus/db/jobs/<job_name>/`:

```
~/.cresus/db/jobs/premarket_monday/
├── config.yml           # Job configuration
├── metadata.json        # Job metadata, results, timing
├── job.log             # Main job log
└── premarket.log       # Optional custom logs
```

### Configuration (config.yml)

Jobs load default configuration from `init/templates/jobs.yml`:

```yaml
description: "Pre-market trading analysis"
parameters:
  market: "cac40"
  initial_capital: 100000

agents:
  - name: "DataAgent"
    params:
      universe: "cac40"
  - name: "IndicatorAgent"
    params:
      indicators: ["RSI", "MACD"]

services:
  logging:
    level: "INFO"
    format: "json"
```

---

## Creating Custom Jobs

To create a new specialized job:

```python
from core.job import Job, JobStatus
from pathlib import Path
from typing import Optional, Dict, Any

class MyCustomJob(Job):
    """Custom job implementation."""

    def __init__(self, name: str, job_dir: Path, context=None):
        super().__init__(name, job_dir, context)
        self.custom_data = {}

    def my_operation(self) -> Dict[str, Any]:
        """Perform custom operation."""
        self.logger.info("Running custom operation")
        
        result = {"status": "success"}
        self.set_result("my_operation", result)
        
        return result

    def execute_workflow(self) -> Dict[str, Any]:
        """Execute full workflow."""
        self.start()
        
        try:
            result = self.my_operation()
            self.complete(result)
            return result
        except Exception as e:
            self.fail(str(e))
            raise
```

Then register in `src/jobs/__init__.py`:

```python
from .my_custom_job import MyCustomJob

__all__ = ["BotPremarket", "BotIntraday", "BotBacktest", "BotDataSync", "MyCustomJob"]
```

---

## Job Management via CLI

Use the jobs CLI to manage specialized jobs:

```bash
# Create a job (uses init/templates/jobs.yml as default config)
cresus> jobs create premarket_monday

# Start the job
cresus> jobs start premarket_monday

# Check status
cresus> jobs info premarket_monday

# View results
cresus> jobs results premarket_monday

# View logs
cresus> jobs logs premarket_monday

# List all jobs
cresus> jobs list

# Delete the job
cresus> jobs delete premarket_monday
```

---

## Using Jobs Programmatically

```python
from tools.jobs import JobManager
from jobs import BotPremarket, BotBacktest

manager = JobManager()

# Create a job
job = manager.create_job("my_backtest")

# Run workflow
if isinstance(job, BotBacktest):
    config = {
        "tickers": ["AC.PA"],
        "start_date": "2025-01-01",
        "end_date": "2026-01-01",
        "strategy": {"name": "momentum"},
        "initial_capital": 100000
    }
    summary = job.run_backtest(config)

# Access results
results = job.get_result("metrics")
status = job.status.value

# Save for later
job.save_metadata()

# Load later
loaded_job = manager.get_job("my_backtest")
```

---

## Job Context

Each job has an `AgentContext` for sharing data with agents:

```python
job = BotPremarket("premarket", Path("."))

# Store data in context
job.context.set("market", "cac40")
job.context.set("capital", 100000)

# Access from agents
market = job.context.get("market")

# Pass to agents
job.call_agent_sync(my_agent, {"context": job.context})
```

---

## Performance Metrics

Jobs track execution metrics:

```python
job = manager.get_job("my_backtest")

# Timing
print(f"Duration: {job.get_duration_seconds()} seconds")
print(f"Created: {job.created_at}")
print(f"Started: {job.started_at}")
print(f"Ended: {job.ended_at}")

# Results
print(f"Status: {job.status.value}")
print(f"Error: {job.error_message}")
print(f"Agents executed: {len(job.agents_executed)}")
```

---

## Examples

See `src/jobs/examples.py` for complete working examples:

```bash
# Run all examples
python src/jobs/examples.py
```

---

## Integration with Job Manager

The specialized jobs work seamlessly with `JobManager`:

```python
from tools.jobs import JobManager
from jobs import BotPremarket

manager = JobManager()

# Create a job (uses template from init/templates/jobs.yml)
premarket = manager.create_job("premarket_monday")

# Run workflow
summary = premarket.execute_premarket()

# Get job
job = manager.get_job("premarket_monday")

# List all jobs
jobs = manager.list_jobs()

# Delete job
manager.delete_job("premarket_monday")
```

---

## See Also

- **Job Class**: `/src/core/job.py` - Base job implementation
- **JobManager**: `/src/tools/jobs/__init__.py` - Job orchestration
- **Jobs CLI**: `/src/cli/commands/jobs.py` - CLI command interface
- **Templates**: `/init/templates/jobs.yml` - Default configuration
