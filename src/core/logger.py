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
	"""Logger for agents to log messages."""

	def __init__(self, agent_name: str):
		"""Initialize logger with agent name.

		Args:
			agent_name: Name of the agent using this logger
		"""
		self.agent_name = agent_name

	def log(self, message: str):
		"""Log a message.

		Args:
			message: The message to log
		"""
		formatted_msg = f"[{self.agent_name}] {message}"
		if HAS_LOGURU:
			loguru_logger.info(formatted_msg)
		else:
			print(formatted_msg)

	def info(self, message: str):
		"""Log an info level message."""
		formatted_msg = f"[{self.agent_name}] {message}"
		if HAS_LOGURU:
			frame = inspect.currentframe().f_back
			rel_path = _get_relative_path(frame.f_code.co_filename)
			loguru_logger.info(f"{rel_path}:{frame.f_lineno} - {formatted_msg}")
		else:
			print(f"INFO: {formatted_msg}")

	def error(self, message: str):
		"""Log an error level message."""
		formatted_msg = f"[{self.agent_name}] {message}"
		if HAS_LOGURU:
			frame = inspect.currentframe().f_back
			rel_path = _get_relative_path(frame.f_code.co_filename)
			loguru_logger.error(f"{rel_path}:{frame.f_lineno} - {formatted_msg}")
		else:
			print(f"ERROR: {formatted_msg}")

	def debug(self, message: str):
		"""Log a debug level message."""
		formatted_msg = f"[{self.agent_name}] {message}"
		if HAS_LOGURU:
			frame = inspect.currentframe().f_back
			rel_path = _get_relative_path(frame.f_code.co_filename)
			loguru_logger.debug(f"{rel_path}:{frame.f_lineno} - {formatted_msg}")
		else:
			print(f"DEBUG: {formatted_msg}")

	def warning(self, message: str):
		"""Log a warning level message."""
		formatted_msg = f"[{self.agent_name}] {message}"
		if HAS_LOGURU:
			frame = inspect.currentframe().f_back
			rel_path = _get_relative_path(frame.f_code.co_filename)
			loguru_logger.warning(f"{rel_path}:{frame.f_lineno} - {formatted_msg}")
		else:
			print(f"WARNING: {formatted_msg}")

	def exception(self, message: str):
		"""Log an exception level message."""
		formatted_msg = f"[{self.agent_name}] {message}"
		if HAS_LOGURU:
			frame = inspect.currentframe().f_back
			rel_path = _get_relative_path(frame.f_code.co_filename)
			loguru_logger.exception(f"{rel_path}:{frame.f_lineno} - {formatted_msg}")
		else:
			print(f"EXCEPTION: {formatted_msg}")
