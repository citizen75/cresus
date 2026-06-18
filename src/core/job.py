"""Job class for processing long-running tasks."""

import json
import time
from datetime import datetime
from typing import Any, Dict, Optional, List
from pathlib import Path
from enum import Enum

from .context import AgentContext
from .logger import AgentLogger

# Response status constants
STATUS_SUCCESS = "success"
STATUS_ERROR = "error"


class JobStatus(str, Enum):
	"""Job status enumeration."""
	PENDING = "pending"
	RUNNING = "running"
	SUCCESS = "success"
	ERROR = "error"
	CANCELLED = "cancelled"


class Job:
	"""Manages long-running tasks with agent orchestration.

	Implements a two-method pattern:
	- run(): Public API with error handling, validation, and instrumentation
	- process(): Override in subclasses for custom logic

	A job can:
	- Call agents synchronously (blocking)
	- Call agents asynchronously via queue (non-blocking)
	- Track execution progress and status
	- Store results and logs
	"""

	def __init__(self, name: str, job_dir: Path, context: Optional[AgentContext] = None):
		"""Initialize a job.

		Args:
			name: Job identifier (e.g., 'backtest_cac40_2026')
			job_dir: Directory to store job data (created if doesn't exist)
			context: Optional AgentContext. If None, a new context is created
		"""
		if not name or not isinstance(name, str):
			raise ValueError("Job name must be a non-empty string")
		self.name = name
		self.job_dir = Path(job_dir)
		self.job_dir.mkdir(parents=True, exist_ok=True)

		# Create context
		if context is None:
			context = AgentContext()
		self.context = context

		# Set up logger
		if not self.context.get("logger"):
			self.context.set("logger", AgentLogger(f"job.{name}"))
		self.logger = self.context.get("logger")

		# Job metadata
		self.status = JobStatus.PENDING
		self.created_at = datetime.now()
		self.started_at: Optional[datetime] = None
		self.ended_at: Optional[datetime] = None
		self.results: Dict[str, Any] = {}
		self.agents_executed: List[str] = []
		self.error_message: Optional[str] = None

	def get_config_path(self) -> Path:
		"""Get path to job configuration file."""
		return self.job_dir / "config.yml"

	def get_log_path(self, log_name: str = "job") -> Path:
		"""Get path to job log file.

		Args:
			log_name: Name of the log (default: 'job')

		Returns:
			Path to log file (e.g., job_dir/job.log)
		"""
		return self.job_dir / f"{log_name}.log"

	def start(self) -> None:
		"""Mark job as started."""
		self.status = JobStatus.RUNNING
		self.started_at = datetime.now()
		self.logger.info(f"Job '{self.name}' started")

	def complete(self, results: Optional[Dict[str, Any]] = None) -> None:
		"""Mark job as completed successfully.

		Args:
			results: Optional results dictionary to store
		"""
		self.status = JobStatus.SUCCESS
		self.ended_at = datetime.now()
		if results:
			self.results.update(results)
		self.logger.info(f"Job '{self.name}' completed successfully")

	def fail(self, error_message: str) -> None:
		"""Mark job as failed.

		Args:
			error_message: Error message describing the failure
		"""
		self.status = JobStatus.ERROR
		self.ended_at = datetime.now()
		self.error_message = error_message
		self.logger.error(f"Job '{self.name}' failed: {error_message}")

	def cancel(self) -> None:
		"""Mark job as cancelled."""
		self.status = JobStatus.CANCELLED
		self.ended_at = datetime.now()
		self.logger.warning(f"Job '{self.name}' cancelled")

	def call_agent_sync(self, agent, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Call an agent synchronously (blocking).

		Args:
			agent: Agent instance to execute
			input_data: Optional input data for the agent

		Returns:
			Agent result dictionary with keys:
				- status: "success" or "error"
				- output: Agent output
				- message: Error message if status is "error"
		"""
		try:
			# Execute agent synchronously
			result = agent.run(input_data)

			# Track agent execution
			self.agents_executed.append(agent.name)
			self.logger.info(f"Agent '{agent.name}' executed synchronously")

			return result

		except Exception as e:
			error_msg = f"Error calling agent '{agent.name}': {str(e)}"
			self.logger.error(error_msg)
			return {
				"status": "error",
				"output": {},
				"message": error_msg,
			}

	def call_agent_async(self, agent, queue, input_data: Optional[Dict[str, Any]] = None) -> str:
		"""Call an agent asynchronously via queue.

		Args:
			agent: Agent instance to execute
			queue: Queue to put the task on
			input_data: Optional input data for the agent

		Returns:
			Task ID for tracking the async execution
		"""
		import uuid

		task_id = str(uuid.uuid4())

		# Create task
		task = {
			"task_id": task_id,
			"agent_name": agent.name,
			"agent": agent,
			"input_data": input_data,
			"context": self.context,
		}

		# Queue the task
		queue.put(task)

		# Track agent submission
		self.agents_executed.append(f"{agent.name} (async:{task_id})")
		self.logger.info(f"Agent '{agent.name}' queued asynchronously (task_id: {task_id})")

		return task_id

	def set_result(self, key: str, value: Any) -> None:
		"""Store a result value.

		Args:
			key: Result key
			value: Result value
		"""
		self.results[key] = value
		self.logger.debug(f"Result stored: {key}")

	def get_result(self, key: str, default: Any = None) -> Any:
		"""Retrieve a stored result.

		Args:
			key: Result key
			default: Default value if key not found

		Returns:
			Result value or default
		"""
		return self.results.get(key, default)

	def get_duration_seconds(self) -> Optional[float]:
		"""Get job execution duration in seconds.

		Returns:
			Duration in seconds, or None if not yet started/ended
		"""
		if self.started_at and self.ended_at:
			return (self.ended_at - self.started_at).total_seconds()
		return None

	def to_dict(self) -> Dict[str, Any]:
		"""Convert job to dictionary representation.

		Returns:
			Dictionary with job metadata and results
		"""
		return {
			"name": self.name,
			"status": self.status.value,
			"created_at": self.created_at.isoformat(),
			"started_at": self.started_at.isoformat() if self.started_at else None,
			"ended_at": self.ended_at.isoformat() if self.ended_at else None,
			"duration_seconds": self.get_duration_seconds(),
			"agents_executed": self.agents_executed,
			"results": self.results,
			"error_message": self.error_message,
		}

	def save_metadata(self) -> None:
		"""Save job metadata to JSON file."""
		metadata_file = self.job_dir / "metadata.json"
		with open(metadata_file, "w") as f:
			json.dump(self.to_dict(), f, indent=2, default=str)
		self.logger.debug(f"Job metadata saved to {metadata_file}")

	def load_metadata(self) -> bool:
		"""Load job metadata from JSON file.

		Returns:
			True if metadata was loaded, False if file doesn't exist
		"""
		metadata_file = self.job_dir / "metadata.json"
		if not metadata_file.exists():
			return False

		try:
			with open(metadata_file, "r") as f:
				data = json.load(f)

			self.status = JobStatus(data.get("status", JobStatus.PENDING.value))
			if data.get("created_at"):
				self.created_at = datetime.fromisoformat(data["created_at"])
			if data.get("started_at"):
				self.started_at = datetime.fromisoformat(data["started_at"])
			if data.get("ended_at"):
				self.ended_at = datetime.fromisoformat(data["ended_at"])
			self.agents_executed = data.get("agents_executed", [])
			self.results = data.get("results", {})
			self.error_message = data.get("error_message")

			self.logger.debug(f"Job metadata loaded from {metadata_file}")
			return True

		except Exception as e:
			self.logger.error(f"Error loading metadata: {e}")
			return False

	def process(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process job with custom logic.

		Override this method in subclasses to implement job-specific logic.
		The base implementation returns a success response with empty output.

		Args:
			params: Optional dictionary of job parameters

		Returns:
			Response dictionary with keys:
				- status: "success" or "error"
				- params: The normalized params dictionary
				- output: Job-specific output (empty dict by default)
				- message: Error message (only if status is "error")
		"""
		if params is None:
			params = {}
		return {
			"status": STATUS_SUCCESS,
			"params": params,
			"output": {},
		}

	def run(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Run the job with error handling, validation, and instrumentation.

		This is the public API method. It validates inputs, marks job as running,
		calls process(), handles completion or errors, and persists state.

		Args:
			params: Optional dictionary of job parameters

		Returns:
			Response dictionary with keys:
				- status: "success" or "error"
				- params: The normalized params dictionary
				- output: Job output (empty dict on error)
				- message: Error message only if status is "error"
		"""
		if params is None:
			params = {}
		elif not isinstance(params, dict):
			self.logger.error(f"Invalid params type: {type(params).__name__}, expected dict")
			self.fail(f"Job params must be a dictionary, got {type(params).__name__}")
			self.save_metadata()
			return {
				"status": STATUS_ERROR,
				"params": {},
				"output": {},
				"message": "Job params must be a dictionary",
			}

		start_time = time.time()
		response = None

		try:
			self.start()
			self.logger.debug(f"Job '{self.name}' starting with params: {list(params.keys())}")

			response = self.process(params)

			if response.get("status") == STATUS_SUCCESS:
				self.complete(response.get("output", {}))
				self.logger.debug(f"Job '{self.name}' completed successfully")
			else:
				error_msg = response.get("message", "Process returned error status")
				self.fail(error_msg)
				self.logger.error(f"Job '{self.name}' failed: {error_msg}")

			self.save_metadata()
			return response

		except Exception as e:
			error_msg = str(e)
			self.logger.error(f"Job '{self.name}' exception: {error_msg}")
			self.fail(error_msg)
			self.save_metadata()

			response = {
				"status": STATUS_ERROR,
				"params": params,
				"output": {},
				"message": error_msg,
			}
			return response
