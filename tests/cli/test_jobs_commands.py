"""Tests for the jobs CLI commands."""

import pytest
import tempfile
import json
from pathlib import Path
from io import StringIO
from unittest.mock import patch

from cli.commands.jobs import JobsCommands
from core.job import JobStatus
from tools.jobs import JobManager


class TestJobsCommandsBasic:
	"""Test basic jobs CLI commands."""

	def test_jobs_commands_init(self):
		"""Test jobs commands initialization."""
		commands = JobsCommands()
		assert commands.manager is not None
		assert commands.manager.jobs_dir is not None

	def test_help_message(self, capsys):
		"""Test help message displays correctly."""
		commands = JobsCommands()
		commands._print_help()
		captured = capsys.readouterr()
		assert "Job Management Commands" in captured.out
		assert "jobs list" in captured.out
		assert "jobs create" in captured.out


class TestJobsCommandsList:
	"""Test jobs list command."""

	def test_list_empty(self, capsys):
		"""Test list with no jobs."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))
			commands = JobsCommands()
			commands.manager = manager

			commands._handle_list("")
			captured = capsys.readouterr()
			assert "No jobs found" in captured.out

	def test_list_with_jobs(self, capsys):
		"""Test list with multiple jobs."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))
			commands = JobsCommands()
			commands.manager = manager

			# Create test jobs
			job1 = manager.create_job("job_1")
			job1.start()
			job1.complete()
			job1.save_metadata()

			job2 = manager.create_job("job_2")
			job2.save_metadata()

			commands._handle_list("")
			captured = capsys.readouterr()
			assert "job_1" in captured.out
			assert "job_2" in captured.out
			assert "success" in captured.out
			assert "pending" in captured.out

	def test_list_by_status(self, capsys):
		"""Test list filtered by status."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))
			commands = JobsCommands()
			commands.manager = manager

			# Create jobs with different statuses
			job1 = manager.create_job("success_job")
			job1.start()
			job1.complete()
			job1.save_metadata()

			job2 = manager.create_job("error_job")
			job2.start()
			job2.fail("Error")
			job2.save_metadata()

			# List successful jobs only
			commands._handle_list("success")
			captured = capsys.readouterr()
			assert "success_job" in captured.out
			assert "error_job" not in captured.out


class TestJobsCommandsSummary:
	"""Test jobs summary command."""

	def test_summary_display(self, capsys):
		"""Test summary displays job counts."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))
			commands = JobsCommands()
			commands.manager = manager

			# Create jobs with different statuses
			job1 = manager.create_job("job_1")
			job1.complete()
			job1.save_metadata()

			job2 = manager.create_job("job_2")
			job2.fail("Error")
			job2.save_metadata()

			job3 = manager.create_job("job_3")
			job3.save_metadata()

			commands._handle_summary()
			captured = capsys.readouterr()
			assert "Job Summary" in captured.out
			assert "success" in captured.out
			assert "error" in captured.out
			assert "pending" in captured.out


class TestJobsCommandsCreate:
	"""Test jobs create command."""

	def test_create_job_basic(self, capsys):
		"""Test creating a basic job."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))
			commands = JobsCommands()
			commands.manager = manager

			commands._handle_create("test_job")
			captured = capsys.readouterr()
			assert "Job created" in captured.out
			assert "test_job" in captured.out

	def test_create_job_duplicate_error(self, capsys):
		"""Test error when creating duplicate job."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))
			commands = JobsCommands()
			commands.manager = manager

			commands._handle_create("test_job")
			commands._handle_create("test_job")
			captured = capsys.readouterr()
			assert "already exists" in captured.out


