"""Tests for the JobManager class."""

import pytest
import tempfile
import yaml
from pathlib import Path

from core.job import JobStatus
from tools.jobs import JobManager


class TestJobManagerInitialization:
	"""Test job manager initialization."""

	def test_manager_creation(self):
		"""Test creating a job manager."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			assert manager.db_root == Path(tmpdir)
			assert manager.jobs_dir == Path(tmpdir) / "jobs"
			assert manager.jobs_dir.exists()

	def test_manager_default_db_root(self):
		"""Test manager with default db_root."""
		manager = JobManager()

		assert manager.db_root is not None
		assert manager.jobs_dir is not None


class TestJobCreation:
	"""Test job creation via manager."""

	def test_create_job(self):
		"""Test creating a job."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			job = manager.create_job("test_job")

			assert job.name == "test_job"
			assert (manager.jobs_dir / "test_job").exists()

	def test_create_job_with_config(self):
		"""Test creating a job with configuration."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			config = {"strategy": "momentum", "market": "cac40"}
			job = manager.create_job("test_job", config)

			config_file = manager.jobs_dir / "test_job" / "config.yml"
			assert config_file.exists()

	def test_create_job_duplicate_error(self):
		"""Test error when creating duplicate job."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			manager.create_job("test_job")

			with pytest.raises(ValueError, match="already exists"):
				manager.create_job("test_job")


class TestJobRetrieval:
	"""Test retrieving jobs."""

	def test_get_job(self):
		"""Test getting an existing job."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			created_job = manager.create_job("test_job")
			created_job.start()
			created_job.complete()
			created_job.save_metadata()

			retrieved_job = manager.get_job("test_job")

			assert retrieved_job is not None
			assert retrieved_job.name == "test_job"
			assert retrieved_job.status == JobStatus.SUCCESS

	def test_get_job_not_found(self):
		"""Test getting non-existent job."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			job = manager.get_job("nonexistent")

			assert job is None


class TestJobDeletion:
	"""Test job deletion."""

	def test_delete_job(self):
		"""Test deleting a job."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			job = manager.create_job("test_job")
			job_dir = manager.get_job_dir("test_job")

			assert job_dir.exists()

			deleted = manager.delete_job("test_job")

			assert deleted is True
			assert not job_dir.exists()

	def test_delete_job_not_found(self):
		"""Test deleting non-existent job."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			deleted = manager.delete_job("nonexistent")

			assert deleted is False


class TestJobListing:
	"""Test listing jobs."""

	def test_list_all_jobs(self):
		"""Test listing all jobs."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			for i in range(3):
				manager.create_job(f"job_{i}")

			jobs = manager.list_jobs()

			assert len(jobs) == 3
			assert "job_0" in jobs
			assert "job_1" in jobs
			assert "job_2" in jobs

	def test_list_jobs_empty(self):
		"""Test listing jobs when none exist."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			jobs = manager.list_jobs()

			assert jobs == []

	def test_list_jobs_by_status(self):
		"""Test listing jobs filtered by status."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			# Create jobs with different statuses
			job1 = manager.create_job("success_job")
			job1.start()
			job1.complete()
			job1.save_metadata()

			job2 = manager.create_job("error_job")
			job2.start()
			job2.fail("Error")
			job2.save_metadata()

			job3 = manager.create_job("pending_job")

			# List by status
			success_jobs = manager.list_jobs(JobStatus.SUCCESS)
			assert "success_job" in success_jobs
			assert "error_job" not in success_jobs

			error_jobs = manager.list_jobs(JobStatus.ERROR)
			assert "error_job" in error_jobs
			assert "success_job" not in error_jobs


class TestJobsSummary:
	"""Test job summary."""

	def test_get_jobs_summary(self):
		"""Test getting job summary."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			# Create jobs with different statuses
			job1 = manager.create_job("job1")
			job1.start()
			job1.complete()
			job1.save_metadata()

			job2 = manager.create_job("job2")
			job2.start()
			job2.fail("Error")
			job2.save_metadata()

			manager.create_job("job3")  # Pending

			summary = manager.get_jobs_summary()

			assert summary["total"] == 3
			assert summary["success"] == 1
			assert summary["error"] == 1
			assert summary["pending"] == 1


