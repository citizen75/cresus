"""Logger for agents."""

import sys
import inspect
import os
from pathlib import Path

try:
	from loguru import logger as loguru_logger
	HAS_LOGURU = True

	# Configure loguru (default to ERROR level for quiet output)
	loguru_logger.remove()
	loguru_logger.add(
		sys.stderr,
		format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
		level="ERROR"
	)
except ImportError:
	HAS_LOGURU = False

# Get project root (parent of src directory)
_project_root = Path(__file__).parent.parent.parent


def _get_relative_path(filepath: str) -> str:
	"""Convert absolute path to relative path from project root.

	Args:
		filepath: Absolute file path

	Returns:
		Relative path from project root
	"""
	try:
		return str(Path(filepath).relative_to(_project_root))
	except ValueError:
		return filepath


def enable_debug_mode():
	"""Enable debug logging level for loguru."""
	if HAS_LOGURU:
		loguru_logger.remove()
		loguru_logger.add(
			sys.stderr,
			format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
			level="DEBUG"
		)


def disable_debug_mode():
	"""Disable debug logging level for loguru."""
	if HAS_LOGURU:
		loguru_logger.remove()
		loguru_logger.add(
			sys.stderr,
			format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
			level="ERROR"
		)


def set_log_level(level: str):
	"""Set log level for loguru.

	Args:
		level: Log level as string ("ERROR", "WARNING", "INFO", "DEBUG")
	"""
	if HAS_LOGURU:
		loguru_logger.remove()
		loguru_logger.add(
			sys.stderr,
			format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
			level=level.upper()
		)


def enable_verbose_mode():
	"""Enable verbose mode - show INFO level and above."""
	set_log_level("INFO")


def disable_verbose_mode():
	"""Disable verbose mode - only show ERROR level and above."""
	set_log_level("ERROR")


class AgentLogger:
	"""Logger for agents to log messages (console + file)."""

	def __init__(self, agent_name: str):
		"""Initialize logger with agent name.

		Logs to both:
		1. Console via loguru (for real-time monitoring)
		2. File via TaskLogger in ~/.cresus/db/logs/{agent_name}.log (for auditing)

		Args:
			agent_name: Name of the agent using this logger
		"""
		self.agent_name = agent_name
		# Initialize file-based logger for this agent
		try:
			from tools.logger import get_task_logger
			self.file_logger = get_task_logger(f"agent.{agent_name}")
		except Exception:
			self.file_logger = None

	def log(self, message: str):
		"""Log a message to console and file.

		Args:
			message: The message to log
		"""
		formatted_msg = f"[{self.agent_name}] {message}"
		if HAS_LOGURU:
			loguru_logger.info(formatted_msg)
		else:
			print(formatted_msg)
		if self.file_logger:
			self.file_logger.info(message)

	def info(self, message: str):
		"""Log an info level message to console and file."""
		formatted_msg = f"[{self.agent_name}]  {message}"
		if HAS_LOGURU:
			loguru_logger.info(formatted_msg)
		else:
			print(f"INFO: {formatted_msg}")
		if self.file_logger:
			self.file_logger.info(message)

	def error(self, message: str):
		"""Log an error level message to console and file."""
		formatted_msg = f"[{self.agent_name}]  {message}"
		if HAS_LOGURU:
			loguru_logger.error(formatted_msg)
		else:
			print(f"ERROR: {formatted_msg}")
		if self.file_logger:
			self.file_logger.error(message)

	def debug(self, message: str):
		"""Log a debug level message to console and file."""
		formatted_msg = f"[{self.agent_name}]  {message}"
		if HAS_LOGURU:
			loguru_logger.debug(formatted_msg)
		else:
			print(f"DEBUG: {formatted_msg}")
		if self.file_logger:
			self.file_logger.debug(message)

	def warning(self, message: str):
		"""Log a warning level message to console and file."""
		formatted_msg = f"[{self.agent_name}]  {message}"
		if HAS_LOGURU:
			loguru_logger.warning(formatted_msg)
		else:
			print(f"WARNING: {formatted_msg}")
		if self.file_logger:
			self.file_logger.warning(message)

	def exception(self, message: str):
		"""Log an exception level message to console and file."""
		formatted_msg = f"[{self.agent_name}]  {message}"
		if HAS_LOGURU:
			loguru_logger.exception(formatted_msg)
		else:
			print(f"EXCEPTION: {formatted_msg}")
		if self.file_logger:
			self.file_logger.error(message)
