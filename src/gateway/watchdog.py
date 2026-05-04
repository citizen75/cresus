"""File watchdog to monitor code changes and restart servers."""

import threading
import time
from pathlib import Path
from typing import Callable, Optional, List
from loguru import logger

try:
	from watchdog.observers import Observer
	from watchdog.events import FileSystemEventHandler, FileModifiedEvent
	WATCHDOG_AVAILABLE = True
except ImportError:
	WATCHDOG_AVAILABLE = False
	logger.warning("watchdog library not installed. Install with: pip install watchdog")


class CodeChangeHandler(FileSystemEventHandler):
	"""Handle file system events and trigger callbacks on code changes."""

	def __init__(
		self,
		on_api_change: Optional[Callable] = None,
		on_mcp_change: Optional[Callable] = None,
		on_gateway_change: Optional[Callable] = None,
		debounce_seconds: float = 2.0,
	):
		"""Initialize handler.

		Args:
			on_api_change: Callback for API changes
			on_mcp_change: Callback for MCP changes
			on_gateway_change: Callback for gateway changes
			debounce_seconds: Debounce period to avoid multiple triggers
		"""
		super().__init__()
		self.on_api_change = on_api_change
		self.on_mcp_change = on_mcp_change
		self.on_gateway_change = on_gateway_change
		self.debounce_seconds = debounce_seconds
		self.last_trigger_time = 0
		self.pending_changes = set()
		self.lock = threading.Lock()

	def on_modified(self, event):
		"""Handle file modification events."""
		if event.is_directory or not self._should_watch(event.src_path):
			return

		with self.lock:
			# Track which module changed
			if "/api/" in event.src_path:
				self.pending_changes.add("api")
			elif "/mcp/" in event.src_path:
				self.pending_changes.add("mcp")
			elif "/gateway/" in event.src_path:
				self.pending_changes.add("gateway")

			# Debounce: trigger callback after delay
			current_time = time.time()
			if current_time - self.last_trigger_time >= self.debounce_seconds:
				self._trigger_callbacks()
				self.last_trigger_time = current_time

	def _should_watch(self, file_path: str) -> bool:
		"""Check if file should be watched."""
		# Ignore __pycache__, .pyc, and temporary files
		if any(x in file_path for x in ["__pycache__", ".pyc", ".tmp", ".swp", ".pyo"]):
			return False

		# Only watch Python files
		return file_path.endswith(".py")

	def _trigger_callbacks(self):
		"""Trigger callbacks for changed modules."""
		changes = self.pending_changes.copy()
		self.pending_changes.clear()

		for module in changes:
			if module == "api" and self.on_api_change:
				logger.info(f"Detected changes in API module")
				self.on_api_change()
			elif module == "mcp" and self.on_mcp_change:
				logger.info(f"Detected changes in MCP module")
				self.on_mcp_change()
			elif module == "gateway" and self.on_gateway_change:
				logger.info(f"Detected changes in gateway module")
				self.on_gateway_change()


class FileWatcher:
	"""Watch for file changes and restart servers."""

	def __init__(
		self,
		project_root: Path,
		on_api_change: Optional[Callable] = None,
		on_mcp_change: Optional[Callable] = None,
		on_gateway_change: Optional[Callable] = None,
		debounce_seconds: float = 2.0,
	):
		"""Initialize file watcher.

		Args:
			project_root: Root path of the project
			on_api_change: Callback when API code changes
			on_mcp_change: Callback when MCP code changes
			on_gateway_change: Callback when gateway code changes
			debounce_seconds: Debounce period for file changes
		"""
		self.project_root = Path(project_root)
		self.debounce_seconds = debounce_seconds
		self.observer: Optional[Observer] = None
		self.running = False

		if not WATCHDOG_AVAILABLE:
			logger.warning("File watcher disabled: watchdog library not installed")
			return

		# Create event handler
		self.handler = CodeChangeHandler(
			on_api_change=on_api_change,
			on_mcp_change=on_mcp_change,
			on_gateway_change=on_gateway_change,
			debounce_seconds=debounce_seconds,
		)

		# Create observer
		self.observer = Observer()

	def start(self) -> None:
		"""Start watching for file changes."""
		if not WATCHDOG_AVAILABLE:
			return

		if self.running or not self.observer:
			return

		try:
			# Watch src/api directory
			api_path = self.project_root / "src" / "api"
			if api_path.exists():
				self.observer.schedule(self.handler, api_path, recursive=True)
				logger.info(f"Watching API directory: {api_path}")

			# Watch src/mcp directory
			mcp_path = self.project_root / "src" / "mcp"
			if mcp_path.exists():
				self.observer.schedule(self.handler, mcp_path, recursive=True)
				logger.info(f"Watching MCP directory: {mcp_path}")

			# Watch src/gateway directory
			gateway_path = self.project_root / "src" / "gateway"
			if gateway_path.exists():
				self.observer.schedule(self.handler, gateway_path, recursive=True)
				logger.info(f"Watching gateway directory: {gateway_path}")

			# Start observer
			self.observer.start()
			self.running = True
			logger.info("File watcher started")

		except Exception as e:
			logger.error(f"Failed to start file watcher: {e}")

	def stop(self) -> None:
		"""Stop watching for file changes."""
		if not self.running or not self.observer:
			return

		try:
			self.observer.stop()
			self.observer.join(timeout=5)
			self.running = False
			logger.info("File watcher stopped")
		except Exception as e:
			logger.error(f"Error stopping file watcher: {e}")
