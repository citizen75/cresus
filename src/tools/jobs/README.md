# Job Management System

Comprehensive job management system for orchestrating long-running tasks and agent execution in Cresus.

## Overview

The Job Management System provides:
- **Job Lifecycle**: Create, execute, monitor, and delete jobs
- **Agent Orchestration**: Call agents synchronously or asynchronously
- **Configuration Management**: YAML-based job configuration
- **Logging**: Per-job logging with automatic file management
- **Metadata Tracking**: Job execution metrics, results, and status

## Architecture

### File Structure

Jobs are stored in `~/.cresus/db/jobs/<job_name>/`:

```
~/.cresus/db/jobs/
├── backtest_cac40_20260618/
│   ├── config.yml              # Job configuration
│   ├── metadata.json           # Job metadata (status, results, etc.)
│   ├── job.log                 # Main job log
│   ├── data_fetch.log          # Optional: Additional logs
│   └── backtest.log            # Optional: Additional logs
└── train_model_20260618/
    ├── config.yml
    ├── metadata.json
    └── job.log
```

### Components

#### Job Class (`core/job.py`)

Represents a single long-running task:

```python
from core.job import Job, JobStatus

# Create job
job = Job("backtest_cac40", job_dir)

# Lifecycle methods
job.start()                      # Mark as running
job.complete(results)            # Mark as success
job.fail("Error message")        # Mark as failed
job.cancel()                     # Mark as cancelled

# Agent execution
result = job.call_agent_sync(agent, input_data)          # Synchronous
task_id = job.call_agent_async(agent, queue, input_data) # Asynchronous

# Result management
job.set_result("key", value)     # Store result
value = job.get_result("key")    # Retrieve result

# Persistence
job.save_metadata()              # Save to JSON
job.load_metadata()              # Load from JSON

# Metadata
job.status                       # JobStatus enum
job.results                      # Dict[str, Any]
job.agents_executed              # List of executed agent names
job.get_duration_seconds()       # Execution time
```

#### JobManager Class (`tools/jobs/__init__.py`)

Manages multiple jobs:

```python
from tools.jobs import JobManager

manager = JobManager()

# Job lifecycle
job = manager.create_job("backtest_cac40", config)        # Create
job = manager.get_job("backtest_cac40")                   # Load
manager.delete_job("backtest_cac40")                      # Delete

# List and query
jobs = manager.list_jobs()                                # All jobs
jobs = manager.list_jobs(JobStatus.RUNNING)               # Filter by status
summary = manager.get_jobs_summary()                      # Counts by status

# Configuration
manager.save_config("backtest_cac40", config)             # Save YAML
config = manager.load_config("backtest_cac40")            # Load YAML

# Utilities
job_dir = manager.get_job_dir("backtest_cac40")           # Directory path
log_file = manager.get_job_log_file("backtest_cac40")     # Log path
deleted_count = manager.cleanup_old_jobs(keep_count=10)   # Delete old jobs
```

## Usage Patterns

### Pattern 1: Simple Synchronous Job

Execute agents sequentially and wait for results:

```python
from core.job import Job
from tools.jobs import JobManager
from my_agents import DataFetcherAgent, AnalyzerAgent

# Create job
manager = JobManager()
job = manager.create_job("analyze_cac40")
job.start()

try:
    # Execute agents synchronously
    agent1 = DataFetcherAgent("DataFetcher", job.context)
    result1 = job.call_agent_sync(agent1, {"universe": "cac40"})
    
    # Pass data to next agent
    job.context.set("fetched_data", result1["output"])
    
    agent2 = AnalyzerAgent("Analyzer", job.context)
    result2 = job.call_agent_sync(agent2, {})
    
    # Store results and complete
    job.set_result("analysis", result2["output"])
    job.complete(job.results)

except Exception as e:
    job.fail(str(e))

finally:
    job.save_metadata()
```

### Pattern 2: Asynchronous Job with Queue

Queue tasks for parallel/background execution:

```python
from queue import Queue
from core.job import Job
from tools.jobs import JobManager
from my_agents import TrainerAgent

# Create job
manager = JobManager()
job = manager.create_job("train_models")
job.start()

task_queue = Queue()

try:
    trainer = TrainerAgent("ModelTrainer", job.context)
    
    # Queue multiple training tasks
    task_ids = []
    for config in training_configs:
        task_id = job.call_agent_async(trainer, task_queue, config)
        task_ids.append(task_id)
    
    print(f"Queued {len(task_ids)} training tasks")
    
    # Process queue (would be done by worker pool)
    while not task_queue.empty():
        task = task_queue.get()
        result = task["agent"].run(task["input_data"])
        job.logger.info(f"Task {task['task_id']} completed")
    
    job.complete(job.results)

except Exception as e:
    job.fail(str(e))

finally:
    job.save_metadata()
```

### Pattern 3: Configuration-Driven Job

Load job configuration from file and execute:

```python
from tools.jobs import JobManager

manager = JobManager()

# Save configuration
config = {
    "market": "CAC40",
    "strategy": "momentum",
    "agents": ["DataAgent", "IndicatorAgent", "BacktestAgent"],
}
manager.save_config("backtest_20260618", config)

# Later: Load and execute
config = manager.load_config("backtest_20260618")
job = manager.create_job("backtest_20260618", config)
job.start()

# Execute based on config
for agent_name in config["agents"]:
    agent_class = get_agent_class(agent_name)
    agent = agent_class(agent_name, job.context)
    result = job.call_agent_sync(agent, {})
    job.logger.info(f"Agent {agent_name} completed")

job.complete()
job.save_metadata()
```

