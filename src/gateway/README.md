# Cresus Gateway

Unified server combining FastAPI backend, MCP protocol server, and APScheduler-based cron jobs.

## Overview

The Gateway server provides:
- **API Server**: FastAPI-based REST API on configurable host/port
- **MCP Server**: Model Context Protocol server for LLM tool integration
- **Cron Scheduler**: APScheduler-based job scheduler for automated tasks
- **Multithreading**: All services run concurrently in separate threads

## Starting the Gateway

### From CLI

```bash
python src/gateway/main.py
```

### From Code

```python
from gateway.server import create_gateway

gateway = create_gateway(
    api_host="0.0.0.0",
    api_port=8000,
    enable_cron=True
)
gateway.start()  # Blocking call
```

## Configuration

### Main Config (`config/cresus.yml`)

```yaml
servers:
  api:
    host: "0.0.0.0"
    port: 8000
  gateway:
    cron_enabled: true      # Enable/disable cron scheduler
    cron_config: "config/cron.yml"
    mcp_enabled: true       # Enable/disable MCP server
```

### Cron Jobs (`config/cron.yml`)

Define cron jobs to run agents or flows:

```yaml
jobs:
  - name: premarket_daily
    description: "Run premarket analysis"
    enabled: true
    schedule: "0 8 * * 1-5"  # 8:00 AM, Mon-Fri
    type: flow              # 'flow' or 'agent'
    target: premarket       # Flow/agent name
    params:
      strategy: momentum_cac
```

## Job Types

### Flow Jobs

Execute a flow with parameters:

```yaml
type: flow
target: premarket  # Must match a Flow subclass name
params:
  strategy: momentum_cac
```

Supported flows:
- `premarket` - PreMarketFlow

### Agent Jobs

Execute an agent with parameters:

```yaml
type: agent
target: strategy  # Must match an Agent class name
params:
  strategy: momentum_etf_fr
```

Supported agents:
- `strategy` - StrategyAgent
- `data` - DataAgent
- `watchlist` - WatchListAgent

## Cron Schedule Format

Uses standard cron syntax:

```
* * * * *
│ │ │ │ └─ Day of week (0-6, 0 = Sunday)
│ │ │ └─── Month (1-12)
│ │ └───── Day of month (1-31)
│ └─────── Hour (0-23)
└───────── Minute (0-59)
```

### Examples

- `0 8 * * 1-5` - 8:00 AM on weekdays (Mon-Fri)
- `0 * * * *` - Every hour
- `0 */6 * * *` - Every 6 hours
- `30 2 * * 0` - 2:30 AM on Sunday
- `0 9,17 * * *` - 9:00 AM and 5:00 PM daily

## Architecture

```
GatewayServer
├── API Thread
│   └── FastAPI Server (uvicorn)
│       └── API Routes (health, portfolios, watchlists, data, etc.)
├── MCP Thread
│   └── MCP Server (asyncio)
│       └── Portfolio Tools (list, details, performance, metrics, etc.)
└── Cron Thread
    └── APScheduler Scheduler
        └── Cron Jobs (agents/flows)
```

## Logging

Both API server and cron scheduler log to:
- Console (loguru)
- Log files (if configured in cresus.yml)

Cron job execution is logged with:
- Job start/completion
- Any errors during execution
- Filtered tickers and metrics

## Example: Enable Daily Premarket Analysis

1. Edit `config/cron.yml`:

```yaml
jobs:
  - name: premarket_daily
    description: "Daily premarket analysis"
    enabled: true
    schedule: "0 8 * * 1-5"
    type: flow
    target: premarket
    params:
      strategy: momentum_cac
```

2. Start the gateway:

```bash
python src/gateway/main.py
```

3. Check logs for scheduled job:

```
INFO     | gateway.cron.scheduler:_add_job:... - Added cron job 'premarket_daily': 0 8 * * 1-5
INFO     | gateway.cron.scheduler:_start_cron:... - Cron scheduler running with 1 jobs
```

## Troubleshooting

### Cron jobs not running

- Check `enabled: true` in `config/cron.yml`
- Verify cron schedule syntax
- Check logs for job execution errors
- Ensure `gateway.cron_enabled: true` in `config/cresus.yml`

### Port already in use

- Change `api.port` in `config/cresus.yml`
- Kill existing process: `lsof -ti:8000 | xargs kill -9`

### Scheduler not initialized

- Verify `config/cron.yml` exists
- Check cron job configurations for errors
- Look for validation warnings in logs

## Development

### Adding Support for New Agents/Flows

1. Update `scheduler.py`:
   - Add to `_call_flow()` flow_classes dict
   - Add to `_call_agent()` agent_classes dict

2. Define parameters in `config/cron.yml`

### Testing Cron Jobs

```python
from gateway.cron.scheduler import CronScheduler
from pathlib import Path

scheduler = CronScheduler(Path("config/cron.yml"))
for job in scheduler.get_jobs():
    print(f"Job: {job.name}, Trigger: {job.trigger}")
```
