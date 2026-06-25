# Unified Execution Pattern: Agent, Flow, Job, Bot

Cresus uses a consistent execution pattern across all major execution models: **Agent**, **Flow**, **Job**, and **Bot**.

## Pattern Overview

All execution models follow the same two-method pattern:

```python
class ExecutionModel:
    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Public API with error handling, validation, and instrumentation."""
        # Validate inputs
        # Call process()
        # Handle errors
        # Persist state
        # Return response

    def process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Override in subclasses for custom logic."""
        # Implement domain-specific logic
        # Return response dict with status and output
```

## Response Format

All execution models return a consistent response dictionary:

```python
{
    "status": "success" | "error",
    "params": {...},          # Input parameters
    "output": {...},          # Execution results
    "message": "..."          # Error message (only if status="error")
}
```

### Status Values
- `"success"` - Execution completed successfully
- `"error"` - Execution failed

### Response Structure Example

**Success Response:**
```python
{
    "status": "success",
    "params": {"market": "cac40", "capital": 100000},
    "output": {
        "trades": 10,
        "pnl": 5000,
        "positions": [...]
    }
}
```

**Error Response:**
```python
{
    "status": "error",
    "params": {"market": "cac40", "capital": 100000},
    "output": {},
    "message": "Market data unavailable"
}
```

## Execution Models

### 1. Agent

**Purpose:** Process a single unit of work with validation

**Pattern:**
```python
from core.agent import Agent

class MyAgent(Agent):
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Implement logic
        return {
            "status": "success",
            "input": input_data,
            "output": {...}
        }

agent = MyAgent("my_agent")
response = agent.run(input_data={"key": "value"})
```

**Use Cases:**
- Single data transformations
- Calculations and analytics
- Validation checks
- Signal generation

**Key Methods:**
- `run(input_data)` - Public API
- `process(input_data)` - Override for custom logic

---

### 2. Flow

**Purpose:** Orchestrate multiple agents or operations

**Pattern:**
```python
from core.flow import Flow

class MyFlow(Flow):
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Orchestrate operations
        return {
            "status": "success",
            "input": input_data,
            "output": {...}
        }

flow = MyFlow("my_flow")
response = flow.run(input_data={"key": "value"})
```

**Use Cases:**
- Multi-step workflows
- Agent orchestration
- Conditional execution
- Parallel processing

**Key Methods:**
- `run(input_data)` - Public API
- `process(input_data)` - Override for orchestration logic

---

### 3. Job

**Purpose:** Long-running asynchronous task with persistence

**Pattern:**
```python
from core.job import Job
from pathlib import Path

class MyJob(Job):
    def process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implement long-running logic
        return {
            "status": "success",
            "params": params,
            "output": {...}
        }

job = MyJob("my_job", Path("./jobs/my_job"))
response = job.run(params={"key": "value"})
# Metadata automatically saved
```

**Use Cases:**
- Backtesting strategies
- Data synchronization
- Model training
- Report generation

**Key Methods:**
- `run(params)` - Public API (auto-persists state)
- `process(params)` - Override for custom logic
- `save_metadata()` - Persist state
- `load_metadata()` - Restore state

**State Persistence:**
- Automatically saves to `~/.cresus/db/jobs/<job_name>/metadata.json`
- Automatic timestamps and duration tracking
- Result storage and retrieval

---

### 4. Bot

**Purpose:** Autonomous trading operation with isolated environment

**Pattern:**
```python
from core.bot import Bot
from pathlib import Path

class MyBot(Bot):
    def process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implement trading logic
        return {
            "status": "success",
            "params": params,
            "output": {...}
        }

bot = MyBot("my_bot", Path("./bots/my_bot"))
bot.activate()
response = bot.run(params={"market": "cac40"})
# Only runs if bot is ACTIVE
```

**Use Cases:**
- Live trading
- Strategy execution
- Portfolio management
- Market monitoring

