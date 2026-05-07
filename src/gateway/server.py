"""Unified gateway server combining API and cron scheduler."""

import sys
import threading
import signal
import time
from pathlib import Path
from typing import Optional
from loguru import logger
import uvicorn

from gateway.cron import CronScheduler
from gateway.watchdog import FileWatcher
from utils.env import get_config_root


class GatewayServer:
	"""Unified gateway server combining FastAPI and cron scheduler.

	Runs the API server and cron scheduler in separate threads,
	allowing them to operate concurrently.
	"""

	def __init__(
		self,
		api_host: str = "0.0.0.0",
		api_port: int = 8000,
		cron_config_path: Optional[Path] = None,
		enable_cron: bool = True,
		enable_mcp: bool = True,
	):
		"""Initialize gateway server.

		Args:
			api_host: API server host
			api_port: API server port
			cron_config_path: Path to cron.yml config file
			enable_cron: Whether to enable cron scheduler
			enable_mcp: Whether to enable MCP server
		"""
		self.api_host = api_host
		self.api_port = api_port
		self.enable_cron = enable_cron
		self.enable_mcp = enable_mcp

		self.api_server: Optional[uvicorn.Server] = None
		self.api_thread: Optional[threading.Thread] = None
		self.cron_scheduler: Optional[CronScheduler] = None
		self.cron_thread: Optional[threading.Thread] = None
		self.mcp_thread: Optional[threading.Thread] = None
		self.file_watcher: Optional[FileWatcher] = None

		if enable_cron and cron_config_path is None:
			cron_config_path = get_config_root() / "cron.yml"

		self.cron_config_path = cron_config_path
		self.running = False

		# Initialize file watcher to monitor code changes
		project_root = Path(__file__).parent.parent.parent
		self.file_watcher = FileWatcher(
			project_root,
			on_api_change=self._on_api_change,
			on_mcp_change=self._on_mcp_change,
			on_gateway_change=self._on_gateway_change,
		)

	def _on_api_change(self) -> None:
		"""Handle API module changes - restart API server."""
		logger.info("Detected API code changes, restarting API server...")
		try:
			if self.api_server:
				self.api_server.should_exit = True
				if self.api_thread and self.api_thread.is_alive():
					self.api_thread.join(timeout=5)

			# Restart API server in new thread
			self.api_thread = threading.Thread(target=self._start_api, daemon=False)
			self.api_thread.start()
			logger.info("API server restarted")

		except Exception as e:
			logger.error(f"Error restarting API server: {e}", exc_info=True)

	def _on_mcp_change(self) -> None:
		"""Handle MCP module changes - restart MCP server."""
		logger.info("Detected MCP code changes, restarting MCP server...")
		try:
			if self.mcp_thread and self.mcp_thread.is_alive():
				self.mcp_thread.join(timeout=5)

			# Restart MCP server in new thread
			self.mcp_thread = threading.Thread(target=self._start_mcp, daemon=False)
			self.mcp_thread.start()
			logger.info("MCP server restarted")

		except Exception as e:
			logger.error(f"Error restarting MCP server: {e}", exc_info=True)

	def _on_gateway_change(self) -> None:
		"""Handle gateway module changes - restart cron scheduler."""
		logger.info("Detected gateway code changes, restarting cron scheduler...")
		try:
			if self.cron_scheduler and self.cron_scheduler.is_running():
				self.cron_scheduler.stop()
				if self.cron_thread and self.cron_thread.is_alive():
					self.cron_thread.join(timeout=5)

			# Restart cron scheduler in new thread
			if self.enable_cron:
				self.cron_thread = threading.Thread(target=self._start_cron, daemon=False)
				self.cron_thread.start()
				logger.info("Cron scheduler restarted")

		except Exception as e:
			logger.error(f"Error restarting cron scheduler: {e}", exc_info=True)

	def _start_api(self) -> None:
		"""Start the API server in a separate thread."""
		try:
			logger.info(f"Starting API server on {self.api_host}:{self.api_port}")

			config = uvicorn.Config(
				"api.app:create_app",
				host=self.api_host,
				port=self.api_port,
				factory=True,
				log_level="info",
			)

			self.api_server = uvicorn.Server(config)
			self.api_server.run()

		except Exception as e:
			logger.error(f"API server failed: {e}", exc_info=True)

	def _start_cron(self) -> None:
		"""Start the cron scheduler in a separate thread."""
		try:
			logger.info("Starting cron scheduler")

			self.cron_scheduler = CronScheduler(self.cron_config_path)
			self.cron_scheduler.start()

			# Keep the scheduler running
			if self.cron_scheduler.is_running():
				logger.info(f"Cron scheduler running with {len(self.cron_scheduler.get_jobs())} jobs")

				# Block until shutdown
				while self.running and self.cron_scheduler.is_running():
					time.sleep(1)

		except Exception as e:
			logger.error(f"Cron scheduler failed: {e}", exc_info=True)

	def _start_mcp(self) -> None:
		"""Start the MCP server in a separate thread."""
		try:
			logger.info("Starting MCP server")

			from mcp.server import CresusMCPServer

			mcp_server = CresusMCPServer()
			mcp_server.run()

		except ImportError:
			logger.warning("MCP module not found, skipping MCP server")
		except Exception as e:
			logger.error(f"MCP server failed: {e}", exc_info=True)

	def start(self) -> None:
		"""Start the gateway server."""
		if self.running:
			logger.warning("Gateway is already running")
			return

		self.running = True

		# Set up signal handlers for graceful shutdown
		signal.signal(signal.SIGINT, self._signal_handler)
		signal.signal(signal.SIGTERM, self._signal_handler)

		# Start API server in a separate thread
		logger.info("Starting Cresus Gateway")
		self.api_thread = threading.Thread(target=self._start_api, daemon=False)
		self.api_thread.start()
		logger.info("API server thread started")

		# Start cron scheduler in a separate thread if enabled
		if self.enable_cron:
			self.cron_thread = threading.Thread(target=self._start_cron, daemon=False)
			self.cron_thread.start()
			logger.info("Cron scheduler thread started")

		# Start MCP server in a separate thread if enabled
		if self.enable_mcp:
			self.mcp_thread = threading.Thread(target=self._start_mcp, daemon=False)
			self.mcp_thread.start()
			logger.info("MCP server thread started")

		# Start file watcher to monitor code changes
		if self.file_watcher:
			self.file_watcher.start()
			logger.info("File watcher started")

		# Wait for all threads to complete
		if self.api_thread:
			self.api_thread.join()

		if self.cron_thread:
			self.cron_thread.join()

		if self.mcp_thread:
			self.mcp_thread.join()

	def stop(self) -> None:
		"""Stop the gateway server gracefully."""
		logger.info("Stopping Cresus Gateway")
		self.running = False

		# Stop file watcher
		if self.file_watcher:
			try:
				self.file_watcher.stop()
			except Exception as e:
				logger.error(f"Error stopping file watcher: {e}")

		# Stop cron scheduler
		if self.cron_scheduler and self.cron_scheduler.is_running():
			try:
				self.cron_scheduler.stop()
			except Exception as e:
				logger.error(f"Error stopping cron scheduler: {e}")

		# Stop API server
		if self.api_server:
			try:
				self.api_server.should_exit = True
			except Exception as e:
				logger.error(f"Error stopping API server: {e}")

	def _signal_handler(self, sig, frame):
		"""Handle shutdown signals gracefully."""
		logger.info(f"Received signal {sig}, shutting down gracefully...")
		self.stop()
		sys.exit(0)


def create_gateway(
	api_host: str = "0.0.0.0",
	api_port: int = 8000,
	enable_cron: bool = True,
	enable_mcp: bool = True,
) -> GatewayServer:
	"""Create a gateway server instance.

	Args:
		api_host: API server host
		api_port: API server port
		enable_cron: Whether to enable cron scheduler
		enable_mcp: Whether to enable MCP server

	Returns:
		GatewayServer instance
	"""
	return GatewayServer(api_host, api_port, enable_cron=enable_cron, enable_mcp=enable_mcp)