### Pattern 4: Job Management and Monitoring

Query and manage multiple jobs:

```python
from tools.jobs import JobManager
from core.job import JobStatus

manager = JobManager()

# Get summary of all jobs
summary = manager.get_jobs_summary()
print(f"Total jobs: {summary['total']}")
print(f"Running: {summary['running']}")
print(f"Failed: {summary['error']}")

# List jobs by status
running_jobs = manager.list_jobs(JobStatus.RUNNING)
failed_jobs = manager.list_jobs(JobStatus.ERROR)

# Clean up old completed jobs
deleted = manager.cleanup_old_jobs(keep_count=10, status_filter=JobStatus.SUCCESS)
print(f"Deleted {deleted} old successful jobs")

# Monitor a specific job
job = manager.get_job("backtest_cac40")
if job:
    print(f"Job: {job.name}")
    print(f"Status: {job.status.value}")
    print(f"Duration: {job.get_duration_seconds():.2f}s")
    print(f"Results: {job.results}")
    print(f"Error: {job.error_message}")
```

## Job Lifecycle

### Status Transitions

```
PENDING → RUNNING → SUCCESS
              ↘ ERROR
              ↘ CANCELLED
```

### States

- **PENDING**: Job created but not started
- **RUNNING**: Job currently executing
- **SUCCESS**: Job completed successfully
- **ERROR**: Job failed with error
- **CANCELLED**: Job was cancelled

## Logging

Jobs include logging via the `Job.logger` instance:

```python
job.logger.info("Processing data...")     # Info level
job.logger.debug("Details...")             # Debug level
job.logger.warning("Watch out...")         # Warning level
job.logger.error("Something went wrong")   # Error level
```

Logs are stored in:
- `<job_dir>/job.log` - Main job log
- `<job_dir>/<log_name>.log` - Additional logs (custom names)

## Metadata Storage

Job metadata is automatically saved to `<job_dir>/metadata.json`:

```json
{
  "name": "backtest_cac40_20260618",
  "status": "success",
  "created_at": "2026-06-18T10:30:00",
  "started_at": "2026-06-18T10:31:00",
  "ended_at": "2026-06-18T10:45:00",
  "duration_seconds": 840.0,
  "agents_executed": ["DataFetcher", "Calculator", "Reporter"],
  "results": {
    "data_rows": 5000,
    "calculation_result": 123456.78
  },
  "error_message": null
}
```

## Agent Execution Modes

### Synchronous (Blocking)

```python
# Call agent and wait for result
result = job.call_agent_sync(agent, input_data)
# Continues after agent completes
```

**Use when:**
- Need immediate results
- Sequential dependencies between agents
- Simpler error handling

### Asynchronous (Non-Blocking)

```python
# Queue agent for execution
task_id = job.call_agent_async(agent, queue, input_data)
# Continues immediately, agent runs later
```

**Use when:**
- Parallel execution needed
- Long-running agents shouldn't block
- Distributed processing via worker pool

## Context Sharing

Job context is shared with all agents:

```python
# Set value in job context
job.context.set("fetched_data", data)

# Agent can access it
data = job.context.get("fetched_data")

# Merge job context into agent
for key in job.context.data:
    if not agent.context.get(key):
        agent.context.set(key, job.context.get(key))
```

## API Reference

### Job Class

```python
class Job:
    def __init__(name: str, job_dir: Path, context: Optional[AgentContext])
    def start() -> None
    def complete(results: Optional[Dict]) -> None
    def fail(error_message: str) -> None
    def cancel() -> None
    def call_agent_sync(agent, input_data) -> Dict[str, Any]
    def call_agent_async(agent, queue, input_data) -> str
    def set_result(key: str, value: Any) -> None
    def get_result(key: str, default: Any = None) -> Any
    def get_duration_seconds() -> Optional[float]
    def to_dict() -> Dict[str, Any]
    def save_metadata() -> None
    def load_metadata() -> bool
```

### JobManager Class

```python
class JobManager:
    def __init__(db_root: Optional[Path] = None)
    def create_job(name: str, config: Optional[Dict]) -> Job
    def get_job(name: str) -> Optional[Job]
    def delete_job(name: str) -> bool
    def list_jobs(status: Optional[JobStatus]) -> List[str]
    def get_jobs_summary() -> Dict[str, Any]
    def save_config(name: str, config: Dict) -> Path
    def load_config(name: str) -> Optional[Dict]
    def get_job_dir(name: str) -> Path
    def get_job_log_file(name: str, log_name: str) -> Path
    def cleanup_old_jobs(keep_count: int, status_filter: Optional[JobStatus]) -> int
```

## Examples

See `examples.py` for complete working examples:

```bash
cd src/tools/jobs
python examples.py
```

Examples include:
1. Simple synchronous job
2. Asynchronous job with queue
3. Job management operations
4. Job configuration

## Best Practices

1. **Always save metadata**: Call `job.save_metadata()` after job completes
2. **Handle errors**: Use try/except and call `job.fail(error_msg)` on exception
3. **Set descriptive names**: Use timestamps and identifiers (e.g., `backtest_cac40_20260618`)
4. **Configure before execution**: Save config before starting job
5. **Use context for sharing**: Pass data between agents via job context
6. **Clean up regularly**: Use `cleanup_old_jobs()` to manage storage
7. **Monitor status**: Check `job.status` and use `list_jobs()` for monitoring
8. **Log significant events**: Use `job.logger` for tracking job progress

## See Also

- `core/job.py` - Job class implementation
- `core/agent.py` - Agent base class
- `core/context.py` - Agent context
- Examples: `tools/jobs/examples.py`
