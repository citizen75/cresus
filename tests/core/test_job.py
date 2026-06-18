"""Tests for the Job class."""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime

from core.job import Job, JobStatus
from core.agent import Agent
from core.context import AgentContext


class TestJobInitialization:
	"""Test job initialization and basic properties."""

	def test_job_creation(self):
		"""Test creating a job."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job = Job("test_job", Path(tmpdir))

			assert job.name == "test_job"
			assert job.status == JobStatus.PENDING
			assert job.created_at is not None
			assert job.results == {}
			assert job.agents_executed == []

	def test_job_directory_creation(self):
		"""Test that job directory is created."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "test_job"
			job = Job("test_job", job_dir)

			assert job_dir.exists()
			assert job_dir.is_dir()

	def test_job_with_context(self):
		"""Test job with custom context."""
		with tempfile.TemporaryDirectory() as tmpdir:
			context = AgentContext()
			context.set("custom_key", "custom_value")

			job = Job("test_job", Path(tmpdir), context)

			assert job.context.get("custom_key") == "custom_value"


class TestJobLifecycle:
	"""Test job status transitions."""

	def test_start_job(self):
		"""Test starting a job."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job = Job("test_job", Path(tmpdir))
			job.start()

			assert job.status == JobStatus.RUNNING
			assert job.started_at is not None

	def test_complete_job(self):
		"""Test completing a job."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job = Job("test_job", Path(tmpdir))
			job.start()
			job.complete({"result": "success"})

			assert job.status == JobStatus.SUCCESS
			assert job.ended_at is not None
			assert job.results == {"result": "success"}

	def test_fail_job(self):
		"""Test failing a job."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job = Job("test_job", Path(tmpdir))
			job.start()
			job.fail("Test error message")

			assert job.status == JobStatus.ERROR
			assert job.error_message == "Test error message"
			assert job.ended_at is not None

	def test_cancel_job(self):
		"""Test cancelling a job."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job = Job("test_job", Path(tmpdir))
			job.start()
			job.cancel()

			assert job.status == JobStatus.CANCELLED
			assert job.ended_at is not None


class TestJobResults:
	"""Test job result management."""

	def test_set_and_get_result(self):
		"""Test storing and retrieving results."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job = Job("test_job", Path(tmpdir))

			job.set_result("key1", "value1")
			job.set_result("key2", {"nested": "value"})

			assert job.get_result("key1") == "value1"
			assert job.get_result("key2") == {"nested": "value"}

	def test_get_result_default(self):
		"""Test getting result with default value."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job = Job("test_job", Path(tmpdir))

			value = job.get_result("nonexistent", "default")
			assert value == "default"

	def test_multiple_results(self):
		"""Test storing multiple results."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job = Job("test_job", Path(tmpdir))

			results = {"a": 1, "b": 2, "c": 3}
			for key, value in results.items():
				job.set_result(key, value)

			assert job.results == results


class TestJobAgentExecution:
	"""Test synchronous and asynchronous agent execution."""

	def test_call_agent_sync(self):
		"""Test synchronous agent call."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job = Job("test_job", Path(tmpdir))

			class TestAgent(Agent):
				def process(self, input_data=None):
					return {
						"status": "success",
						"output": {"result": 42},
					}

			agent = TestAgent("TestAgent", job.context)
			result = job.call_agent_sync(agent, {})

			assert result["status"] == "success"
			assert result["output"]["result"] == 42
			assert "TestAgent" in job.agents_executed

	def test_call_agent_sync_error(self):
		"""Test synchronous agent call with error."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job = Job("test_job", Path(tmpdir))

			class FailingAgent(Agent):
				def process(self, input_data=None):
					raise ValueError("Agent error")

			agent = FailingAgent("FailingAgent", job.context)
			result = job.call_agent_sync(agent, {})

			assert result["status"] == "error"
			assert "Agent error" in result["message"]

	def test_call_agent_async(self):
		"""Test asynchronous agent call."""
		from queue import Queue

		with tempfile.TemporaryDirectory() as tmpdir:
			job = Job("test_job", Path(tmpdir))
			queue = Queue()

			class AsyncAgent(Agent):
				def process(self, input_data=None):
					return {"status": "success", "output": {}}

			agent = AsyncAgent("AsyncAgent", job.context)
			task_id = job.call_agent_async(agent, queue, {})

			assert task_id is not None
			assert not queue.empty()
			assert "AsyncAgent" in " ".join(job.agents_executed)

			# Verify task structure
			task = queue.get()
			assert task["task_id"] == task_id
			assert task["agent_name"] == "AsyncAgent"
			assert task["agent"] == agent


class TestJobDuration:
	"""Test job duration tracking."""

	def test_duration_calculation(self):
		"""Test calculating job duration."""
		import time

		with tempfile.TemporaryDirectory() as tmpdir:
			job = Job("test_job", Path(tmpdir))
			job.start()
			time.sleep(0.1)
			job.complete()

			duration = job.get_duration_seconds()
			assert duration is not None
			assert duration >= 0.1

	def test_duration_not_started(self):
		"""Test duration when job not started."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job = Job("test_job", Path(tmpdir))

			duration = job.get_duration_seconds()
			assert duration is None


class TestJobPersistence:
	"""Test saving and loading job metadata."""

	def test_save_metadata(self):
		"""Test saving job metadata to JSON."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "test_job"
			job = Job("test_job", job_dir)
			job.start()
			job.set_result("key", "value")
			job.complete()
			job.save_metadata()

			metadata_file = job_dir / "metadata.json"
			assert metadata_file.exists()

			with open(metadata_file) as f:
				data = json.load(f)

			assert data["name"] == "test_job"
			assert data["status"] == "success"
			assert data["results"]["key"] == "value"

	def test_load_metadata(self):
		"""Test loading job metadata from JSON."""
		with tempfile.TemporaryDirectory() as tmpdir:
			# Create and save job
			job1 = Job("test_job", Path(tmpdir) / "test_job")
			job1.start()
			job1.set_result("key", "value")
			job1.complete()
			job1.save_metadata()

			# Load job
			job2 = Job("test_job", Path(tmpdir) / "test_job")
			loaded = job2.load_metadata()

			assert loaded is True
			assert job2.status == JobStatus.SUCCESS
			assert job2.get_result("key") == "value"

	def test_load_metadata_not_found(self):
		"""Test loading metadata when file doesn't exist."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job = Job("test_job", Path(tmpdir))

			loaded = job.load_metadata()
			assert loaded is False


class TestJobPaths:
	"""Test job path utilities."""

	def test_get_config_path(self):
		"""Test getting config file path."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job = Job("test_job", Path(tmpdir) / "test_job")

			config_path = job.get_config_path()
			assert config_path.name == "config.yml"

	def test_get_log_path(self):
		"""Test getting log file path."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job = Job("test_job", Path(tmpdir) / "test_job")

			log_path = job.get_log_path()
			assert log_path.name == "job.log"

			custom_log_path = job.get_log_path("custom")
			assert custom_log_path.name == "custom.log"


class TestJobDictRepresentation:
	"""Test job dictionary representation."""

	def test_to_dict(self):
		"""Test converting job to dictionary."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job = Job("test_job", Path(tmpdir))
			job.start()
			job.set_result("key", "value")
			job.complete()

			job_dict = job.to_dict()

			assert job_dict["name"] == "test_job"
			assert job_dict["status"] == "success"
			assert job_dict["results"] == {"key": "value"}
			assert "created_at" in job_dict
			assert "started_at" in job_dict
			assert "ended_at" in job_dict
