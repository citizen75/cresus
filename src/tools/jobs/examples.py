"""Examples demonstrating job management and agent orchestration."""

from pathlib import Path
from typing import Dict, Any
from queue import Queue
import time

from core.job import Job, JobStatus
from core.agent import Agent
from core.context import AgentContext
from tools.jobs import JobManager


# Example 1: Simple synchronous job with agent
def example_simple_job():
	"""Example: Execute agents synchronously in a job."""
	print("\n=== Example 1: Simple Synchronous Job ===")

	# Create job manager
	manager = JobManager()

	# Create a job
	config = {
		"agents": ["data_fetcher", "calculator"],
		"strategy": "momentum",
	}
	job = manager.create_job("backtest_cac40_20260618", config)
	job.start()

	try:
		# Simulate agents
		class DataFetcherAgent(Agent):
			def process(self, input_data=None):
				self.logger.info("Fetching data...")
				time.sleep(0.5)  # Simulate work
				return {
					"status": "success",
					"output": {"data": [1, 2, 3, 4, 5]},
				}

		class CalculatorAgent(Agent):
			def process(self, input_data=None):
				self.logger.info("Calculating...")
				data = self.context.get("previous_output", {}).get("data", [])
				result = sum(data)
				return {
					"status": "success",
					"output": {"result": result},
				}

		# Execute agents in job
		fetcher = DataFetcherAgent("DataFetcher", job.context)
		result1 = job.call_agent_sync(fetcher, {})

		job.context.set("previous_output", result1.get("output"))

		calculator = CalculatorAgent("Calculator", job.context)
		result2 = job.call_agent_sync(calculator, {})

		# Store results and complete
		job.set_result("fetch_output", result1.get("output"))
		job.set_result("calculation_result", result2.get("output"))
		job.complete(job.results)
		job.save_metadata()

		print(f"✓ Job completed: {job.name}")
		print(f"  Status: {job.status.value}")
		print(f"  Results: {job.results}")

	except Exception as e:
		job.fail(str(e))
		job.save_metadata()
		print(f"✗ Job failed: {e}")


# Example 2: Asynchronous job with queue
def example_async_job():
	"""Example: Execute agents asynchronously via queue."""
	print("\n=== Example 2: Asynchronous Job with Queue ===")

	manager = JobManager()
	job = manager.create_job("train_model_20260618", {
		"model_type": "LightGBM",
		"train_set": "historical_data",
	})
	job.start()

	# Create queue for async tasks
	task_queue = Queue()

	try:
		class TrainerAgent(Agent):
			def process(self, input_data=None):
				self.logger.info("Training model...")
				time.sleep(1)  # Simulate training
				return {
					"status": "success",
					"output": {"model_id": "model_v1", "accuracy": 0.92},
				}

		trainer = TrainerAgent("ModelTrainer", job.context)

		# Queue agents asynchronously
		task_id_1 = job.call_agent_async(trainer, task_queue, {"epochs": 100})
		task_id_2 = job.call_agent_async(trainer, task_queue, {"epochs": 200})

		# Process queue (would normally be done by a worker pool)
		print(f"✓ Queued 2 training tasks")
		print(f"  Task 1: {task_id_1}")
		print(f"  Task 2: {task_id_2}")

		# Simulate queue processing
		processed = 0
		while not task_queue.empty():
			task = task_queue.get()
			print(f"  Processing: {task['task_id']} (agent: {task['agent_name']})")
			result = task["agent"].run(task["input_data"])
			processed += 1

		job.set_result("tasks_processed", processed)
		job.complete(job.results)
		job.save_metadata()

		print(f"✓ Job completed: {job.name}")
		print(f"  Status: {job.status.value}")

	except Exception as e:
		job.fail(str(e))
		job.save_metadata()
		print(f"✗ Job failed: {e}")


# Example 3: Job management operations
def example_job_management():
	"""Example: Job management operations."""
	print("\n=== Example 3: Job Management ===")

	manager = JobManager()

	# Create multiple jobs
	jobs = []
	for i in range(3):
		job = manager.create_job(f"test_job_{i:03d}", {
			"iteration": i,
			"status": "pending",
		})
		jobs.append(job)

		if i == 0:
			job.start()
			job.complete({"result": "success"})
			job.save_metadata()
		elif i == 1:
			job.start()
			job.fail("Test error")
			job.save_metadata()
		# i == 2 remains pending

	# List and summarize jobs
	print(f"✓ Created 3 test jobs")

	summary = manager.get_jobs_summary()
	print(f"  Job Summary:")
	print(f"    Total: {summary['total']}")
	print(f"    Pending: {summary['pending']}")
	print(f"    Running: {summary['running']}")
	print(f"    Success: {summary['success']}")
	print(f"    Error: {summary['error']}")

	# List jobs by status
	successful = manager.list_jobs(JobStatus.SUCCESS)
	print(f"  Successful jobs: {successful}")

	failed = manager.list_jobs(JobStatus.ERROR)
	print(f"  Failed jobs: {failed}")

	# Get job directories
	for job_name in manager.list_jobs():
		job_dir = manager.get_job_dir(job_name)
		print(f"  Job '{job_name}' directory: {job_dir}")

	# Cleanup
	deleted = manager.cleanup_old_jobs(keep_count=1, status_filter=JobStatus.SUCCESS)
	print(f"✓ Cleaned up: deleted {deleted} old jobs")

	# Delete all test jobs
	for job_name in manager.list_jobs():
		if manager.delete_job(job_name):
			print(f"  Deleted: {job_name}")


# Example 4: Job configuration
def example_job_config():
	"""Example: Working with job configuration."""
	print("\n=== Example 4: Job Configuration ===")

	manager = JobManager()

	config = {
		"name": "backtest_strategy",
		"description": "Backtest momentum strategy on CAC40",
		"parameters": {
			"market": "CAC40",
			"strategy": "momentum",
			"period": 20,
			"lookback_days": 500,
		},
		"agents": [
			{"name": "DataAgent", "params": {"universe": "cac40"}},
			{"name": "IndicatorAgent", "params": {"indicators": ["rsi_14", "ema_20"]}},
			{"name": "BacktestAgent", "params": {"initial_capital": 100000}},
		],
		"output_services": [
			{"type": "file", "params": {"path": "results.csv"}},
			{"type": "gsheet", "params": {"sheet_name": "_results"}},
		],
	}

	# Save configuration
	config_path = manager.save_config("backtest_config_example", config)
	print(f"✓ Configuration saved to: {config_path}")

	# Load configuration
	loaded_config = manager.load_config("backtest_config_example")
	print(f"✓ Configuration loaded:")
	print(f"  Name: {loaded_config['name']}")
	print(f"  Market: {loaded_config['parameters']['market']}")
	print(f"  Agents: {len(loaded_config['agents'])}")

	# Cleanup
	manager.delete_job("backtest_config_example")


if __name__ == "__main__":
	print("Job Management System Examples")
	print("=" * 50)

	example_simple_job()
	example_async_job()
	example_job_management()
	example_job_config()

	print("\n" + "=" * 50)
	print("✓ All examples completed")