**Key Methods:**
- `run(params)` - Public API (only if ACTIVE)
- `process(params)` - Override for trading logic
- `activate()` / `deactivate()` - State management
- `save_metadata()` - Persist state

**State Management:**
- ACTIVE / INACTIVE / ERROR / STOPPED states
- Automatically saves to `~/.cresus/db/bots/<bot_name>/metadata.json`
- Only executes when ACTIVE

---

## Comparison Table

| Aspect | Agent | Flow | Job | Bot |
|--------|-------|------|-----|-----|
| **Purpose** | Single task | Orchestration | Long-running task | Trading strategy |
| **Duration** | Seconds | Seconds-Minutes | Minutes-Hours | Continuous |
| **Persistence** | Context | Context | File system | File system |
| **Error Handling** | Automatic | Automatic | Automatic | Automatic |
| **State Tracking** | In memory | In memory | Metadata JSON | Metadata JSON |
| **Execution Control** | Direct | Direct | Automatic | State-gated |
| **Params Name** | `input_data` | `input_data` | `params` | `params` |

---

## Usage Patterns

### Sequential Execution

```python
# Agent -> Agent
agent1 = Agent1("agent1")
result1 = agent1.run(input_data={"x": 1})

agent2 = Agent2("agent2")
result2 = agent2.run(input_data=result1["output"])

# Job -> Job
job1 = MyJob("step1", Path("./jobs/step1"))
result1 = job1.run(params={"stage": 1})

job2 = MyJob("step2", Path("./jobs/step2"))
result2 = job2.run(params=result1["output"])
```

### Flow with Agents

```python
class MyFlow(Flow):
    def process(self, input_data):
        # Run agents
        agent1_result = self.run_agent(Agent1(), input_data)
        agent2_result = self.run_agent(Agent2(), agent1_result["output"])
        
        return {
            "status": "success",
            "input": input_data,
            "output": agent2_result["output"]
        }

flow = MyFlow("my_flow")
result = flow.run(input_data={"key": "value"})
```

### Job with Async Agents

```python
class BacktestJob(Job):
    def process(self, params):
        # Run agents asynchronously
        data_result = self.call_agent_async(DataAgent(), params)
        analysis_result = self.call_agent_async(AnalysisAgent(), params)
        
        return {
            "status": "success",
            "params": params,
            "output": {
                "data": data_result,
                "analysis": analysis_result
            }
        }
```

### Bot with Strategy Execution

```python
class TradingBot(Bot):
    def process(self, params):
        market = params.get("market", "cac40")
        
        # Fetch market data
        data = self.fetch_data(market)
        
        # Generate signals
        signals = self.generate_signals(data)
        
        # Execute trades
        trades = self.execute_trades(signals)
        
        return {
            "status": "success",
            "params": params,
            "output": {
                "trades": trades,
                "pnl": self.calculate_pnl(trades)
            }
        }

bot = TradingBot("my_bot", Path("./bots/my_bot"))
bot.activate()
result = bot.run(params={"market": "cac40"})
```

---

## Error Handling

All execution models handle errors consistently:

```python
result = model.run(params)

if result["status"] == "error":
    error_message = result["message"]
    # Handle error
else:
    output = result["output"]
    # Use output
```

### Exception Handling in process()

```python
def process(self, params):
    try:
        # Do work
        result = do_work(params)
        return {
            "status": "success",
            "params": params,
            "output": result
        }
    except Exception as e:
        return {
            "status": "error",
            "params": params,
            "output": {},
            "message": str(e)
        }
```

The `run()` method catches exceptions and returns error responses automatically.

---

## Logging

All execution models include automatic logging via `self.logger`:

```python
class MyAgent(Agent):
    def process(self, input_data):
        self.logger.info("Starting processing")
        self.logger.debug(f"Input keys: {list(input_data.keys())}")
        
        result = do_work(input_data)
        
        self.logger.info("Processing complete")
        return {
            "status": "success",
            "input": input_data,
            "output": result
        }
```

