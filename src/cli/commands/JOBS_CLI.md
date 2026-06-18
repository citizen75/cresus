# Jobs CLI Commands

Comprehensive CLI for managing long-running jobs in Cresus.

## Overview

The `jobs` command provides full control over job lifecycle, from creation through completion. Jobs are stored in `~/.cresus/db/jobs/<job_name>/` with configuration, metadata, logs, and results.

## Quick Start

```bash
# Create a job
cresus> jobs create my_backtest

# Start the job
cresus> jobs start my_backtest

# Check status
cresus> jobs info my_backtest

# Mark as complete
cresus> jobs complete my_backtest

# View results
cresus> jobs results my_backtest

# Delete the job
cresus> jobs delete my_backtest
```

## Commands Reference

### List Jobs

**List all jobs:**
```bash
cresus> jobs list
```

**List jobs by status:**
```bash
cresus> jobs list pending
cresus> jobs list running
cresus> jobs list success
cresus> jobs list error
cresus> jobs list cancelled
```

**Output:**
```
┏━━━━━━━━━━━━━━━━┳━━━━━━━┳─────────────────────────┳──────────┓
┃ Name           ┃ Status┃ Created                 ┃ Duration ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━╇─────────────────────────╇──────────┩
│ backtest_cac40 │ success │ 2026-06-18 14:30:00     │ 1523.5s  │
│ train_model    │ running │ 2026-06-18 15:00:00     │ 45.2s    │
└────────────────┴────────┴─────────────────────────┴──────────┘
```

### Show Summary

**Get job counts by status:**
```bash
cresus> jobs summary
```

**Output:**
```
┏─────────┳───────┓
┃ Status  ┃ Count ┃
┡─────────╇───────┤
│ pending │   2   │
│ running │   1   │
│ success │   5   │
│ error   │   1   │
│ cancelled│  0   │
│ Total   │   9   │
└─────────┴───────┘
```

### Create Job

**Create a new job:**
```bash
cresus> jobs create my_job_name
```

**Create with configuration file:**
```bash
cresus> jobs create my_job --config config.json
```

**Configuration file format (JSON):**
```json
{
  "market": "CAC40",
  "strategy": "momentum",
  "initial_capital": 100000,
  "agents": [
    "DataAgent",
    "IndicatorAgent",
    "BacktestAgent"
  ]
}
```

### Get Job Information

**Show complete job details:**
```bash
cresus> jobs info my_backtest
```

**Output:**
```
╔═══════════════════════════════════════╗
║ Job: my_backtest                      ║
╠═══════════════════════════════════════╣
║ Name: my_backtest                     ║
║ Status: success                       ║
║ Created: 2026-06-18 10:30:00         ║
║ Started: 2026-06-18 10:31:00         ║
║ Ended: 2026-06-18 10:47:00           ║
║ Duration: 960.00s                     ║
║ Agents Executed: 3                    ║
║ Results Keys: 4                       ║
║ Error: None                           ║
╚═══════════════════════════════════════╝

Agents:
  • DataFetcher
  • IndicatorCalculator
  • BacktestEngine

Results:
  • total_return: 0.152
  • sharpe_ratio: 1.42
  • max_drawdown: -0.08
  • trades: 45
```

### Start Job

**Mark job as running:**
```bash
cresus> jobs start my_backtest
```

This sets the status to "running" and records the start time.

### Complete Job

**Mark job as successfully completed:**
```bash
cresus> jobs complete my_backtest
```

**With results:**
```bash
cresus> jobs complete my_backtest --results '{"return": 0.15, "sharpe": 1.42}'
```

### Fail Job

**Mark job as failed with error message:**
```bash
cresus> jobs fail my_backtest "Data download failed"
```

### Delete Job

**Delete a job and all its data:**
```bash
cresus> jobs delete my_backtest
```

⚠️ This removes the entire job directory including config, logs, and results.

### Manage Configuration

**Show job configuration:**
```bash
cresus> jobs config my_backtest show
```

**Save configuration to file:**
```bash
cresus> jobs config my_backtest save exported_config.json
```

**Load configuration from file:**
```bash
cresus> jobs config my_backtest load new_config.json
```

### View Results

**Show all job results:**
```bash
cresus> jobs results my_backtest
```

**Get specific result:**
```bash
cresus> jobs results my_backtest sharpe_ratio
```