class TestJobConfiguration:
	"""Test job configuration management."""

	def test_save_config(self):
		"""Test saving job configuration."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			config = {
				"strategy": "momentum",
				"market": "cac40",
				"agents": ["DataAgent", "CalculatorAgent"],
			}

			config_path = manager.save_config("test_job", config)

			assert config_path.exists()
			assert config_path.suffix == ".yml"

	def test_load_config(self):
		"""Test loading job configuration."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			config = {
				"strategy": "momentum",
				"market": "cac40",
			}

			manager.save_config("test_job", config)
			loaded_config = manager.load_config("test_job")

			assert loaded_config == config

	def test_load_config_not_found(self):
		"""Test loading non-existent configuration."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			config = manager.load_config("nonexistent")

			assert config is None


class TestJobDirectories:
	"""Test job directory utilities."""

	def test_get_job_dir(self):
		"""Test getting job directory."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			manager.create_job("test_job")
			job_dir = manager.get_job_dir("test_job")

			assert job_dir.exists()
			assert job_dir.name == "test_job"

	def test_get_job_log_file(self):
		"""Test getting job log file path."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			log_file = manager.get_job_log_file("test_job")

			assert log_file.name == "job.log"

			custom_log = manager.get_job_log_file("test_job", "custom")
			assert custom_log.name == "custom.log"


class TestJobCleanup:
	"""Test job cleanup operations."""

	def test_cleanup_old_jobs(self):
		"""Test cleaning up old jobs."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			# Create 5 completed jobs
			for i in range(5):
				job = manager.create_job(f"job_{i:03d}")
				job.start()
				job.complete()
				job.save_metadata()

			# Keep only 2, should delete 3
			deleted = manager.cleanup_old_jobs(keep_count=2)

			assert deleted == 3

			remaining_jobs = manager.list_jobs()
			assert len(remaining_jobs) == 2

	def test_cleanup_with_status_filter(self):
		"""Test cleanup with status filter."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			# Create successful and failed jobs
			for i in range(3):
				job = manager.create_job(f"success_{i}")
				job.start()
				job.complete()
				job.save_metadata()

			for i in range(2):
				job = manager.create_job(f"error_{i}")
				job.start()
				job.fail("Error")
				job.save_metadata()

			# Delete old successful jobs, keep 1
			deleted = manager.cleanup_old_jobs(keep_count=1, status_filter=JobStatus.SUCCESS)

			assert deleted == 2

			remaining_jobs = manager.list_jobs()
			assert len(remaining_jobs) == 3  # 1 success + 2 errors


class TestJobIntegration:
	"""Integration tests for job management."""

	def test_full_job_lifecycle(self):
		"""Test complete job lifecycle."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			# Create job with config
			config = {"strategy": "momentum"}
			job = manager.create_job("backtest", config)

			# Verify config saved
			loaded_config = manager.load_config("backtest")
			assert loaded_config == config

			# Execute job
			job.start()
			job.set_result("return", 0.15)
			job.complete()
			job.save_metadata()

			# Retrieve and verify
			retrieved_job = manager.get_job("backtest")
			assert retrieved_job.status == JobStatus.SUCCESS
			assert retrieved_job.get_result("return") == 0.15

			# Cleanup
			deleted = manager.delete_job("backtest")
			assert deleted is True
			assert manager.get_job("backtest") is None

	def test_multiple_jobs_management(self):
		"""Test managing multiple jobs."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))

			# Create multiple jobs
			job_names = []
			for i in range(5):
				job = manager.create_job(f"job_{i}")
				job.start()
				if i % 2 == 0:
					job.complete()
				else:
					job.fail("Test error")
				job.save_metadata()
				job_names.append(job.name)

			# Verify summary
			summary = manager.get_jobs_summary()
			assert summary["total"] == 5
			assert summary["success"] == 3
			assert summary["error"] == 2

			# List by status
			successful = manager.list_jobs(JobStatus.SUCCESS)
			failed = manager.list_jobs(JobStatus.ERROR)
			assert len(successful) == 3
			assert len(failed) == 2

			# Cleanup all
			for job_name in job_names:
				manager.delete_job(job_name)

			assert manager.list_jobs() == []
