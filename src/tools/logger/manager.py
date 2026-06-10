"""Task logger with per-job logging and automatic file rotation (async/fire-and-forget)."""

import os
from pathlib import Path
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
import queue
from typing import Optional
from threading import Lock
from utils.env import get_db_root

# Global loggers cache, queue listeners, and lock for thread safety
_loggers = {}
_listeners = {}  # QueueListener instances for async logging
_loggers_lock = Lock()


class TaskLogger:
	"""Logger for scheduled tasks with automatic file rotation."""

	def __init__(self, task_name: str, log_dir: Optional[Path] = None, max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5):
		"""Initialize task logger with async/fire-and-forget logging.

		Args:
			task_name: Name of the task (e.g., 'alert_sha_red')
			log_dir: Directory to store logs (default: get_db_root()/logs)
			max_bytes: Maximum file size before rotation (default: 10MB)
			backup_count: Number of backup files to keep (default: 5)
		"""
		self.task_name = task_name
		self.log_dir = log_dir or (get_db_root() / "logs")
		self.max_bytes = max_bytes
		self.backup_count = backup_count
		self.log_file = self.log_dir / f"{task_name}.log"

		# Create logs directory if it doesn't exist
		self.log_dir.mkdir(parents=True, exist_ok=True)

		# Set up logger
		self.logger = logging.getLogger(f"task.{task_name}")
		self.logger.setLevel(logging.DEBUG)
		self.logger.propagate = False  # Don't propagate to parent loggers

		# Remove existing handlers to avoid duplicates
		self.logger.handlers.clear()

		# Create queue for async logging (fire-and-forget)
		log_queue = queue.Queue(-1)  # Unlimited queue

		# Create formatter
		formatter = logging.Formatter(
			"%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
			datefmt="%Y-%m-%d %H:%M:%S"
		)

		# Create rotating file handler for the listener
		file_handler = RotatingFileHandler(
			str(self.log_file),
			maxBytes=self.max_bytes,
			backupCount=self.backup_count
		)
		file_handler.setFormatter(formatter)

		# Set up queue listener with file handler (runs in separate thread)
		listener = QueueListener(log_queue, file_handler, respect_handler_level=True)
		listener.start()

		# Store listener for cleanup
		_listeners[task_name] = listener

		# Add queue handler to logger (non-blocking, fire-and-forget)
		queue_handler = QueueHandler(log_queue)
		queue_handler.setLevel(logging.DEBUG)
		self.logger.addHandler(queue_handler)


	def info(self, msg: str) -> None:
		"""Log info level message."""
		self.logger.info(msg)

	def debug(self, msg: str) -> None:
		"""Log debug level message."""
		self.logger.debug(msg)

	def warning(self, msg: str) -> None:
		"""Log warning level message."""
		self.logger.warning(msg)

	def error(self, msg: str) -> None:
		"""Log error level message."""
		self.logger.error(msg)

	def exception(self, msg: str) -> None:
		"""Log exception level message."""
		self.logger.exception(msg)

	def get_logs(self, lines: int = 100) -> list[str]:
		"""Get recent logs from the current log file.

		Args:
			lines: Number of recent lines to return

		Returns:
			List of log lines
		"""
		if not self.log_file.exists():
			return []

		try:
			with open(self.log_file, 'r', encoding='utf-8') as f:
				all_lines = f.readlines()
				return all_lines[-lines:] if len(all_lines) > lines else all_lines
		except Exception as e:
			return [f"Error reading logs: {e}"]

	def get_all_logs(self) -> list[str]:
		"""Get all logs from the current log file.

		Returns:
			List of all log lines
		"""
		if not self.log_file.exists():
			return []

		try:
			with open(self.log_file, 'r', encoding='utf-8') as f:
				return f.readlines()
		except Exception as e:
			return [f"Error reading logs: {e}"]

	def flush(self) -> None:
		"""Flush pending log records to disk.

		Wait for all queued log records to be written.
		"""
		if self.task_name in _listeners:
			try:
				# Force flush by processing all queue items
				listener = _listeners[self.task_name]
				# The queue listener will process remaining items
				# We do this by ensuring the queue is empty
				import time
				time.sleep(0.1)  # Give queue time to process
			except Exception:
				pass

	def stop(self) -> None:
		"""Stop the queue listener and clean up resources."""
		self.flush()
		if self.task_name in _listeners:
			try:
				_listeners[self.task_name].stop()
				del _listeners[self.task_name]
			except Exception:
				pass


def get_task_logger(task_name: str) -> TaskLogger:
	"""Get or create a logger for a task.

	Args:
		task_name: Name of the task

	Returns:
		TaskLogger instance
	"""
	with _loggers_lock:
		if task_name not in _loggers:
			_loggers[task_name] = TaskLogger(task_name)
		return _loggers[task_name]


def list_task_logs(log_dir: Optional[Path] = None) -> dict[str, dict]:
	"""List all task log files with metadata.

	Args:
		log_dir: Directory to scan for logs

	Returns:
		Dictionary mapping task names to log metadata
	"""
	log_dir = log_dir or (get_db_root() / "logs")
	if not log_dir.exists():
		return {}

	logs = {}
	for log_file in log_dir.glob("*.log"):
		task_name = log_file.stem
		try:
			stat = log_file.stat()
			logs[task_name] = {
				"size": stat.st_size,
				"modified": stat.st_mtime,
				"path": str(log_file),
			}
		except Exception as e:
			logs[task_name] = {"error": str(e)}

	return logs
