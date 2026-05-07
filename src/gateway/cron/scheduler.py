"""Cron scheduler using APScheduler."""

from pathlib import Path
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from .config import CronConfig, CronJobConfig


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

		def job_func():
			try:
				logger.info(f"Executing cron job '{job_config.name}' ({job_config.type}: {job_config.target})")

				if job_config.type == "flow":
					self._call_flow(job_config.target, job_config.params)
				elif job_config.type == "agent":
					self._call_agent(job_config.target, job_config.params)

				logger.info(f"Cron job '{job_config.name}' completed successfully")

			except Exception as e:
				logger.error(f"Cron job '{job_config.name}' failed: {e}", exc_info=True)

		return job_func

	def _call_flow(self, flow_name: str, params: dict) -> None:
		"""Call a flow with given parameters.

		Args:
			flow_name: Name of the flow
			params: Flow parameters
		"""
		from core.context import AgentContext
		from flows.premarket import PreMarketFlow
		from flows.data_fetch import DataFetchFlow
		from flows.heartbeat import HeartbeatFlow

		# Map flow names to flow classes
		flow_classes = {
			"premarket": PreMarketFlow,
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
