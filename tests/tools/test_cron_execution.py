"""Tests for cron job execution."""

import pytest
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import yaml
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tools.cron import CronManager, CronJobConfig


class TestCronJobExecution:
	"""Test cases for executing cron jobs."""

	def test_execute_flow_job(self):
		"""Test executing a flow-type job."""
		config = {
			"name": "test_flow_job",
			"schedule": "0 8 * * *",
			"type": "flow",
			"target": "heartbeat",
			"enabled": True,
			"params": {}
		}
		job = CronJobConfig(config)
		assert job.type == "flow"
		assert job.target == "heartbeat"

	def test_execute_agent_job(self):
		"""Test executing an agent-type job."""
		config = {
			"name": "test_agent_job",
			"schedule": "0 12 * * *",
			"type": "agent",
			"target": "premarket",
			"enabled": True,
			"params": {"strategy": "momentum_cac"}
		}
		job = CronJobConfig(config)
		assert job.type == "agent"
		assert job.target == "premarket"
		assert job.params["strategy"] == "momentum_cac"


class TestAlertShaRedCronJob:
	"""Test cases for alert_sha_red cron job."""

	def test_alert_sha_red_config(self):
		"""Test alert_sha_red cron job configuration."""
		config = {
			"name": "alert_sha_red",
			"description": "Alert when SHA turns red",
			"enabled": True,
			"schedule": "*/30 9-18 * * 1-5",
			"type": "flow",
			"target": "http",
			"params": {
				"method": "POST",
				"url": "http://localhost:8000/api/alerts/sha_red/run"
			}
		}
		job = CronJobConfig(config)

		assert job.name == "alert_sha_red"
		assert job.enabled == True
		assert job.schedule == "*/30 9-18 * * 1-5"
		assert job.type == "flow"
		assert job.target == "http"
		assert job.params["method"] == "POST"
		assert "/alerts/sha_red/run" in job.params["url"]

	def test_alert_sha_red_schedule_parsing(self):
		"""Test that alert_sha_red schedule is valid cron format."""
		config = {
			"name": "alert_sha_red",
			"schedule": "*/30 9-18 * * 1-5",
			"type": "flow",
			"target": "http",
		}
		job = CronJobConfig(config)

		# Parse cron schedule
		parts = job.schedule.split()
		assert len(parts) == 5, "Cron schedule should have 5 parts"
		assert parts[0] == "*/30", "Should run every 30 minutes"
		assert "9-18" in parts[1], "Should run 9-18 hours"
		assert "1-5" in parts[4], "Should run Monday-Friday"

	def test_alert_sha_red_http_flow_params(self):
		"""Test that alert_sha_red uses correct HTTP flow parameters."""
		config = {
			"name": "alert_sha_red",
			"schedule": "*/30 9-18 * * 1-5",
			"type": "flow",
			"target": "http",
			"params": {
				"method": "POST",
				"url": "http://localhost:8000/api/alerts/sha_red/run"
			}
		}
		job = CronJobConfig(config)

		assert job.params["method"] == "POST"
		assert "localhost:8000" in job.params["url"]
		assert "api/alerts" in job.params["url"]