class TestJobsCommandsInfo:
	"""Test jobs info command."""

	def test_info_display(self, capsys):
		"""Test info displays job details."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))
			commands = JobsCommands()
			commands.manager = manager

			job = manager.create_job("test_job")
			job.start()
			job.set_result("return", 0.15)
			job.complete()
			job.save_metadata()

			commands._handle_info("test_job")
			captured = capsys.readouterr()
			assert "test_job" in captured.out
			assert "success" in captured.out

	def test_info_not_found(self, capsys):
		"""Test info for non-existent job."""
		commands = JobsCommands()
		commands._handle_info("nonexistent")
		captured = capsys.readouterr()
		assert "not found" in captured.out


class TestJobsCommandsLifecycle:
	"""Test job lifecycle commands."""

	def test_start_job(self, capsys):
		"""Test starting a job."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))
			commands = JobsCommands()
			commands.manager = manager

			manager.create_job("test_job")
			commands._handle_start("test_job")
			captured = capsys.readouterr()
			assert "started" in captured.out

	def test_complete_job(self, capsys):
		"""Test completing a job."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))
			commands = JobsCommands()
			commands.manager = manager

			job = manager.create_job("test_job")
			job.start()
			job.save_metadata()

			commands._handle_complete("test_job")
			captured = capsys.readouterr()
			assert "completed" in captured.out

	def test_fail_job(self, capsys):
		"""Test marking job as failed."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))
			commands = JobsCommands()
			commands.manager = manager

			job = manager.create_job("test_job")
			job.start()
			job.save_metadata()

			commands._handle_fail("test_job Test error message")
			captured = capsys.readouterr()
			assert "marked as failed" in captured.out
			assert "Test error message" in captured.out


class TestJobsCommandsDelete:
	"""Test jobs delete command."""

	def test_delete_job(self, capsys):
		"""Test deleting a job."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))
			commands = JobsCommands()
			commands.manager = manager

			manager.create_job("test_job")
			commands._handle_delete("test_job")
			captured = capsys.readouterr()
			assert "deleted" in captured.out

	def test_delete_nonexistent(self, capsys):
		"""Test deleting non-existent job."""
		commands = JobsCommands()
		commands._handle_delete("nonexistent")
		captured = capsys.readouterr()
		assert "not found" in captured.out


class TestJobsCommandsConfig:
	"""Test jobs configuration commands."""

	def test_config_show(self, capsys):
		"""Test showing job configuration."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))
			commands = JobsCommands()
			commands.manager = manager

			config = {"strategy": "momentum", "market": "cac40"}
			manager.save_config("test_job", config)

			commands._handle_config("test_job show")
			captured = capsys.readouterr()
			assert "strategy" in captured.out
			assert "momentum" in captured.out

	def test_config_missing(self, capsys):
		"""Test showing config for job without configuration."""
		commands = JobsCommands()
		commands._handle_config("nonexistent show")
		captured = capsys.readouterr()
		assert "not found" in captured.out


class TestJobsCommandsResults:
	"""Test jobs results commands."""

	def test_results_display(self, capsys):
		"""Test displaying job results."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))
			commands = JobsCommands()
			commands.manager = manager

			job = manager.create_job("test_job")
			job.set_result("return", 0.15)
			job.set_result("sharpe", 1.42)
			job.save_metadata()

			commands._handle_results("test_job")
			captured = capsys.readouterr()
			assert "return" in captured.out
			assert "sharpe" in captured.out

	def test_results_specific_key(self, capsys):
		"""Test displaying specific result."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))
			commands = JobsCommands()
			commands.manager = manager

			job = manager.create_job("test_job")
			job.set_result("return", 0.15)
			job.save_metadata()

			commands._handle_results("test_job return")
			captured = capsys.readouterr()
			assert "0.15" in captured.out or "return" in captured.out


class TestJobsCommandsCleanup:
	"""Test jobs cleanup command."""

	def test_cleanup_old_jobs(self, capsys):
		"""Test cleanup removes old jobs."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))
			commands = JobsCommands()
			commands.manager = manager

			# Create multiple jobs
			for i in range(5):
				job = manager.create_job(f"job_{i:03d}")
				job.complete()
				job.save_metadata()

			commands._handle_cleanup("--keep 2")
			captured = capsys.readouterr()
			assert "Cleaned up" in captured.out or "to clean up" in captured.out


class TestJobsCommandsIntegration:
	"""Integration tests for jobs CLI."""

	def test_full_workflow(self, capsys):
		"""Test complete job workflow via CLI."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = JobManager(Path(tmpdir))
			commands = JobsCommands()
			commands.manager = manager

			# Create
			commands._handle_create("workflow_test")
			assert (manager.jobs_dir / "workflow_test").exists()

			# Start
			commands._handle_start("workflow_test")
			job = manager.get_job("workflow_test")
			assert job.status == JobStatus.RUNNING

			# Complete
			commands._handle_complete("workflow_test")
			job = manager.get_job("workflow_test")
			assert job.status == JobStatus.SUCCESS

			# Info
			commands._handle_info("workflow_test")
			captured = capsys.readouterr()
			assert "workflow_test" in captured.out

			# Delete
			commands._handle_delete("workflow_test")
			assert not (manager.jobs_dir / "workflow_test").exists()
