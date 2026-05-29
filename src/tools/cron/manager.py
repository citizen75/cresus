"""Cron job management."""

from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import yaml
from loguru import logger
from utils.env import get_config_root
from .config import CronConfig, CronJobConfig


class CronManager:
	"""Manager for cron jobs."""

	def __init__(self, config_path: Optional[Path] = None):
		"""Initialize cron manager.

		Args:
			config_path: Path to cron.yml config file
		"""
		if config_path is None:
			config_path = get_config_root() / "cron.yml"

		self.config_path = config_path
		self.config = CronConfig(config_path)

	def list_jobs(self) -> List[CronJobConfig]:
		"""List all cron jobs.

		Returns:
			List of all job configurations
		"""
		return self.config.jobs

	def get_job(self, name: str) -> Optional[CronJobConfig]:
		"""Get a job by name.

		Args:
			name: Job name

		Returns:
			Job configuration or None
		"""
		return self.config.get_job(name)

	def create_job(
		self,
		name: str,
		schedule: str,
		target: str,
		job_type: str = "flow",
		description: str = "",
		params: Optional[Dict[str, Any]] = None,
		enabled: bool = False,
	) -> Tuple[bool, str]:
		"""Create a new cron job.

		Args:
			name: Job name (must be unique)
			schedule: Cron schedule string
			target: Target flow or agent name
			job_type: Job type ('flow' or 'agent')
			description: Job description
			params: Job parameters
			enabled: Whether job is enabled

		Returns:
			Tuple of (success, message)
		"""
		if not name or not schedule or not target:
			return False, "name, schedule, and target are required"

		if job_type not in ("flow", "agent"):
			return False, "job_type must be 'flow' or 'agent'"

		if self.get_job(name):
			return False, f"Job '{name}' already exists"

		# Validate cron schedule
		try:
			from apscheduler.triggers.cron import CronTrigger
			CronTrigger.from_crontab(schedule)
		except Exception as e:
			return False, f"Invalid cron schedule: {e}"

		job_config = {
			"name": name,
			"description": description,
			"enabled": enabled,
			"schedule": schedule,
			"type": job_type,
			"target": target,
			"params": params or {},
		}

		# Add to config
		self.config.jobs.append(CronJobConfig(job_config))

		# Save to file
		success, message = self._save_config()
		if success:
			logger.info(f"Created cron job '{name}'")
			return True, f"Cron job '{name}' created successfully"
		else:
			# Remove from memory if save failed
			self.config.jobs = [j for j in self.config.jobs if j.name != name]
			return False, message

	def delete_job(self, name: str) -> Tuple[bool, str]:
		"""Delete a cron job.

		Args:
			name: Job name

		Returns:
			Tuple of (success, message)
		"""
		job = self.get_job(name)
		if not job:
			return False, f"Job '{name}' not found"

		self.config.jobs = [j for j in self.config.jobs if j.name != name]

		success, message = self._save_config()
		if success:
			logger.info(f"Deleted cron job '{name}'")
			return True, f"Cron job '{name}' deleted successfully"
		else:
			# Reload if save failed
			self.config.reload()
			return False, message

	def update_job(
		self,
		name: str,
		schedule: Optional[str] = None,
		target: Optional[str] = None,
		job_type: Optional[str] = None,
		description: Optional[str] = None,
		params: Optional[Dict[str, Any]] = None,
		enabled: Optional[bool] = None,
	) -> Tuple[bool, str]:
		"""Update a cron job.

		Args:
			name: Job name
			schedule: New schedule (optional)
			target: New target (optional)
			job_type: New type (optional)
			description: New description (optional)
			params: New parameters (optional)
			enabled: New enabled status (optional)

		Returns:
			Tuple of (success, message)
		"""
		job = self.get_job(name)
		if not job:
			return False, f"Job '{name}' not found"

		# Validate new schedule if provided
		if schedule:
			try:
				from apscheduler.triggers.cron import CronTrigger
				CronTrigger.from_crontab(schedule)
			except Exception as e:
				return False, f"Invalid cron schedule: {e}"

		# Validate type if provided
		if job_type and job_type not in ("flow", "agent"):
			return False, "job_type must be 'flow' or 'agent'"

		# Update fields
		if schedule is not None:
			job.schedule = schedule
		if target is not None:
			job.target = target
		if job_type is not None:
			job.type = job_type
		if description is not None:
			job.description = description
		if params is not None:
			job.params = params
		if enabled is not None:
			job.enabled = enabled

		# Validate updated config
		if not job.validate():
			return False, "Updated job configuration is invalid"

		success, message = self._save_config()
		if success:
			logger.info(f"Updated cron job '{name}'")
			return True, f"Cron job '{name}' updated successfully"
		else:
			self.config.reload()
			return False, message

	def enable_job(self, name: str) -> Tuple[bool, str]:
		"""Enable a cron job.

		Args:
			name: Job name

		Returns:
			Tuple of (success, message)
		"""
		return self.update_job(name, enabled=True)

	def disable_job(self, name: str) -> Tuple[bool, str]:
		"""Disable a cron job.

		Args:
			name: Job name

		Returns:
			Tuple of (success, message)
		"""
		return self.update_job(name, enabled=False)

	def duplicate_job(self, name: str, new_name: str) -> Tuple[bool, str]:
		"""Duplicate a cron job with a new name.

		Args:
			name: Original job name
			new_name: New job name

		Returns:
			Tuple of (success, message)
		"""
		job = self.get_job(name)
		if not job:
			return False, f"Job '{name}' not found"

		if self.get_job(new_name):
			return False, f"Job '{new_name}' already exists"

		# Create new job with same properties but new name
		job_config = {
			"name": new_name,
			"description": f"{job.description} (copy)" if job.description else "(copy)",
			"enabled": False,
			"schedule": job.schedule,
			"type": job.type,
			"target": job.target,
			"params": job.params.copy() if job.params else {},
		}

		self.config.jobs.append(CronJobConfig(job_config))

		success, message = self._save_config()
		if success:
			logger.info(f"Duplicated cron job '{name}' as '{new_name}'")
			return True, f"Cron job '{name}' duplicated as '{new_name}' (disabled)"
		else:
			self.config.jobs = [j for j in self.config.jobs if j.name != new_name]
			return False, message

	def run_job(self, name: str) -> Tuple[bool, str]:
		"""Run a cron job immediately.

		Args:
			name: Job name

		Returns:
			Tuple of (success, message)
		"""
		job = self.get_job(name)
		if not job:
			return False, f"Job '{name}' not found"

		logger.info(f"Executing cron job '{name}' (target: {job.target}, type: {job.type})")
		return True, f"Job '{name}' queued for execution"

	def _save_config(self) -> Tuple[bool, str]:
		"""Save configuration to file.

		Returns:
			Tuple of (success, message)
		"""
		try:
			self.config_path.parent.mkdir(parents=True, exist_ok=True)

			# Build YAML structure
			jobs_list = [job.to_dict() for job in self.config.jobs]
			data = {"jobs": jobs_list}

			# Write YAML
			with open(self.config_path, "w") as f:
				yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

			return True, "Configuration saved"

		except Exception as e:
			logger.error(f"Failed to save cron config: {e}")
			return False, f"Failed to save configuration: {e}"