class TestCronConfigLoading:
	"""Test cases for loading cron configuration."""

	def test_load_cron_config_with_alert_sha_red(self):
		"""Test loading cron.yml with alert_sha_red job."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"

			data = {
				"jobs": [
					{
						"name": "alert_sha_red",
						"description": "Alert when SHA turns red",
						"enabled": True,
						"schedule": "*/30 9-18 * * 1-5",
						"type": "flow",
						"target": "http",
						"params": {
							"method": "POST",
							"url": "http://localhost:8000/api/alerts/sha_red/run"
						}
					}
				]
			}
			with open(config_path, "w") as f:
				yaml.safe_dump(data, f)

			from tools.cron import CronConfig
			config = CronConfig(config_path)
			assert len(config.jobs) == 1
			assert config.jobs[0].name == "alert_sha_red"

	def test_load_multiple_jobs_including_alert(self):
		"""Test loading config with multiple jobs including alert."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"

			data = {
				"jobs": [
					{
						"name": "heartbeat",
						"schedule": "*/5 * * * *",
						"type": "flow",
						"target": "heartbeat",
						"enabled": True,
						"params": {}
					},
					{
						"name": "alert_sha_red",
						"schedule": "*/30 9-18 * * 1-5",
						"type": "flow",
						"target": "http",
						"enabled": True,
						"params": {
							"method": "POST",
							"url": "http://localhost:8000/api/alerts/sha_red/run"
						}
					},
					{
						"name": "data_sync",
						"schedule": "*/30 9-18 * * 1-5",
						"type": "flow",
						"target": "data_fetch",
						"enabled": True,
						"params": {"universe": "cac40"}
					}
				]
			}
			with open(config_path, "w") as f:
				yaml.safe_dump(data, f)

			from tools.cron import CronConfig
			config = CronConfig(config_path)
			assert len(config.jobs) == 3

			# Find alert_sha_red
			alert_job = config.get_job("alert_sha_red")
			assert alert_job is not None
			assert alert_job.target == "http"


class TestCronJobFiltering:
	"""Test cases for filtering cron jobs."""

	def test_get_enabled_jobs_excludes_disabled(self):
		"""Test that disabled jobs are not in enabled list."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"

			data = {
				"jobs": [
					{
						"name": "job1",
						"schedule": "0 8 * * *",
						"type": "flow",
						"target": "premarket",
						"enabled": True
					},
					{
						"name": "alert_sha_red",
						"schedule": "*/30 9-18 * * 1-5",
						"type": "flow",
						"target": "http",
						"enabled": False
					}
				]
			}
			with open(config_path, "w") as f:
				yaml.safe_dump(data, f)

			from tools.cron import CronConfig
			config = CronConfig(config_path)
			enabled = config.get_enabled_jobs()

			assert len(enabled) == 1
			assert enabled[0].name == "job1"
			# alert_sha_red should not be in enabled jobs if disabled=False

	def test_get_flow_jobs(self):
		"""Test filtering for flow-type jobs."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"

			data = {
				"jobs": [
					{
						"name": "flow_job1",
						"schedule": "0 8 * * *",
						"type": "flow",
						"target": "premarket",
						"enabled": True
					},
					{
						"name": "agent_job1",
						"schedule": "0 9 * * *",
						"type": "agent",
						"target": "strategy",
						"enabled": True
					},
					{
						"name": "alert_sha_red",
						"schedule": "*/30 9-18 * * 1-5",
						"type": "flow",
						"target": "http",
						"enabled": True
					}
				]
			}
			with open(config_path, "w") as f:
				yaml.safe_dump(data, f)

			from tools.cron import CronConfig
			config = CronConfig(config_path)

			flow_jobs = [j for j in config.jobs if j.type == "flow"]
			assert len(flow_jobs) == 2
			assert "alert_sha_red" in [j.name for j in flow_jobs]


class TestCronJobValidation:
	"""Test cases for validating cron job configuration."""

	def test_validate_alert_sha_red_job(self):
		"""Test validation of alert_sha_red configuration."""
		config = {
			"name": "alert_sha_red",
			"schedule": "*/30 9-18 * * 1-5",
			"type": "flow",
			"target": "http",
			"params": {
				"method": "POST",
				"url": "http://localhost:8000/api/alerts/sha_red/run"
			}
		}
		job = CronJobConfig(config)
		assert job.validate() == True

	def test_missing_schedule_fails_validation(self):
		"""Test validation fails without schedule."""
		config = {
			"name": "bad_job",
			"type": "flow",
			"target": "http"
		}
		job = CronJobConfig(config)
		assert job.validate() == False

	def test_missing_target_fails_validation(self):
		"""Test validation fails without target."""
		config = {
			"name": "bad_job",
			"schedule": "*/30 * * * *",
			"type": "flow"
		}
		job = CronJobConfig(config)
		assert job.validate() == False


