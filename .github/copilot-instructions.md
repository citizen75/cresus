# Copilot Instructions for Cresus

This document provides essential guidance for AI assistants working in this repository.

## Project Overview

Cresus is a **portfolio management and backtesting platform** with a multi-agent architecture. It features:
- **Backend**: FastAPI REST API with multi-agent orchestration
- **Frontend**: React + TypeScript SPA with Tailwind CSS
- **MCP Server**: Model Context Protocol integration for Claude Desktop
- **Core Architecture**: Agent/Flow pattern with shared context

## Build & Install

### Install Dependencies

```bash
# Backend (Python 3.11+)
pip install -e .

# Frontend
npm install --prefix front
```

### Run Tests

```bash
# All tests
pytest

# Single test file
pytest tests/core/test_flow.py

# Single test function
pytest tests/core/test_flow.py::TestFlowInitialization::test_flow_initialization

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Start Services

**Option A: Using CLI (recommended)**
```bash
python src/cli/main.py
# Then at the prompt:
# > service start all -d
# > status
```

**Option B: Start individually**
```bash
# Terminal 1: API (port 8000)
python src/api/main.py

# Terminal 2: Frontend (port 5173)
cd front && npm run dev

# Terminal 3: MCP Server (for Claude Desktop)
python src/mcp/main.py
```

### Build Frontend

```bash
# Development build
npm run dev --prefix front

