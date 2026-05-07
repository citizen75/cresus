"""Cron job configuration loader."""

from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml
from loguru import logger
from utils.env import get_config_root


class CronJobConfig:
	"""Configuration for a single cron job."""

	def __init__(self, config: Dict[str, Any]):
		"""Initialize cron job config.

		Args:
			config: Job configuration dict with keys: name, description, enabled,
					schedule, type, target, params
		"""
		self.name = config.get("name", "unnamed")
		self.description = config.get("description", "")
		self.enabled = config.get("enabled", False)
		self.schedule = config.get("schedule", "")
		self.type = config.get("type", "flow")  # 'flow' or 'agent'
		self.target = config.get("target", "")
		self.params = config.get("params", {})

	def validate(self) -> bool:
		"""Validate job configuration.

		Returns:
			True if valid, False otherwise
		"""
		if not self.schedule:
			logger.warning(f"Job '{self.name}': missing schedule")
			return False

		if self.type not in ("flow", "agent"):
			logger.warning(f"Job '{self.name}': invalid type '{self.type}', must be 'flow' or 'agent'")
			return False

		if not self.target:
			logger.warning(f"Job '{self.name}': missing target")
			return False

		return True


class CronConfig:
	"""Load and manage cron job configurations."""

	def __init__(self, config_path: Optional[Path] = None):
		"""Initialize cron config loader.

		Args:
			config_path: Path to cron.yml config file. Defaults to ~/.cresus/config/cron.yml
		"""
		if config_path is None:
			config_path = get_config_root() / "cron.yml"

		self.config_path = config_path
		self.jobs: List[CronJobConfig] = []
		self._load()

	def _load(self) -> None:
		"""Load cron configuration from file."""
		if not self.config_path.exists():
			logger.warning(f"Cron config file not found: {self.config_path}")
			return

		try:
			content = self.config_path.read_text()
			config = yaml.safe_load(content) or {}

			job_configs = config.get("jobs", [])
			if not isinstance(job_configs, list):
				logger.warning("Invalid cron config: 'jobs' must be a list")
				return

			for job_config in job_configs:
				job = CronJobConfig(job_config)
				if job.validate():
					self.jobs.append(job)
				else:
					logger.warning(f"Skipping invalid cron job: {job.name}")

			logger.info(f"Loaded {len(self.jobs)} cron jobs from {self.config_path}")

		except Exception as e:
			logger.error(f"Failed to load cron config: {e}")

	def get_enabled_jobs(self) -> List[CronJobConfig]:
		"""Get enabled cron jobs.

		Returns:
			List of enabled job configurations
		"""
		return [job for job in self.jobs if job.enabled]