class TestCronScheduleParsing:
	"""Test cases for parsing cron schedules."""

	def test_parse_every_30_minutes(self):
		"""Test parsing '*/30' minutes syntax."""
		schedule = "*/30 * * * *"
		parts = schedule.split()
		assert parts[0] == "*/30"

	def test_parse_business_hours(self):
		"""Test parsing business hours range."""
		schedule = "0 9-18 * * 1-5"
		parts = schedule.split()
		assert "9-18" in parts[1]
		assert "1-5" in parts[4]

	def test_parse_market_hours_schedule(self):
		"""Test parsing market hours schedule (9-18, Mon-Fri)."""
		schedule = "*/30 9-18 * * 1-5"
		parts = schedule.split()
		assert len(parts) == 5
		assert parts[0] == "*/30"  # Every 30 minutes
		assert parts[1] == "9-18"  # 9 AM to 6 PM
		assert parts[2] == "*"     # Every day
		assert parts[3] == "*"     # Every month
		assert parts[4] == "1-5"   # Monday to Friday

	def test_parse_extended_market_hours(self):
		"""Test parsing extended market hours (9 AM to midnight)."""
		schedule = "*/30 9-23 * * 1-5"
		parts = schedule.split()
		assert "9-23" in parts[1]


class TestCronJobPersistence:
	"""Test cases for persisting cron jobs."""

	def test_create_and_persist_alert_job(self):
		"""Test creating and persisting alert job."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"
			manager = CronManager(config_path)

			success, message = manager.create_job(
				name="alert_sha_red",
				schedule="*/30 9-18 * * 1-5",
				target="http",
				job_type="flow",
				description="Alert when SHA turns red",
				params={
					"method": "POST",
					"url": "http://localhost:8000/api/alerts/sha_red/run"
				},
				enabled=True
			)

			assert success == True
			assert config_path.exists()

			# Reload and verify
			manager2 = CronManager(config_path)
			job = manager2.get_job("alert_sha_red")
			assert job is not None
			assert job.target == "http"
			assert job.params["method"] == "POST"

	def test_update_alert_job_schedule(self):
		"""Test updating alert job schedule."""
		with TemporaryDirectory() as tmpdir:
			config_path = Path(tmpdir) / "cron.yml"
			manager = CronManager(config_path)

			# Create job
			manager.create_job(
				name="alert_sha_red",
				schedule="*/30 9-18 * * 1-5",
				target="http",
				job_type="flow"
			)

			# Update schedule
			success, message = manager.update_job(
				name="alert_sha_red",
				schedule="*/15 9-18 * * 1-5"
			)

			assert success == True
			job = manager.get_job("alert_sha_red")
			assert job.schedule == "*/15 9-18 * * 1-5"


class TestCronJobComparison:
	"""Test cases comparing different cron configurations."""

	def test_compare_http_vs_shell_exec(self):
		"""Compare HTTP flow vs shell_exec for alert."""
		# HTTP flow approach
		http_config = {
			"name": "alert_sha_red_http",
			"schedule": "*/30 9-18 * * 1-5",
			"type": "flow",
			"target": "http",
			"params": {
				"method": "POST",
				"url": "http://localhost:8000/api/alerts/sha_red/run"
			}
		}

		# Shell exec approach (old)
		shell_config = {
			"name": "alert_sha_red_shell",
			"schedule": "*/30 9-18 * * 1-5",
			"type": "flow",
			"target": "shell_exec",
			"params": {
				"command": "curl -X POST http://localhost:8000/api/alerts/sha_red/run"
			}
		}

		http_job = CronJobConfig(http_config)
		shell_job = CronJobConfig(shell_config)

		# Both should be valid
		assert http_job.validate() == True
		assert shell_job.validate() == True

		# HTTP approach has cleaner params
		assert "method" in http_job.params
		assert "url" in http_job.params