# Production build
npm run build --prefix front
```

## Architecture Patterns

### Agent/Flow System

Cresus uses a **composable multi-agent architecture**:

- **Agent**: Base class at `src/core/agent.py`
  - `process(input_data)` — override to implement logic
  - `run(input_data)` — public API with error handling
  - Always returns: `{"status", "input", "output", "message"}`
  - Access shared data via `self.context.get/set(key, value)`

- **Flow**: Base class at `src/core/flow.py`
  - Orchestrates sequential agent execution
  - Shares `AgentContext` across all steps
  - `add_step(agent, step_name, required)` for building pipelines
  - Stops on first required step failure

- **AgentContext**: Shared state dictionary at `src/core/context.py`
  - Thread-safe attribute-based access
  - Passed between agents and flows

### Key Flows

- **BacktestFlow** (`src/flows/backtest.py`) — Orchestrates multi-day backtesting
  - PreMarketFlow → TransactFlow → PostMarketFlow for each trading day
  - Runs ResearchAgent at end for analysis
  - Requires: `strategy` (name), optional `start_date`, `end_date`

- **WatchlistFlow** (`src/flows/watchlist.py`) — Analyzes universe of tickers
  - Chains: DataFetchFlow → StrategyFlow → EntryAgent → OrderAgent

- **DataFetchFlow** (`src/flows/data_fetch.py`) — Fetches market & fundamental data

### Agent Patterns

**Agent naming**: Use suffixes clearly:
- `XxxAgent` — Main orchestrator (uses flows internally)
- `XxxSubAgent` or `XxxAnalyzer` — Standalone analyzer (no sub-flows)

**Agent response format**:
```python
{
  "status": "success" | "error",
  "input": {...},
  "output": {...},  # agent-specific results
  "message": "error details only"
}
```

**Agent sub-classes pattern** (see `EntryAgent`):
- Orchestrator agents import `Flow` and `Agent`
- Add sub-agents with `flow.add_step(SubAgent, optional_name)`
- Access context via `self.context.get("key")`

### Tools Module

Located at `src/tools/`:
- **strategy/** — Load YAML configs via `StrategyManager`
- **portfolio/** — `PortfolioManager`, `PortfolioMetrics`, journal operations
- **data/** — Market data fetching (yfinance, fundamental data)
- **indicators/** — Technical indicator calculations
- **universe/** — Ticker universe filtering (e.g., CAC40, Russell 3000)
- **watchlist/** — Watchlist management via JSON files

## Key Conventions

### Import Paths

Always use relative imports within the src module:
```python
from core.flow import Flow
from agents.backtest.agent import BacktestAgent
from tools.portfolio import PortfolioManager
from flows.backtest import BacktestFlow
```

When ensuring imports from scripts (non-package entry points), explicitly add src to path:
```python
import sys
from pathlib import Path
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
```

### Logging

Use `loguru` for all logging (auto-injected into agents via context):
```python
self.logger.debug("message")    # Debug details
self.logger.info("message")     # User-facing info
self.logger.warning("message")  # Recoverable issues
self.logger.error("message")    # Errors (don't raise)
```

Never raise exceptions; instead:
- Log error with `logger.error()`
- Return error response: `{"status": "error", "message": "details"}`

### Data Storage

- **Portfolios**: `db/local/{portfolio_name}/` (JSON files, CSV journals)
- **Market Data Cache**: `db/local/data/`
- **Configs**: `config/` (YAML strategy configs, universe definitions)
- **Logs**: `logs/`

### Testing Conventions

- **Structure**: Mirror `src/` layout in `tests/` (e.g., `tests/core/`, `tests/agents/research/`)
- **Setup**: Use `conftest.py` for fixtures
- **Path handling**: Always add src to `sys.path` in test files (see `tests/core/test_flow.py`)
- **Naming**: `test_*.py` files, `Test*` classes, `test_*` methods

## Frontend Architecture

**Location**: `front/` directory
- **Build tool**: Vite
- **Framework**: React 18 + TypeScript
- **Styling**: Tailwind CSS + PostCSS
- **State**: Zustand
- **Queries**: TanStack React Query
- **HTTP**: Axios
- **Routing**: React Router v6
- **Charting**: Recharts

**Scripts**:
```bash
npm run dev      # Dev server (http://localhost:5173)
npm run build    # Production build to dist/
npm run preview  # Preview production build
```

## MCP Server Integration

The MCP server at `src/mcp/main.py` exposes Cresus tools to Claude Desktop:
- Located at `src/mcp/tools/`
- Register in `~/.config/Claude/claude_desktop_config.json`
- Requires env var: `CRESUS_PROJECT_ROOT`

Example tools available:
- List portfolios
- Get portfolio metrics
- View positions and journal
- Run backtests

## Important Notes

- **No linters configured** — Follow PEP 8 conventions manually
- **Python 3.11+** required (type hints, match statements)
- **Database**: Local file-based (JSON, CSV, Parquet), no migrations needed
- **Environment**: Create `.env` for local overrides; see `.env.local.example`
- **Tests are isolated** — Each test gets fresh fixtures via conftest.py

## Common Tasks

### Add a New Agent

1. Create `src/agents/myfeature/agent.py` inheriting from `Agent`
2. Implement `process(input_data)` with error handling (never raise)
3. Access context: `self.context.get("key")`
4. Return response dict with `status`, `input`, `output`, `message`
5. Add tests in `tests/agents/myfeature/test_agent.py`

### Add a Tool

1. Create `src/tools/myfeature/manager.py` with utility functions
2. Import via `from tools.myfeature import MyFeatureManager`
3. Use in agents by instantiating: `manager = MyFeatureManager()`

### Integrate a New Flow

1. Create `src/flows/myfeature.py` as `class MyFlow(Flow)`
2. Add steps with agents: `self.add_step(MyAgent(), "step_name")`
3. Return output from `process()`: `{"status": "success", "output": {...}}`
4. Use in orchestrator agents by instantiating and calling `process()`

## Useful Commands

```bash
# Run a specific backtest
pytest tests/agents/backtest/test_agent.py::TestBacktestAgent::test_backtest_execution

# Debug a test with print output
pytest -s tests/core/test_flow.py

# Run frontend type check only
npm run build --prefix front -- --mode type-check

# View API docs (when server running)
open http://localhost:8000/docs

# Check installed package info
pip show cresus
```
