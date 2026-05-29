"""Tests for cron manager."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
import yaml

from src.tools.cron import CronManager, CronJobConfig, CronConfig


class TestCronJobConfig:
	"""Test CronJobConfig class."""

	def test_init_defaults(self):
		"""Test initialization with defaults."""
		config = {
			"name": "test_job",
			"schedule": "0 8 * * *",
			"target": "premarket",
		}
		job = CronJobConfig(config)

		assert job.name == "test_job"
		assert job.schedule == "0 8 * * *"
		assert job.target == "premarket"
		assert job.type == "flow"
		assert job.enabled == False
		assert job.description == ""
		assert job.params == {}

	def test_validate_success(self):
		"""Test validation with valid config."""
		config = {
			"name": "test_job",
			"schedule": "0 8 * * *",
			"type": "flow",
			"target": "premarket",
		}
		job = CronJobConfig(config)
		assert job.validate() == True

	def test_validate_missing_schedule(self):
		"""Test validation with missing schedule."""
		config = {
			"name": "test_job",
			"type": "flow",
			"target": "premarket",
		}
		job = CronJobConfig(config)
		assert job.validate() == False

	def test_validate_invalid_type(self):
		"""Test validation with invalid type."""
		config = {
			"name": "test_job",
			"schedule": "0 8 * * *",
			"type": "invalid",
			"target": "premarket",
		}
		job = CronJobConfig(config)
		assert job.validate() == False

	def test_validate_missing_target(self):
		"""Test validation with missing target."""
		config = {
			"name": "test_job",
			"schedule": "0 8 * * *",
			"type": "flow",
		}
		job = CronJobConfig(config)
		assert job.validate() == False

	def test_to_dict(self):
		"""Test conversion to dictionary."""
		config = {
			"name": "test_job",
			"description": "Test job",
			"enabled": True,
			"schedule": "0 8 * * *",
			"type": "flow",
			"target": "premarket",
			"params": {"strategy": "momentum"},
		}
		job = CronJobConfig(config)
		result = job.to_dict()

		assert result == config


class TestCronConfig:
	"""Test CronConfig class."""

	def test_load_nonexistent(self):
		"""Test loading nonexistent config file."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "nonexistent.yml"
			config = CronConfig(config_path)
			assert config.jobs == []

	def test_load_valid_config(self):
		"""Test loading valid config file."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"

			# Create test config
			data = {
				"jobs": [
					{
						"name": "job1",
						"schedule": "0 8 * * *",
						"type": "flow",
						"target": "premarket",
						"enabled": True,
					}
				]
			}
			with open(config_path, "w") as f:
				yaml.safe_dump(data, f)

			config = CronConfig(config_path)
			assert len(config.jobs) == 1
			assert config.jobs[0].name == "job1"

	def test_get_enabled_jobs(self):
		"""Test getting enabled jobs."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"

			data = {
				"jobs": [
					{
						"name": "job1",
						"schedule": "0 8 * * *",
						"type": "flow",
						"target": "premarket",
						"enabled": True,
					},
					{
						"name": "job2",
						"schedule": "0 9 * * *",
						"type": "flow",
						"target": "analysis",
						"enabled": False,
					},
				]
			}
			with open(config_path, "w") as f:
				yaml.safe_dump(data, f)

			config = CronConfig(config_path)
			enabled = config.get_enabled_jobs()
			assert len(enabled) == 1
			assert enabled[0].name == "job1"

	def test_get_job(self):
		"""Test getting job by name."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"

			data = {
				"jobs": [
					{
						"name": "job1",
						"schedule": "0 8 * * *",
						"type": "flow",
						"target": "premarket",
					}
				]
			}
			with open(config_path, "w") as f:
				yaml.safe_dump(data, f)

			config = CronConfig(config_path)
			job = config.get_job("job1")
			assert job is not None
			assert job.name == "job1"

			job = config.get_job("nonexistent")
			assert job is None


class TestCronManager:
	"""Test CronManager class."""

	def test_init(self):
		"""Test manager initialization."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"
			manager = CronManager(config_path)
			assert manager.config_path == config_path

	def test_list_jobs(self):
		"""Test listing jobs."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"

			data = {
				"jobs": [
					{
						"name": "job1",
						"schedule": "0 8 * * *",
						"type": "flow",
						"target": "premarket",
					}
				]
			}
			with open(config_path, "w") as f:
				yaml.safe_dump(data, f)

			manager = CronManager(config_path)
			jobs = manager.list_jobs()
			assert len(jobs) == 1

	def test_get_job(self):
		"""Test getting job."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"

			data = {
				"jobs": [
					{
						"name": "job1",
						"schedule": "0 8 * * *",
						"type": "flow",
						"target": "premarket",
					}
				]
			}
			with open(config_path, "w") as f:
				yaml.safe_dump(data, f)

			manager = CronManager(config_path)
			job = manager.get_job("job1")
			assert job is not None
			assert job.name == "job1"

	def test_create_job_success(self):
		"""Test creating a job."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"
			manager = CronManager(config_path)

			success, message = manager.create_job(
				name="new_job",
				schedule="0 8 * * *",
				target="premarket",
				job_type="flow",
				description="Test job",
				params={"strategy": "momentum"},
				enabled=True,
			)

			assert success == True
			assert "created successfully" in message
			assert manager.get_job("new_job") is not None
			assert manager.get_job("new_job").enabled == True

	def test_create_job_duplicate(self):
		"""Test creating duplicate job."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"
			manager = CronManager(config_path)

			# Create first job
			manager.create_job(
				name="job1",
				schedule="0 8 * * *",
				target="premarket",
			)

			# Try to create duplicate
			success, message = manager.create_job(
				name="job1",
				schedule="0 9 * * *",
				target="analysis",
			)

			assert success == False
			assert "already exists" in message

	def test_create_job_invalid_schedule(self):
		"""Test creating job with invalid schedule."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"
			manager = CronManager(config_path)

			success, message = manager.create_job(
				name="bad_job",
				schedule="invalid schedule",
				target="premarket",
			)

			assert success == False
			assert "Invalid cron schedule" in message

	def test_create_job_invalid_type(self):
		"""Test creating job with invalid type."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"
			manager = CronManager(config_path)

			success, message = manager.create_job(
				name="bad_job",
				schedule="0 8 * * *",
				target="premarket",
				job_type="invalid",
			)

			assert success == False
			assert "must be 'flow' or 'agent'" in message

	def test_delete_job_success(self):
		"""Test deleting a job."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"
			manager = CronManager(config_path)

			# Create job
			manager.create_job(
				name="job_to_delete",
				schedule="0 8 * * *",
				target="premarket",
			)

			assert manager.get_job("job_to_delete") is not None

			# Delete job
			success, message = manager.delete_job("job_to_delete")
			assert success == True
			assert "deleted successfully" in message
			assert manager.get_job("job_to_delete") is None

	def test_delete_job_not_found(self):
		"""Test deleting nonexistent job."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"
			manager = CronManager(config_path)

			success, message = manager.delete_job("nonexistent")
			assert success == False
			assert "not found" in message

	def test_update_job_success(self):
		"""Test updating a job."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"
			manager = CronManager(config_path)

			# Create job
			manager.create_job(
				name="job_to_update",
				schedule="0 8 * * *",
				target="premarket",
				enabled=False,
			)

			# Update job
			success, message = manager.update_job(
				name="job_to_update",
				schedule="0 9 * * *",
				enabled=True,
			)

			assert success == True
			job = manager.get_job("job_to_update")
			assert job.schedule == "0 9 * * *"
			assert job.enabled == True

	def test_update_job_not_found(self):
		"""Test updating nonexistent job."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"
			manager = CronManager(config_path)

			success, message = manager.update_job(
				name="nonexistent",
				enabled=True,
			)

			assert success == False
			assert "not found" in message

	def test_enable_disable_job(self):
		"""Test enabling and disabling jobs."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"
			manager = CronManager(config_path)

			# Create disabled job
			manager.create_job(
				name="test_job",
				schedule="0 8 * * *",
				target="premarket",
				enabled=False,
			)

			assert manager.get_job("test_job").enabled == False

			# Enable job
			success, message = manager.enable_job("test_job")
			assert success == True
			assert manager.get_job("test_job").enabled == True

			# Disable job
			success, message = manager.disable_job("test_job")
			assert success == True
			assert manager.get_job("test_job").enabled == False

	def test_persistence(self):
		"""Test that changes are persisted to file."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"

			# Create job with manager 1
			manager1 = CronManager(config_path)
			manager1.create_job(
				name="persistent_job",
				schedule="0 8 * * *",
				target="premarket",
			)

			# Load with manager 2
			manager2 = CronManager(config_path)
			job = manager2.get_job("persistent_job")

			assert job is not None
			assert job.name == "persistent_job"
