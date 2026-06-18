# Jobs Quick Start Guide

## Overview

Specialized jobs for trading operations:

- **BotPremarket** - Pre-market setup and opportunity identification
- **BotIntraday** - Active position management during trading hours
- **BotBacktest** - Historical strategy testing and analysis
- **BotDataSync** - Market data synchronization and validation

## Installation

Jobs are part of the Cresus package. They integrate with the Job and JobManager classes:

```bash
# Install in dev mode
pip install -e .
```

## Quick Examples

### Create and Run Pre-Market Job

```python
from jobs import BotPremarket
from tools.jobs import JobManager

manager = JobManager()
job = manager.create_job("premarket_monday")

# Execute pre-market workflow
summary = job.execute_premarket()

print(f"Opportunities found: {summary['opportunities_found']}")
print(f"Positions ready: {summary['positions_ready']}")
```

### Create and Run Intraday Job

```python
from jobs import BotIntraday
from tools.jobs import JobManager

manager = JobManager()
job = manager.create_job("intraday_monday")

portfolio = {
    "positions": [
        {"ticker": "AC.PA", "quantity": 100, "pnl": 250, "pnl_pct": 0.05}
    ]
}

rules = {"exits": {"stop_loss": -0.05, "take_profit": 0.10}}

summary = job.run_intraday_cycle(portfolio, rules)
print(f"Trades executed: {summary['trades_executed']}")
```

### Create and Run Backtest Job

```python
from jobs import BotBacktest
from tools.jobs import JobManager

manager = JobManager()
job = manager.create_job("backtest_momentum")

config = {
    "tickers": ["AC.PA", "OR.PA"],
    "start_date": "2025-01-01",
    "end_date": "2026-01-01",
    "strategy": {"name": "momentum"},
    "initial_capital": 100000
}

summary = job.run_backtest(config)
print(f"Return: {summary['total_return']:.2%}")
print(f"Sharpe: {summary['sharpe_ratio']:.2f}")
```

### Create and Run Data Sync Job

```python
from jobs import BotDataSync
from tools.jobs import JobManager

manager = JobManager()
job = manager.create_job("data_sync_daily")

config = {
    "sources": ["yfinance"],
    "tickers": ["AC.PA", "OR.PA"],
    "fields": ["close", "high", "low", "volume"],
    "yfinance_credentials": {}
}

summary = job.run_sync(config)
print(f"Tickers updated: {summary['tickers_updated']}")
```

## CLI Usage

```bash
# Create a job (uses template from init/templates/jobs.yml)
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

## Job Lifecycle

All jobs have the same lifecycle:

```
created (PENDING)
    ↓
started (RUNNING)
    ↓
completed → SUCCESS
    ↓
    → ERROR (failed)
    ↓
    → CANCELLED (manually stopped)
```

Access status:

```python
job = manager.get_job("my_job")
print(job.status.value)  # "success", "error", "pending", "running", "cancelled"
```

## Storing and Retrieving Results

Store results during execution:

```python
job.set_result("metric_name", value)
job.set_result("sharpe_ratio", 1.42)
```

Retrieve results after completion:

```python
sharpe = job.get_result("sharpe_ratio")
metrics = job.get_result("metrics")
```

## File Structure

Jobs are stored at `~/.cresus/db/jobs/<job_name>/`:

```
~/.cresus/db/jobs/my_backtest/
├── config.yml          # Job configuration
├── metadata.json       # Job metadata, results, timing
├── job.log            # Main job log
└── backtest.log       # Custom logs (optional)
```

## Accessing Job Data

```python
job = manager.get_job("my_backtest")

# Timing information
print(f"Created: {job.created_at}")
print(f"Duration: {job.get_duration_seconds()} seconds")

# Results
print(f"Results: {job.results}")

# Metadata
job.save_metadata()  # Persist to disk
job.load_metadata()  # Load from disk

# Dictionary representation
job_dict = job.to_dict()  # Get all job info as dict
```

## Error Handling

Jobs handle errors gracefully:

```python
try:
    summary = job.run_backtest(config)
except Exception as e:
    job = manager.get_job("backtest_name")
    print(f"Job failed: {job.error_message}")
    print(f"Status: {job.status.value}")  # "error"
```

## Running Tests

```bash
# Run all job tests
pytest tests/jobs/ -v

# Run specific test class
pytest tests/jobs/test_bot_premarket.py::TestBotPremarketWorkflow -v

# Run with coverage
pytest tests/jobs/ --cov=src/jobs
```

## Full Documentation

For complete documentation, see:

- **README.md** - Comprehensive API reference
- **examples.py** - Working code examples
- **../tools/jobs/README.md** - JobManager documentation
- **../cli/commands/JOBS_CLI.md** - CLI command reference

## Common Patterns

### Sequential Jobs (Pipeline)

```python
from tools.jobs import JobManager

manager = JobManager()

# Step 1: Sync data
sync = manager.create_job("sync_step")
sync.run_sync(sync_config)

# Step 2: Backtest
backtest = manager.create_job("backtest_step")
backtest.run_backtest(backtest_config)

# Step 3: Premarket (if backtest good)
if backtest.get_result("metrics")["total_return"] > 0:
    premarket = manager.create_job("premarket_step")
    premarket.execute_premarket()
```

### Parallel Job Monitoring

```python
jobs = []
for i in range(5):
    job = manager.create_job(f"backtest_{i}")
    jobs.append(job)

# Check status
for job in jobs:
    job = manager.get_job(job.name)
    print(f"{job.name}: {job.status.value}")
```

### Results Aggregation

```python
from tools.jobs import JobManager

manager = JobManager()

# Get all successful jobs
all_jobs = manager.list_jobs()
successful = [j for j in all_jobs if j.status == "success"]

# Aggregate results
total_return = sum(
    manager.get_job(j.name).get_result("metrics", {}).get("total_return_pct", 0)
    for j in successful
)
```

## Tips

1. **Job Names**: Use descriptive names with dates: `backtest_cac40_20260618`
2. **Configuration**: Use `init/templates/jobs.yml` as template for consistency
3. **Logging**: Jobs automatically log to `~/.cresus/db/jobs/<job_name>/job.log`
4. **Storage**: Job data persists automatically - jobs survive application restart
5. **Cleanup**: Use `jobs cleanup` to remove old jobs regularly

## Troubleshooting

**Job directory not found:**
```python
# Ensure directory structure exists
manager = JobManager()  # Creates ~/.cresus/db/jobs/
job = manager.create_job("my_job")  # Creates job subdirectory
```

**Results not saved:**
```python
job.set_result("key", value)
job.save_metadata()  # Don't forget to save!
```

**Job status stuck on RUNNING:**
```python
# Manually set status if job crashed
job = manager.get_job("stuck_job")
job.status = JobStatus.ERROR
job.error_message = "Manual error mark"
job.save_metadata()
```

## See Also

- `src/jobs/examples.py` - Full working examples
- `src/jobs/README.md` - Complete documentation
- `src/core/job.py` - Job class implementation
- `src/tools/jobs/__init__.py` - JobManager implementation
