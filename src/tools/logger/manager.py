"""Task logger with per-job logging and automatic file rotation."""

import os
from pathlib import Path
from datetime import datetime
import logging
from typing import Optional
from utils.env import get_db_root

# Global loggers cache
_loggers = {}


class TaskLogger:
	"""Logger for scheduled tasks with automatic file rotation."""

	def __init__(self, task_name: str, log_dir: Optional[Path] = None, max_bytes: int = 10 * 1024 * 1024):
		"""Initialize task logger.

		Args:
			task_name: Name of the task (e.g., 'alert_sha_red')
			log_dir: Directory to store logs (default: get_db_root()/logs)
			max_bytes: Maximum file size before rotation (default: 10MB)
		"""
		self.task_name = task_name
		self.log_dir = log_dir or (get_db_root() / "logs")
		self.max_bytes = max_bytes
		self.log_file = self.log_dir / f"{task_name}.log"

		# Create logs directory if it doesn't exist
		self.log_dir.mkdir(parents=True, exist_ok=True)

		# Set up logger
		self.logger = logging.getLogger(f"task.{task_name}")
		self.logger.setLevel(logging.DEBUG)

		# Remove existing handlers to avoid duplicates
		self.logger.handlers.clear()

		# Create formatter
		formatter = logging.Formatter(
			"%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
			datefmt="%Y-%m-%d %H:%M:%S"
		)

		# Add file handler with rotation
		handler = self._get_rotating_handler(formatter)
		self.logger.addHandler(handler)

	def _get_rotating_handler(self, formatter: logging.Formatter) -> logging.FileHandler:
		"""Create a file handler with rotation logic."""
		# Check if rotation is needed
		if self.log_file.exists() and self.log_file.stat().st_size >= self.max_bytes:
			self._rotate_logs()

		handler = logging.FileHandler(self.log_file, mode='a', encoding='utf-8')
		handler.setFormatter(formatter)
		return handler

	def _rotate_logs(self) -> None:
		"""Rotate log file when size exceeds threshold."""
		if not self.log_file.exists():
			return

		# Create backup filename with timestamp
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		backup_file = self.log_dir / f"{self.task_name}.{timestamp}.log"

		try:
			self.log_file.rename(backup_file)
			self.logger.info(f"Log rotated: {backup_file.name}")
		except Exception as e:
			self.logger.error(f"Failed to rotate log: {e}")

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


def get_task_logger(task_name: str) -> TaskLogger:
	"""Get or create a logger for a task.

	Args:
		task_name: Name of the task

	Returns:
		TaskLogger instance
	"""
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
