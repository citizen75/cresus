"""Cron scheduler using APScheduler."""

from pathlib import Path
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from tools.cron import CronConfig, CronJobConfig


class CronScheduler:
	"""APScheduler-based cron job scheduler."""

	def __init__(self, config_path: Optional[Path] = None):
		"""Initialize cron scheduler.

		Args:
			config_path: Path to cron.yml config file
		"""
		self.config = CronConfig(config_path)
		self.scheduler = BackgroundScheduler()
		self._setup_jobs()

	def _setup_jobs(self) -> None:
		"""Set up cron jobs from configuration."""
		enabled_jobs = self.config.get_enabled_jobs()

		if not enabled_jobs:
			logger.info("No enabled cron jobs found")
			return

		for job_config in enabled_jobs:
			try:
				self._add_job(job_config)
			except Exception as e:
				logger.error(f"Failed to add cron job '{job_config.name}': {e}")

	def _add_job(self, job_config: CronJobConfig) -> None:
		"""Add a cron job to the scheduler.

		Args:
			job_config: Job configuration
		"""
		# Create job function that calls agent or flow
		job_func = self._create_job_function(job_config)

		# Parse cron expression and add to scheduler
		try:
			trigger = CronTrigger.from_crontab(job_config.schedule)
		except Exception as e:
			logger.error(f"Invalid cron schedule '{job_config.schedule}' for job '{job_config.name}': {e}")
			return

		self.scheduler.add_job(
			job_func,
			trigger=trigger,
			id=job_config.name,
			name=job_config.description or job_config.name,
			coalesce=True,
			max_instances=1,
		)

		logger.info(f"Added cron job '{job_config.name}': {job_config.schedule}")

	def _create_job_function(self, job_config: CronJobConfig):
		"""Create a job function that calls the target agent or flow.

		Args:
			job_config: Job configuration

		Returns:
			Callable job function
		"""
		from tools.logger import get_task_logger
		import time

		def job_func():
			# Get per-task logger
			task_logger = get_task_logger(job_config.name)

			try:
				task_logger.info(f"Starting execution ({job_config.type}: {job_config.target})")
				logger.info(f"Executing cron job '{job_config.name}' ({job_config.type}: {job_config.target})")

				if job_config.type == "http":
					self._call_http(job_config.target, job_config.params)
				elif job_config.type == "shell_exec":
					self._call_shell(job_config.target, job_config.params)
				elif job_config.type == "flow":
					self._call_flow(job_config.target, job_config.params)
				elif job_config.type == "agent":
					self._call_agent(job_config.target, job_config.params)
				elif job_config.type == "job":
					self._call_job(job_config.target, job_config.params)
				else:
					raise ValueError(f"Unknown job type: {job_config.type}")

				task_logger.info(f"Execution completed successfully")
				logger.info(f"Cron job '{job_config.name}' completed successfully")

			except Exception as e:
				task_logger.error(f"Execution failed: {e}")
				logger.error(f"Cron job '{job_config.name}' failed: {e}", exc_info=True)
			finally:
				# Ensure logs are flushed to disk
				time.sleep(0.2)  # Give queue time to process
				task_logger.flush()

		return job_func

	def _call_flow(self, flow_name: str, params: dict) -> None:
		"""Call a flow with given parameters.

		Args:
			flow_name: Name of the flow
			params: Flow parameters
		"""
		from core.context import AgentContext
		from agents.market_prep.agent import MarketPrepAgent
		from flows.data_fetch import DataFetchFlow
		from flows.heartbeat import HeartbeatFlow

		# Map flow names to flow/agent classes
		flow_classes = {
			"premarket": MarketPrepAgent,
			"data_fetch": DataFetchFlow,
			"heartbeat": HeartbeatFlow,
		}

		if flow_name not in flow_classes:
			raise ValueError(f"Unknown flow: {flow_name}")

		# Instantiate flow and execute based on flow type
		flow_class = flow_classes[flow_name]

		if flow_name == "heartbeat":
			flow = flow_class()
		elif flow_name == "data_fetch":
			universe = params.get("universe", "cac40")
			flow = flow_class(universe=universe)
		else:
			# Default: strategy-based flows
			strategy = params.get("strategy")
			if not strategy:
				raise ValueError(f"Flow '{flow_name}' requires 'strategy' parameter")
			flow = flow_class(strategy)

		result = flow.process(params)
		logger.info(f"Flow '{flow_name}' result: {result.get('status', 'unknown')}")

	def _call_agent(self, agent_name: str, params: dict) -> None:
		"""Call an agent with given parameters.

		Args:
			agent_name: Name of the agent
			params: Agent parameters
		"""
		from core.context import AgentContext
		from agents.strategy.agent import StrategyAgent
		from agents.data.agent import DataAgent
		from agents.watchlist.agent import WatchListAgent

		# Map agent names to agent classes
		agent_classes = {
			"strategy": StrategyAgent,
			"data": DataAgent,
			"watchlist": WatchListAgent,
		}

		if agent_name not in agent_classes:
			raise ValueError(f"Unknown agent: {agent_name}")

		# Create context and instantiate agent
		context = AgentContext()
		agent_class = agent_classes[agent_name]
		agent = agent_class(f"{agent_name}_cron_job", context)

		# Execute agent
		result = agent.process(params)
		logger.info(f"Agent '{agent_name}' result: {result.get('status', 'unknown')}")

	def _call_job(self, job_name: str, params: dict) -> None:
		"""Call a Job (long-running task with its own job_dir/lifecycle tracking).

		Args:
			job_name: Name of the job
			params: Job parameters
		"""
		from jobs.job_intraday import JobIntraday
		from jobs.job_pre_market import JobPreMarket

		# Map job names to job classes
		job_classes = {
			"intraday": JobIntraday,
			"pre_market": JobPreMarket,
		}

		if job_name not in job_classes:
			raise ValueError(f"Unknown job: {job_name}")

		job_class = job_classes[job_name]
		job = job_class()

		# Execute job (run() handles start/complete/fail lifecycle and metadata persistence)
		result = job.run(params)
		logger.info(f"Job '{job_name}' result: {result.get('status', 'unknown')}")

	def _call_http(self, url: str, params: dict) -> None:
		"""Make an HTTP request.

		Args:
			url: Target URL
			params: HTTP request parameters (method, headers, body, etc.)
		"""
		import requests

		method = params.get("method", "POST").upper()
		headers = params.get("headers", {})
		body = params.get("body")
		timeout = params.get("timeout", 30)

		logger.info(f"Making HTTP {method} request to {url}")

		try:
			if method == "GET":
				response = requests.get(url, headers=headers, timeout=timeout)
			elif method == "POST":
				response = requests.post(url, json=body, headers=headers, timeout=timeout)
			elif method == "PUT":
				response = requests.put(url, json=body, headers=headers, timeout=timeout)
			elif method == "DELETE":
				response = requests.delete(url, headers=headers, timeout=timeout)
			elif method == "PATCH":
				response = requests.patch(url, json=body, headers=headers, timeout=timeout)
			else:
				raise ValueError(f"Unsupported HTTP method: {method}")

			response.raise_for_status()
			logger.info(f"HTTP {method} request completed: {response.status_code}")
		except Exception as e:
			logger.error(f"HTTP request failed: {e}")
			raise

	def _call_shell(self, command: str, params: dict) -> None:
		"""Execute a shell command.

		Args:
			command: Shell command to execute
			params: Additional parameters (env, timeout, etc.)
		"""
		import subprocess

		timeout = params.get("timeout", 300)

		logger.info(f"Executing shell command: {command}")

		try:
			result = subprocess.run(
				command,
				shell=True,
				timeout=timeout,
				capture_output=True,
				text=True
			)

			if result.returncode != 0:
				logger.error(f"Shell command failed with code {result.returncode}: {result.stderr}")
				raise RuntimeError(f"Command failed: {result.stderr}")

			logger.info(f"Shell command completed successfully")
			if result.stdout:
				logger.info(f"Output: {result.stdout}")
		except subprocess.TimeoutExpired:
			logger.error(f"Shell command timed out after {timeout}s")
			raise
		except Exception as e:
			logger.error(f"Shell execution failed: {e}")
			raise

	def start(self) -> None:
		"""Start the scheduler."""
		if self.scheduler.running:
			logger.warning("Scheduler is already running")
			return

		self.scheduler.start()
		logger.info("Cron scheduler started")

	def stop(self) -> None:
		"""Stop the scheduler."""
		if not self.scheduler.running:
			logger.warning("Scheduler is not running")
			return

		self.scheduler.shutdown(wait=True)
		logger.info("Cron scheduler stopped")

	def is_running(self) -> bool:
		"""Check if scheduler is running.

		Returns:
			True if running, False otherwise
		"""
		return self.scheduler.running

	def get_jobs(self) -> list:
		"""Get list of scheduled jobs.

		Returns:
			List of APScheduler Job objects
		"""
		return self.scheduler.get_jobs()

	def reload_job(self, job_name: str) -> bool:
		"""Reload a single job from config and update scheduler.

		Used when a job is updated in config to apply changes to running scheduler.

		Args:
			job_name: Name of the job to reload

		Returns:
			True if job was reloaded, False otherwise
		"""
		try:
			# Get updated job config
			self.config.reload()
			job_config = self.config.get_job(job_name)

			if not job_config:
				logger.warning(f"Job '{job_name}' not found in config after reload")
				return False

			# Remove old job from scheduler
			try:
				self.scheduler.remove_job(job_name)
			except Exception:
				pass  # Job might not be running

			# Add updated job to scheduler
			self._add_job(job_config)
			logger.info(f"Reloaded cron job '{job_name}' in running scheduler")
			return True

		except Exception as e:
			logger.error(f"Failed to reload job '{job_name}': {e}", exc_info=True)
			return False

	def reload_all_jobs(self) -> None:
		"""Reload all jobs from config after external config file changes.

		Useful when config.yml is modified externally to sync scheduler with config.
		"""
		try:
			logger.info("Reloading all cron jobs from config...")
			# Reload config from disk
			self.config.reload()

			# Get all currently scheduled jobs
			current_jobs = {job.id for job in self.scheduler.get_jobs()}

			# Get all jobs from updated config
			enabled_config_jobs = self.config.get_enabled_jobs()
			config_job_names = {job.name for job in enabled_config_jobs}

			# Remove jobs that are no longer enabled
			for job_id in current_jobs:
				if job_id not in config_job_names:
					try:
						self.scheduler.remove_job(job_id)
						logger.info(f"Removed job '{job_id}' (no longer enabled)")
					except Exception:
						pass

			# Update or add jobs from config
			for job_config in enabled_config_jobs:
				try:
					# Remove old job if it exists
					try:
						self.scheduler.remove_job(job_config.name)
					except Exception:
						pass
					# Add updated job
					self._add_job(job_config)
				except Exception as e:
					logger.error(f"Failed to reload job '{job_config.name}': {e}")

			logger.info(f"All cron jobs reloaded: {len(enabled_config_jobs)} enabled jobs")

		except Exception as e:
			logger.error(f"Failed to reload all jobs: {e}", exc_info=True)

	def add_job_to_scheduler(self, job_name: str) -> bool:
		"""Add a job to the running scheduler.

		Args:
			job_name: Name of the job

		Returns:
			True if job was added, False otherwise
		"""
		try:
			job_config = self.config.get_job(job_name)
			if not job_config:
				logger.error(f"Job '{job_name}' not found in config")
				return False

			self._add_job(job_config)
			return True

		except Exception as e:
			logger.error(f"Failed to add job '{job_name}' to scheduler: {e}", exc_info=True)
			return False

	def remove_job_from_scheduler(self, job_name: str) -> bool:
		"""Remove a job from the running scheduler.

		Args:
			job_name: Name of the job

		Returns:
			True if job was removed, False otherwise
		"""
		try:
			self.scheduler.remove_job(job_name)
			logger.info(f"Removed job '{job_name}' from running scheduler")
			return True

		except Exception as e:
			logger.error(f"Failed to remove job '{job_name}' from scheduler: {e}", exc_info=True)
			return False