Logs are written to:
- **Agent/Flow:** Console and context
- **Job:** `~/.cresus/db/jobs/<name>/job.log`
- **Bot:** `~/.cresus/db/bots/<name>/bot.log`

---

## Context Access

All execution models have access to shared context:

```python
class MyAgent(Agent):
    def process(self, input_data):
        # Access context
        value = self.context.get("key")
        
        # Set context
        self.context.set("key", "value")
        
        return {
            "status": "success",
            "input": input_data,
            "output": {}
        }
```

Context allows data sharing between agents, flows, jobs, and bots.

---

## Migration Guide

### From Old Job Pattern to New Pattern

**Old:**
```python
job = MyJob("test", Path("./jobs/test"))
job.start()
try:
    result = job.execute()  # Custom method
    job.complete(result)
except Exception as e:
    job.fail(str(e))
job.save_metadata()
```

**New:**
```python
job = MyJob("test", Path("./jobs/test"))
result = job.run(params={...})  # Handles all state management
```

### From Old Bot Pattern to New Pattern

**Old:**
```python
bot.start_trading()
try:
    trades = bot.execute_strategy()  # Custom method
    bot.save_results(trades)
except Exception as e:
    bot.stop()
```

**New:**
```python
bot.activate()
result = bot.run(params={...})  # Handles all state management
```

---

## Best Practices

1. **Always Return Proper Response Dict**
   ```python
   return {
       "status": "success" | "error",
       "params": params,
       "output": {...},
       "message": "..."  # Only if error
   }
   ```

2. **Use Try/Except in process()**
   ```python
   def process(self, params):
       try:
           result = do_work(params)
           return {"status": "success", "params": params, "output": result}
       except Exception as e:
           return {"status": "error", "params": params, "output": {}, "message": str(e)}
   ```

3. **Don't Override run()**
   Override `process()` for custom logic, not `run()`.

4. **Use Logging**
   ```python
   self.logger.info("Starting work")
   self.logger.error("Something went wrong")
   ```

5. **Let run() Handle State**
   Don't manually call start/complete/fail methods in process().

---

## Examples

### Agent Example

```python
from core.agent import Agent

class CalculatorAgent(Agent):
    def process(self, input_data):
        x = input_data.get("x", 0)
        y = input_data.get("y", 0)
        result = x + y
        
        return {
            "status": "success",
            "input": input_data,
            "output": {"sum": result}
        }

agent = CalculatorAgent("calculator")
response = agent.run(input_data={"x": 5, "y": 3})
# response["output"]["sum"] == 8
```

### Job Example

```python
from core.job import Job
from pathlib import Path

class DataSyncJob(Job):
    def process(self, params):
        sources = params.get("sources", [])
        data = {}
        
        for source in sources:
            data[source] = self.fetch_from_source(source)
        
        return {
            "status": "success",
            "params": params,
            "output": {"data": data}
        }

job = DataSyncJob("sync_job", Path("./jobs/sync_job"))
result = job.run(params={"sources": ["source1", "source2"]})
# Metadata saved automatically
```

### Bot Example

```python
from core.bot import Bot
from pathlib import Path

class SimpleTradingBot(Bot):
    def process(self, params):
        market = params.get("market")
        capital = params.get("capital", 100000)
        
        # Generate signals
        signals = self.generate_signals(market)
        
        # Execute trades
        trades = []
        for signal in signals:
            trade = self.execute_trade(signal, capital)
            trades.append(trade)
        
        return {
            "status": "success",
            "params": params,
            "output": {"trades": trades}
        }

bot = SimpleTradingBot("trader", Path("./bots/trader"))
bot.activate()
result = bot.run(params={"market": "cac40", "capital": 100000})
```

---

## See Also

- **Agent**: `src/core/agent.py`
- **Flow**: `src/core/flow.py`
- **Job**: `src/core/job.py`
- **Bot**: `src/core/bot.py`
- **Job Management**: `src/tools/jobs/README.md`
- **Bot Management**: `src/tools/bot/README.md`