**Output:**
```
┏──────────────┳────────┓
┃ Key          ┃ Value  ┃
┡──────────────╇────────┤
│ total_return │ 0.152  │
│ sharpe_ratio │ 1.42   │
│ max_drawdown │ -0.08  │
│ trades       │ 45     │
└──────────────┴────────┘
```

### View Logs

**Show job log:**
```bash
cresus> jobs logs my_backtest
```

**Show custom log:**
```bash
cresus> jobs logs my_backtest data_fetch
```

Displays contents of `~/.cresus/db/jobs/my_backtest/job.log` or `~/.cresus/db/jobs/my_backtest/data_fetch.log`.

### Cleanup Old Jobs

**Delete old jobs, keeping most recent:**
```bash
cresus> jobs cleanup --keep 10
```

**Cleanup old failed jobs:**
```bash
cresus> jobs cleanup --keep 5 --status error
```

**Cleanup old successful jobs:**
```bash
cresus> jobs cleanup --status success
```

## Job Lifecycle Example

```bash
# 1. Create a new job
cresus> jobs create backtest_cac40_20260618
✓ Job created: backtest_cac40_20260618
  Directory: ~/.cresus/db/jobs/backtest_cac40_20260618

# 2. Load configuration (optional)
cresus> jobs config backtest_cac40_20260618 load config.json
✓ Configuration loaded from: config.json

# 3. Start the job
cresus> jobs start backtest_cac40_20260618
✓ Job started: backtest_cac40_20260618

# 4. Check status
cresus> jobs info backtest_cac40_20260618
[cyan]running[/cyan]

# 5. Complete the job with results
cresus> jobs complete backtest_cac40_20260618 --results '{"return": 0.15}'
✓ Job completed: backtest_cac40_20260618

# 6. View results
cresus> jobs results backtest_cac40_20260618
Total Return: 0.15

# 7. Cleanup old jobs
cresus> jobs cleanup --keep 10
✓ Cleaned up 3 old job(s)
```

## Job Status Values

| Status | Description | Transitions |
|--------|---|---|
| `pending` | Created but not started | → running, deleted |
| `running` | Currently executing | → success, error, cancelled |
| `success` | Completed successfully | → deleted |
| `error` | Failed with error message | → deleted |
| `cancelled` | Manually cancelled | → deleted |

## Job Directory Structure

```
~/.cresus/db/jobs/my_backtest/
├── config.yml              # Job configuration (YAML)
├── metadata.json           # Job metadata (status, results, timing)
├── job.log                 # Main job log
├── data_fetch.log          # Optional: custom log
└── indicator_calc.log      # Optional: custom log
```

## Storage

Jobs are stored in: `~/.cresus/db/jobs/`

Each job is a directory with:
- **config.yml**: YAML configuration file
- **metadata.json**: JSON metadata (auto-saved by job)
- **\*.log**: Log files (main and optional custom logs)

## Tips & Tricks

### Batch Operations

List all failed jobs and get details:
```bash
cresus> jobs list error
cresus> jobs info failed_job_1
cresus> jobs info failed_job_2
```

### Cleanup Strategy

Keep recent successful jobs, delete old failed ones:
```bash
cresus> jobs cleanup --keep 10 --status success
cresus> jobs cleanup --keep 0 --status error
```

### Configuration Management

Export job configuration:
```bash
cresus> jobs config my_job save job_backup.json
```

Re-use configuration for similar jobs:
```bash
cresus> jobs create new_job --config job_backup.json
```

### Monitoring

Monitor a running job:
```bash
cresus> jobs info running_job
cresus> jobs logs running_job
```

Wait for completion by polling status:
```bash
cresus> jobs list running
```

## Error Handling

**Job not found:**
```
✗ Job not found: nonexistent_job
```

**Invalid status:**
```
✗ Invalid status: pending_status
  Valid statuses: pending, running, success, error, cancelled
```

**Configuration error:**
```
✗ Failed to load config: No such file or directory
```

## Integration with Job Class

The CLI commands integrate with the Job and JobManager classes:

```python
from tools.jobs import JobManager

manager = JobManager()
job = manager.create_job("my_job")
job.start()
job.complete({"result": "value"})
job.save_metadata()
```

All CLI operations map to these underlying classes.

## See Also

- `Job` class: `/src/core/job.py`
- `JobManager` class: `/src/tools/jobs/__init__.py`
- Job tests: `/tests/core/test_job.py`, `/tests/tools/test_jobs.py`
- Job examples: `/src/tools/jobs/examples.py`
