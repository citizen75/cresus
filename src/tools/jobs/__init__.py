"""Job management system for long-running tasks."""

import shutil
from pathlib import Path
from typing import Optional, Dict, List, Any
import yaml

from core.job import Job, JobStatus
from utils.env import get_db_root


class JobManager:
	"""Manages job lifecycle, storage, and configuration.

	Jobs are organized in get_db_root()/jobs/<job_name>/:
	- config.yml: Job configuration
	- metadata.json: Job metadata (created by Job class)
	- <log_name>.log: Job logs
	"""

	def __init__(self, db_root: Optional[Path] = None):
		"""Initialize job manager.

		Args:
			db_root: Root database directory (default: get_db_root())
		"""
		self.db_root = db_root or get_db_root()
		self.jobs_dir = self.db_root / "jobs"
		self.jobs_dir.mkdir(parents=True, exist_ok=True)

	def create_job(self, name: str, config: Optional[Dict[str, Any]] = None) -> Job:
		"""Create and initialize a new job.

		Uses init/templates/jobs.yml as default template if no config provided.

		Args:
			name: Job identifier (must be unique)
			config: Optional job configuration dictionary (uses template if None)

		Returns:
			Job instance

		Raises:
			ValueError: If job already exists
		"""
		job_dir = self.jobs_dir / name
		if job_dir.exists():
			raise ValueError(f"Job '{name}' already exists")

		job_dir.mkdir(parents=True, exist_ok=True)

		# Load default template if no config provided
		if config is None:
			config = self._load_default_template()

		# Save configuration
		if config:
			self.save_config(name, config)

		return Job(name, job_dir)

	def _load_default_template(self) -> Dict[str, Any]:
		"""Load default job configuration template.

		Returns:
			Default configuration dictionary from init/templates/jobs.yml
		"""
		# Try to find the template file
		template_path = self.db_root.parent / "init" / "templates" / "jobs.yml"

		if template_path.exists():
			try:
				with open(template_path) as f:
					return yaml.safe_load(f) or {}
			except Exception as e:
				# Return empty dict if template can't be loaded
				return {}

		# Fallback: return minimal default template
		return {
			"description": "Job description",
			"parameters": {
				"initial_capital": 100000
			},
			"agents": []
		}

	def get_job(self, name: str) -> Optional[Job]:
		"""Load an existing job.

		Args:
			name: Job identifier

		Returns:
			Job instance if found, None otherwise
		"""
		job_dir = self.jobs_dir / name
		if not job_dir.exists():
			return None

		job = Job(name, job_dir)
		job.load_metadata()
		return job

	def delete_job(self, name: str) -> bool:
		"""Delete a job and all its data.

		Args:
			name: Job identifier

		Returns:
			True if job was deleted, False if job doesn't exist
		"""
		job_dir = self.jobs_dir / name
		if not job_dir.exists():
			return False

		try:
			shutil.rmtree(job_dir)
			return True
		except Exception as e:
			raise RuntimeError(f"Error deleting job '{name}': {e}")

	def list_jobs(self, status: Optional[JobStatus] = None) -> List[str]:
		"""List all job names, optionally filtered by status.

		Args:
			status: Optional JobStatus to filter by

		Returns:
			List of job names
		"""
		if not self.jobs_dir.exists():
			return []

		jobs = []
		for job_dir in self.jobs_dir.iterdir():
			if job_dir.is_dir():
				if status is None:
					jobs.append(job_dir.name)
				else:
					# Check job status from metadata
					job = self.get_job(job_dir.name)
					if job and job.status == status:
						jobs.append(job_dir.name)

		return sorted(jobs)

	def get_jobs_summary(self) -> Dict[str, Any]:
		"""Get summary of all jobs by status.

		Returns:
			Dictionary with job counts by status
		"""
		summary = {
			"total": 0,
			"pending": 0,
			"running": 0,
			"success": 0,
			"error": 0,
			"cancelled": 0,
		}

		for status in JobStatus:
			jobs = self.list_jobs(status)
			summary[status.value] = len(jobs)
			summary["total"] += len(jobs)

		return summary

	def save_config(self, name: str, config: Dict[str, Any]) -> Path:
		"""Save job configuration to YAML file.

		Args:
			name: Job identifier
			config: Configuration dictionary

		Returns:
			Path to config file
		"""
		job_dir = self.jobs_dir / name
		job_dir.mkdir(parents=True, exist_ok=True)

		config_file = job_dir / "config.yml"
		with open(config_file, "w") as f:
			yaml.dump(config, f, default_flow_style=False)

		return config_file

	def load_config(self, name: str) -> Optional[Dict[str, Any]]:
		"""Load job configuration from YAML file.

		Args:
			name: Job identifier

		Returns:
			Configuration dictionary if found, None otherwise
		"""
		config_file = self.jobs_dir / name / "config.yml"
		if not config_file.exists():
			return None

		try:
			with open(config_file, "r") as f:
				return yaml.safe_load(f) or {}
		except Exception as e:
			raise RuntimeError(f"Error loading config for job '{name}': {e}")

	def get_job_dir(self, name: str) -> Path:
		"""Get job directory path.

		Args:
			name: Job identifier

		Returns:
			Path to job directory
		"""
		return self.jobs_dir / name

	def get_job_log_file(self, name: str, log_name: str = "job") -> Path:
		"""Get path to job log file.

		Args:
			name: Job identifier
			log_name: Log file name (default: 'job')

		Returns:
			Path to log file
		"""
		return self.jobs_dir / name / f"{log_name}.log"

	def cleanup_old_jobs(self, keep_count: int = 10, status_filter: Optional[JobStatus] = None) -> int:
		"""Delete old jobs, keeping only the most recent ones.

		Args:
			keep_count: Number of recent jobs to keep (default: 10)
			status_filter: Optional status to filter by (e.g., only delete error jobs)

		Returns:
			Number of jobs deleted
		"""
		jobs_to_delete = self.list_jobs(status_filter)

		if len(jobs_to_delete) <= keep_count:
			return 0

		# Sort by name (assumes job names include timestamp or version)
		jobs_to_delete.sort()

		# Delete oldest, keep newest
		deleted_count = 0
		for job_name in jobs_to_delete[:-keep_count]:
			if self.delete_job(job_name):
				deleted_count += 1

		return deleted_count
